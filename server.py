from flask import Flask, request, jsonify
from flask_cors import CORS
from sudachipy import tokenizer, dictionary
# 使用更稳定的日语词典
import json
import os
import re
 

# --- 初始化 ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
tokenizer_obj = dictionary.Dictionary(dict_type="full").create()

# 可选：外部多音字库（Kanjidic2 等清单转 json 后放置于项目根目录）
KANJI_READINGS_PATH = os.path.join(os.path.dirname(__file__), 'kanji_readings.json')
EN_KANA_DICT_PATH = os.path.join(os.path.dirname(__file__), 'english_kana.json')
try:
    with open(KANJI_READINGS_PATH, 'r', encoding='utf-8') as _f:
        EXTERNAL_KANJI_READINGS = json.load(_f)
        if not isinstance(EXTERNAL_KANJI_READINGS, dict):
            EXTERNAL_KANJI_READINGS = {}
except Exception:
    EXTERNAL_KANJI_READINGS = {}

try:
    with open(EN_KANA_DICT_PATH, 'r', encoding='utf-8') as _f:
        ENGLISH_KANA_DICT = json.load(_f)
        if not isinstance(ENGLISH_KANA_DICT, dict):
            ENGLISH_KANA_DICT = {}
except Exception:
    ENGLISH_KANA_DICT = {}

ENG_KANA_MODE = os.getenv('ENG_KANA_MODE', 'auto')  # auto|g2p|wordlist|simple

# 外部词典：JMdict/EDICT 与 Kanjidic2（请预处理为 JSON 映射）
JMDICT_PATH = os.getenv('JMDICT_JSON', os.path.join(os.path.dirname(__file__), 'jmdict_readings.json'))
KANJIDIC2_PATH = os.getenv('KANJIDIC2_JSON', os.path.join(os.path.dirname(__file__), 'kanjidic2_readings.json'))
try:
    with open(JMDICT_PATH, 'r', encoding='utf-8') as _f:
        JMDICT_READINGS = json.load(_f)
        if not isinstance(JMDICT_READINGS, dict):
            JMDICT_READINGS = {}
except Exception:
    JMDICT_READINGS = {}

try:
    with open(KANJIDIC2_PATH, 'r', encoding='utf-8') as _f:
        KANJIDIC2_READINGS = json.load(_f)
        if not isinstance(KANJIDIC2_READINGS, dict):
            KANJIDIC2_READINGS = {}
except Exception:
    KANJIDIC2_READINGS = {}

# 词组级优先读音（短语/多字词的纠正，按顺序优先）
PHRASE_OVERRIDE_READINGS = {
    # 薄暮：规范音读「はくぼ」为主，口语/诗意「うすぐれ」为备选
    "薄暮": ["はくぼ", "うすぐれ"],
    # 现代常用表达
    "今日": ["きょう", "こんにち"],
    "昨日": ["きのう", "さくじつ"],
    "明日": ["あした", "みょうにち"],
    "明後日": ["あさって", "みょうごにち"],
}

MODERN_OVERRIDES_PATH = os.getenv('MODERN_OVERRIDES', os.path.join(os.path.dirname(__file__), 'modern_overrides.json'))
try:
    with open(MODERN_OVERRIDES_PATH, 'r', encoding='utf-8') as _f:
        _MODERN_EXT = json.load(_f)
        if isinstance(_MODERN_EXT, dict):
            for k, v in _MODERN_EXT.items():
                if isinstance(v, list) and v:
                    PHRASE_OVERRIDE_READINGS[k] = v
except Exception:
    pass

# --- 辅助函数 ---
def katakana_to_hiragana(katakana_string):
    hiragana_string = ""
    for char in katakana_string:
        if 'ァ' <= char <= 'ヶ':
            hiragana_char = chr(ord(char) - 96)
            hiragana_string += hiragana_char
        else:
            hiragana_string += char
    return hiragana_string

def is_all_katakana(text):
    for char in text:
        if not ('ァ' <= char <= 'ヶ' or char == 'ー'):
            return False
    return True

def contains_kanji(text):
    """检测文本是否包含汉字"""
    for char in text:
        # 汉字的Unicode范围
        if ('\u4e00' <= char <= '\u9fff' or  # CJK统一汉字
            '\u3400' <= char <= '\u4dbf' or  # CJK扩展A
            '\uf900' <= char <= '\ufaff'):   # CJK兼容汉字
            return True
    return False

def is_hiragana(char):
    """检测是否为平假名字符"""
    return '\u3040' <= char <= '\u309f'

def is_hiragana_text(text: str) -> bool:
    """是否整段为平假名（用于判断后续送假名/助词等）"""
    if not text:
        return False
    for ch in text:
        if not ('\u3040' <= ch <= '\u309f'):
            return False
    return True

def extract_trailing_hiragana(text: str) -> str:
    """提取结尾连续的平假名串（若无则返回空串）。"""
    if not text:
        return ""
    i = len(text) - 1
    while i >= 0 and ('\u3040' <= text[i] <= '\u309f'):
        i -= 1
    return text[i+1:]

def collect_next_hiragana(tokens, current_index: int, max_chars: int = 2) -> str:
    """从当前 token 之后收集连续的“非助词/非助动词/非符号”的平假名。
    仅用于判定是否与下一片段构成同一词形读音（避免把「の/は/が」等助词误当作送假名）。"""
    collected = ""
    j = current_index + 1
    while j < len(tokens) and len(collected) < max_chars:
        s = tokens[j].surface()
        pos0 = tokens[j].part_of_speech()[0]
        if is_hiragana_text(s) and pos0 not in ("助詞", "助動詞", "補助記号"):
            collected += s
            j += 1
        else:
            break
    return collected

def filter_alternative_readings(surface: str, readings: list) -> list:
    """过滤明显无效的候选读音：
    - 若包含汉字，则剔除长度<=1的纯假名候选（如误把后续送假名切成单假名）
    - 去重并保序
    """
    if not readings:
        return readings
    seen = set()
    filtered = []
    # 允许的短读音（来自词库），避免误删如「生→う」
    allow_short = set(get_common_multireadings(surface))
    for r in readings:
        if not r:
            continue
        if contains_kanji(surface) and is_hiragana_text(r) and len(r) <= 1 and r not in allow_short:
            # 单假名且不在词库允许清单中，视为误切分噪声
            continue
        if r not in seen:
            seen.add(r)
            filtered.append(r)
    return filtered


# 浊/半浊音分组（首字变体，用于与后续送假名对齐时的容错过滤）
_HIRA_VOICING_GROUPS = [
    ['か','が'], ['き','ぎ'], ['く','ぐ'], ['け','げ'], ['こ','ご'],
    ['さ','ざ'], ['し','じ'], ['す','ず'], ['せ','ぜ'], ['そ','ぞ'],
    ['た','だ'], ['ち','ぢ'], ['つ','づ'], ['て','で'], ['と','ど'],
    ['は','ば','ぱ'], ['ひ','び','ぴ'], ['ふ','ぶ','ぷ'], ['へ','べ','ぺ'], ['ほ','ぼ','ぽ'],
    ['う','ゔ']
]

def voicing_variants(h: str) -> set:
    """返回该平假名在清音/浊音/半浊音中的变体集合（若有）。"""
    if not h:
        return set()
    for grp in _HIRA_VOICING_GROUPS:
        if h in grp:
            return set(grp)
    return {h}


def smart_tokenize(text, tokenizer_obj):
    """智能分词，优化日语注音的分词精度"""
    # 对于歌词，使用模式B通常能得到更好的结果
    # 模式A过于粗糙，模式C过于细致
    return tokenizer_obj.tokenize(text, tokenizer.Tokenizer.SplitMode.B)

def should_skip_alternatives(pos0: str, surface: str) -> bool:
    """助詞・助動詞・補助記号・純ひらがな等は多音候補を出さない"""
    if pos0 in ("助詞", "助動詞", "補助記号"):
        return True
    # 純ひらがなは候補不要（片仮名は UI オプションで制御）
    if is_hiragana_text(surface):
        return True
    return False

# --- 英文单词 -> かな 的简易回退 ---
_VOWELS = ['a','e','i','o','u']
_ROW_KATA = {
    'k': ['カ','ケ','キ','コ','ク'],  # 将索引按 a,e,i,o,u 顺序映射
    's': ['サ','セ','シ','ソ','ス'],
    't': ['タ','テ','チ','ト','ツ'],
    'n': ['ナ','ネ','ニ','ノ','ヌ'],
    'h': ['ハ','ヘ','ヒ','ホ','フ'],
    'm': ['マ','メ','ミ','モ','ム'],
    'y': ['ヤ','イェ','イ','ヨ','ユ'],
    'r': ['ラ','レ','リ','ロ','ル'],
    'l': ['ラ','レ','リ','ロ','ル'],
    'w': ['ワ','ウェ','ウィ','ウォ','ウ'],
    'g': ['ガ','ゲ','ギ','ゴ','グ'],
    'z': ['ザ','ゼ','ジ','ゾ','ズ'],
    'd': ['ダ','デ','ヂ','ド','ヅ'],
    'b': ['バ','ベ','ビ','ボ','ブ'],
    'p': ['パ','ペ','ピ','ポ','プ'],
    'f': ['ファ','フェ','フィ','フォ','フ'],
    'v': ['ヴァ','ヴェ','ヴィ','ヴォ','ヴ'],
    'j': ['ジャ','ジェ','ジ','ジョ','ジュ'],
    'c': ['カ','セ','シ','コ','ク'],
}
_V_KATA = {'a':'ア','e':'エ','i':'イ','o':'オ','u':'ウ'}
_DIGRAPH = {
    'tion':'ション','sion':'ジョン','ch':'チ','sh':'シ','th':'ス','ph':'フ','wh':'ウ','ck':'ック','ng':'ング','qu':'ク','ts':'ツ'
}

def english_to_katakana(word: str) -> str:
    s = re.sub(r"[^A-Za-z]","", word or "")
    if not s:
        return ""
    s = s.lower()
    out = []
    i = 0
    # 尾部规则
    if s.endswith('ing'):
        s = s[:-3] + 'ing'  # 保持
    while i < len(s):
        # digraphs
        matched = False
        for L in (5,4,3,2):
            if i+L <= len(s):
                chunk = s[i:i+L]
                if chunk in _DIGRAPH:
                    out.append(_DIGRAPH[chunk])
                    i += L
                    matched = True
                    break
        if matched:
            continue
        ch = s[i]
        # 末尾 er → アー
        if ch == 'e' and i == len(s)-2 and s.endswith('er'):
            out.append('アー')
            break
        # 元音
        if ch in _VOWELS:
            kat = _V_KATA[ch]
            # 连续元音视为长音
            j = i+1
            while j < len(s) and s[j] in _VOWELS:
                j += 1
            if j - i >= 2:
                out.append(kat + 'ー')
                i = j
                continue
            out.append(kat)
            i += 1
            continue
        # 子音 + 元音
        if i+1 < len(s) and s[i+1] in _VOWELS:
            row = _ROW_KATA.get(ch)
            if row:
                v = s[i+1]
                idx = _VOWELS.index(v)
                out.append(row[idx])
                i += 2
                continue
        # 促音（子音重叠）
        if i+1 < len(s) and s[i] == s[i+1] and s[i] not in _VOWELS and s[i] != 'n':
            out.append('ッ')
            i += 1
            continue
        # 单独子音
        # 用行的ウ列兜底
        row = _ROW_KATA.get(ch)
        if row:
            out.append(row[4])
        elif ch == 'x':
            out.append('クス')
        elif ch == 'q':
            out.append('ク')
        elif ch == 'n':
            out.append('ン')
        i += 1
    katakana = ''.join(out)
    return katakana

def english_to_hiragana(word: str) -> str:
    # 1) 词表优先（可维护高质量词条）
    if ENGLISH_KANA_DICT:
        key = (word or '').lower()
        kana = ENGLISH_KANA_DICT.get(key)
        if kana:
            return katakana_to_hiragana(kana)

    mode = ENG_KANA_MODE
    # 2) 预留 g2p 管道（如安装 g2p-en / phonemizer 可在此接入）
    if mode in ('auto','g2p'):
        try:
            # 占位：若未来接入 g2p-en，可在此把 english -> IPA -> katakana
            pass
        except Exception:
            pass

    # 3) 简易规则回退
    kat = english_to_katakana(word)
    return katakana_to_hiragana(kat)

def english_wordlist_to_hiragana(word: str) -> str:
    """仅使用本地词表进行英→かな转换；未命中则返回空。"""
    key = (word or '').lower()
    kana = ENGLISH_KANA_DICT.get(key) if ENGLISH_KANA_DICT else None
    return katakana_to_hiragana(kana) if kana else ""

# 已弃用：旧版多音候选收集函数（保留在历史中）。

def get_alternative_readings_with_primary(surface, primary_reading, tokenizer_obj, context):
    """获取多音字选项，特殊处理某些容易误读的词汇"""
    readings = []
    best_reading = primary_reading
    
    # 特殊处理"如何"这个词
    if surface == "如何":
        word_pos = context.find(surface)
        if word_pos != -1:
            after_word = context[word_pos + len(surface):word_pos + len(surface) + 6]  # 取后6个字符
            before_word = context[max(0, word_pos - 3):word_pos]  # 取前3个字符
            
            # 在以下情况下，"如何"读作"どう"（副词用法）：
            if (after_word.startswith("か") or      # 如何か
                after_word.startswith("し") or      # 如何し
                after_word.startswith("だ") or      # 如何だ
                after_word.startswith("考え") or    # 如何考える
                after_word.startswith("思") or      # 如何思う
                "思う" in context or               # 包含思考动词
                "考え" in context):               # 包含思考动词
                best_reading = "どう"
            elif after_word.startswith("です"):    # 如何ですか
                best_reading = "いかが"
            # 其他情况保持原读音
    
    # 对于其他词汇，尝试在更小的上下文中重新分析
    elif primary_reading == "いかん" and surface in ["如何"]:  # 可以扩展到其他类似词汇
        try:
            # 只分析这个词加上紧随其后的2-3个字符
            word_pos = context.find(surface)
            if word_pos != -1:
                end_pos = min(len(context), word_pos + len(surface) + 3)
                minimal_context = context[word_pos:end_pos]
                
                # 用最小上下文重新分词
                minimal_tokens = tokenizer_obj.tokenize(minimal_context, tokenizer.Tokenizer.SplitMode.A)
                
                for token in minimal_tokens:
                    if token.surface() == surface:
                        minimal_reading = token.reading_form()
                        if minimal_reading and minimal_reading != "*":
                            minimal_reading_hiragana = katakana_to_hiragana(minimal_reading)
                            best_reading = minimal_reading_hiragana
                            break
        except:
            pass
    
    # 添加最佳读音
    if best_reading:
        readings.append(best_reading)
    
    # 短语级覆盖：若该 surface 命中短语优先表，追加并置顶（现代歌词优先）
    try:
        phrase = PHRASE_OVERRIDE_READINGS.get(surface)
        if phrase:
            # 先把短语读音追加
            for r in phrase:
                if r not in readings:
                    readings.append(r)
            # 置顶短语首选
            readings = [phrase[0]] + [r for r in readings if r != phrase[0]]
    except Exception:
        pass

    # 只有对于预设的常见多音字，才添加其他读音选项
    common_multireadings = get_common_multireadings(surface)
    if common_multireadings:
        for alt_reading in common_multireadings:
            if alt_reading not in readings:
                readings.append(alt_reading)

    # 通用候选收集：对该词在不同分词模式下的读音（避免漏掉其他可行读音）
    try:
        alt_set = set(readings)
        for split_mode in [tokenizer.Tokenizer.SplitMode.A,
                           tokenizer.Tokenizer.SplitMode.B,
                           tokenizer.Tokenizer.SplitMode.C]:
            tokens = tokenizer_obj.tokenize(surface, split_mode)
            for token in tokens:
                if token.surface() == surface:
                    r = token.reading_form()
                    if r and r != "*":
                        alt_set.add(katakana_to_hiragana(r))
        # 重新排序：最佳读音优先，其余按长度/字典序稳定输出
        merged = [best_reading] + [r for r in sorted(alt_set, key=lambda x: (len(x), x)) if r != best_reading]
    except Exception:
        merged = readings if readings else [best_reading] if best_reading else []
    
    return filter_alternative_readings(surface, merged)

def get_common_multireadings(surface):
    """返回常见多音字的已知读音选项"""
    # 这里添加一些常见的多音字及其读音
    multireadings_dict = {
        "生": ["せい", "なま", "き", "う"],
        "上": ["うえ", "じょう", "あ", "のぼ"],
        "下": ["した", "げ", "か", "お", "さ", "くだ"],
        "中": ["なか", "ちゅう", "じゅう"],
        "大": ["おお", "だい", "たい"],
        "小": ["ちい", "こ", "しょう"],
        "人": ["ひと", "じん", "にん"],
        "日": ["ひ", "にち", "か"],
        "月": ["つき", "げつ", "がつ"],
        "年": ["とし", "ねん"],
        "時": ["とき", "じ"],
        "分": ["ぶん", "ふん", "わ"],
        "間": ["あいだ", "かん", "ま"],
        "手": ["て", "しゅ"],
        "口": ["くち", "こう", "ぐち"],
        "目": ["め", "ま", "もく", "ぼく"],
        "心": ["こころ", "しん"],
        "気": ["き", "け"],
        "水": ["みず", "すい"],
        "火": ["ひ", "か"],
        "土": ["つち", "ど", "と"],
        "金": ["かね", "きん", "こん"],
        "木": ["き", "もく", "ぼく"],
        "花": ["はな", "か"],
        "山": ["やま", "さん", "ざん"],
        "川": ["かわ", "せん"],
        "海": ["うみ", "かい"],
        "空": ["そら", "くう", "から"],
        "風": ["かぜ", "ふう"],
        "雨": ["あめ", "う"],
        "雪": ["ゆき", "せつ"],
        "星": ["ほし", "せい", "しょう"],
        "光": ["ひかり", "こう"],
        "音": ["おと", "おん", "いん"],
        "色": ["いろ", "しょく", "しき"],
        "行": ["い", "ゆ", "こう", "ぎょう"],
        "来": ["く", "こ", "らい"],
        "出": ["で", "だ", "しゅつ"],
        "入": ["はい", "い", "にゅう"],
        "立": ["た", "りつ", "りゅう"],
        "止": ["と", "し"],
        "走": ["はし", "そう"],
        "見": ["み", "けん"],
        "聞": ["き", "ぶん", "もん"],
        "言": ["い", "こと", "げん", "ごん"],
        "話": ["はな", "はなし", "わ"],
        "読": ["よ", "どく", "とく"],
        "書": ["か", "しょ"],
        "学": ["まな", "がく"],
        "校": ["こう"],
        "先": ["さき", "せん"],
        "青": ["あお", "せい", "しょう"],
        "赤": ["あか", "せき", "しゃく"],
        "白": ["しろ", "はく", "びゃく"],
        "黒": ["くろ", "こく"],
        "新": ["あたら", "しん"],
        "古": ["ふる", "こ"],
        "長": ["なが", "ちょう"],
        "短": ["みじか", "たん"],
        "高": ["たか", "こう"],
        "低": ["ひく", "てい"],
        "強": ["つよ", "きょう", "ごう"],
        "弱": ["よわ", "じゃく"],
        "重": ["おも", "じゅう", "ちょう"],
        "軽": ["かる", "けい"],
        "早": ["はや", "そう", "さっ"],
        "遅": ["おそ", "ち"],
        # 僕：仅保留可信读音（现代：ぼく；古语/训读：しもべ；古语一人称：やつがれ）
        "僕": ["ぼく", "しもべ", "やつがれ"],
    }

    # 外部库优先级更高：若存在，合并并去重
    external = EXTERNAL_KANJI_READINGS.get(surface, []) if isinstance(surface, str) else []
    base = multireadings_dict.get(surface, [])
    if external:
        seen = set()
        merged = []
        for r in external + base:
            if r and r not in seen:
                seen.add(r)
                merged.append(r)
        return merged
    return base

def get_reading_whitelist(surface: str) -> list:
    """对高频汉字提供有效读音白名单（按优先级）"""
    wl = {
        "東": ["とう", "ひがし", "あずま"],
        "西": ["せい", "さい", "にし"],
        "南": ["なん", "みなみ"],
        "北": ["ほく", "きた"],
        "行": ["こう", "ぎょう", "い", "ゆ"],
        "上": ["じょう", "うえ", "あ", "のぼ"],
        "下": ["か", "げ", "した", "さ", "お", "くだ"],
        "中": ["ちゅう", "なか", "じゅう"],
        "人": ["じん", "にん", "ひと"],
        "生": ["せい", "しょう", "なま", "き", "う"],
        "空": ["くう", "そら", "から"],
        "風": ["ふう", "かぜ"],
        "目": ["め", "ま", "もく", "ぼく"],
        "明": ["あく", "あくる", "あか", "めい"],
        "何": ["なに", "なん"],
        "見": ["み", "けん"],
        "失": ["しつ", "うしな", "うせ", "なく"],
        "時": ["じ", "とき"],
        "来": ["らい", "く", "こ"],
        "出": ["しゅつ", "で", "だ"],
        "入": ["にゅう", "はい", "い"],
        # 单字“僕”——现代常用读音与可接受的古语
        "僕": ["ぼく", "しもべ", "やつがれ"],
        # 皆：现代口语常作 みんな
        "皆": ["みんな", "みな", "みんなさん"],
    }
    return wl.get(surface, [])

def compose_whitelist_reading(surface: str) -> str:
    """若 surface 为多汉字组合，尝试按单字白名单首选读音组合一个候选读音。全部字符均有白名单时返回串接结果，否则返回空字符串。"""
    pieces = []
    for ch in surface:
        if contains_kanji(ch):
            wl = get_reading_whitelist(ch)
            if not wl:
                return ""
            pieces.append(wl[0])
        else:
            # 出现非汉字（假名/符号）则放弃组合
            return ""
    return "".join(pieces) if pieces else ""

def add_external_dictionary_candidates(surface: str, candidates: list) -> list:
    """融合外部词典候选（JMdict / Kanjidic2），统一转为平假名并合并去重。
    已移除对 UniDic-lite (fugashi) 的依赖。"""
    merged = list(candidates) if candidates else []
    seen = set(merged)
    # JMdict: 词形 -> [かな读法]
    try:
        jm = JMDICT_READINGS.get(surface)
        if jm:
            for r in jm:
                hira = katakana_to_hiragana(r)
                if hira and hira not in seen:
                    seen.add(hira)
                    merged.append(hira)
    except Exception:
        pass
    # Kanjidic2: 单字 -> [音/训读]
    try:
        if len(surface) == 1 and contains_kanji(surface):
            kj = KANJIDIC2_READINGS.get(surface)
            if kj:
                for r in kj:
                    hira = katakana_to_hiragana(r)
                    if hira and hira not in seen:
                        seen.add(hira)
                        merged.append(hira)
    except Exception:
        pass
    return merged

def _kanjidic_sets_for(kanji: str):
    """从 Kanjidic2 中提取该单字的音读/训读集合（平假名）。
    兼容两种 JSON 结构：
    1) {"漢": {"on": ["コウ"], "kun": ["い-く"]}}
    2) {"漢": ["コウ", "いく"]}（无类型信息）
    """
    try:
        data = KANJIDIC2_READINGS.get(kanji)
    except Exception:
        data = None
    on_set, kun_set = set(), set()
    if isinstance(data, dict):
        on_list = data.get('on') or data.get('on_readings') or []
        kun_list = data.get('kun') or data.get('kun_readings') or []
        for r in on_list:
            if r:
                on_set.add(katakana_to_hiragana(r))
        for r in kun_list:
            if r:
                kun_set.add(katakana_to_hiragana(r))
    elif isinstance(data, list):
        # 无类型信息，返回空集合以表示未知
        pass
    return on_set, kun_set

def sort_with_kun_priority(surface: str, candidates: list, default_reading: str, pos0: str, next_hira: str, token_full_reading: str):
    """简化排序：仅置顶默认读音，其余保持稳定顺序。"""
    ordered = []
    seen = set()
    if default_reading:
        ordered.append((default_reading, 'unknown'))
        seen.add(default_reading)
    for r in candidates:
        if r and r not in seen:
            ordered.append((r, 'unknown'))
    return ordered

def restrict_to_kanjidic_allowlist(surface: str, candidates: list, preferred: str) -> list:
    """若是单个汉字，则用 KANJIDIC2 + 白名单 作为允许集合进行裁剪，
    同时保留当前上下文读音 preferred。"""
    if not candidates:
        return candidates
    if not (len(surface) == 1 and contains_kanji(surface)):
        return candidates
    allow = set()
    try:
        kj = KANJIDIC2_READINGS.get(surface)
        if kj:
            allow.update(katakana_to_hiragana(r) for r in kj if r)
    except Exception:
        pass
    wl = get_reading_whitelist(surface) or []
    allow.update(wl)
    if preferred:
        allow.add(preferred)
    if not allow:
        return candidates
    # 按原顺序保留允许项
    filtered = [r for r in candidates if r in allow]
    return filtered or candidates

def filter_readings_for_shita(next_hira: str, candidates: list, preferred: str) -> list:
    """对『下』的读音进行基于上下文的剪裁：
    - 无送假名：保留 した/か/げ
    - さげ/さが 系：保留以『さ』起的读音（さげる/さがる 等）
    - くだ 系：保留以『くだ』起的读音（くだる/くだす/くださる 等）
    - おり/おろ 系：保留以『お』起的读音（おりる/おろす 等）
    始终保留 preferred。
    """
    if not candidates:
        return candidates
    if next_hira is None:
        next_hira = ""
    keep = set()
    nh = next_hira[:2]
    if not nh:
        keep.update(["した", "か", "げ"])
    else:
        if nh.startswith("げ") or nh.startswith("が"):
            keep.update([r for r in candidates if r.startswith("さ")])
        elif nh.startswith("だ") or nh.startswith("さ"):
            keep.update([r for r in candidates if r.startswith("くだ")])
        elif nh.startswith("り") or nh.startswith("ろ"):
            keep.update([r for r in candidates if r.startswith("お")])
    if preferred:
        keep.add(preferred)
    filtered = [r for r in candidates if r in keep] or candidates
    return filtered

def filter_readings_by_alignment(token_reading: str, next_hira: str, candidates: list, preferred: str, keep_always: list | None = None) -> list:
    """通用对齐规则：保留能与送假名拼接后匹配到 token 全读音前缀的候选。
    例：token=さげる, r=さ, next=げる => さ+げる 与 さげる 对齐, 保留。
    若 next_hira 为空，则保留能与 token_reading 前缀对齐的候选（如 した vs した）。
    始终保留 preferred。
    """
    if not candidates:
        return candidates
    if not token_reading:
        return candidates
    if next_hira is None:
        next_hira = ""
    # 若没有送假名/后续假名，则不要做对齐剪裁（以免名词类被误删）
    if next_hira == "":
        return candidates
    keep = set()
    for r in candidates:
        combo = r + next_hira
        if token_reading.startswith(combo) or token_reading == r:
            keep.add(r)
    if preferred:
        keep.add(preferred)
    # 保留白名单读音（即便未与 token_reading 对齐）
    if keep_always:
        for r in candidates:
            if r in keep_always:
                keep.add(r)
    filtered = [r for r in candidates if r in keep]
    return filtered or candidates

# --- 首页路由 ---
@app.route("/")
def index():
    return app.send_static_file('index.html')

# --- API 端点 ---
@app.route("/api/furigana", methods=["POST"])
def get_furigana():
    data = request.get_json()
    if not data or "lyrics" not in data:
        return jsonify({"error": "No lyrics provided"}), 400

    lyrics_text = data["lyrics"]
    want_katakana_conversion = bool(data.get("katakana", True))
    lines = lyrics_text.split('\n')
    
    processed_lines = []
    for line in lines:
        if not line.strip():
            processed_lines.append([])
            continue

        # 使用智能分词模式选择
        tokens = smart_tokenize(line, tokenizer_obj)
        line_result = []
        for idx, m in enumerate(tokens):
            surface = m.surface()
            reading = m.reading_form()
            pos = m.part_of_speech()
            
            reading_hiragana = ""
            alternative_readings = []

            if surface.isspace() or pos[0] == "補助記号":
                reading_hiragana = surface
            else:
                # 检查是否为片假名单词
                if is_all_katakana(surface) and len(surface) > 1:
                    # 如果开启转换，则生成平假名注音
                    if want_katakana_conversion:
                        reading_hiragana = katakana_to_hiragana(surface)
                    # 如果关闭转换，则不提供注音
                    else:
                        reading_hiragana = ""
                # 对于非片假名单词，使用 Sudachi 的读音
                else:
                    if reading and reading != "*":
                        reading_hiragana = katakana_to_hiragana(reading)
                        # 若 Sudachi 的 reading 仍是拉丁字母或与原文一致，则视为无有效读音，回退英→かな
                        if re.fullmatch(r"[A-Za-z]+", surface or "") and (reading.lower() == surface.lower() or re.fullmatch(r"[A-Za-z]+", reading or "")):
                            reading_hiragana = english_to_hiragana(surface)
                        # 助詞/助動詞/補助記号/純ひらがな：不出多音菜单
                        if should_skip_alternatives(pos[0], surface):
                            alternative_readings = []
                        # 只为汉字单词获取多音字选项，平假名单词不需要
                        elif contains_kanji(surface):
                            # 使用当前token的读音作为主要选择，而不是重新分析
                            alternative_readings = get_alternative_readings_with_primary(
                                surface,
                                reading_hiragana,
                                tokenizer_obj,
                                line,
                            )
                            # 融合外部词典候选（JMdict/Kanjidic2）
                            alternative_readings = add_external_dictionary_candidates(surface, alternative_readings)
                            # 若该汉字存在读音白名单，则与候选合并；保持“上下文读音优先”
                            white = get_reading_whitelist(surface)
                            if white:
                                merged = []
                                seen = set()
                                # 1) 先放置当前上下文读音（若有）
                                if reading_hiragana:
                                    merged.append(reading_hiragana)
                                    seen.add(reading_hiragana)
                                # 2) 再放白名单
                                for r in white:
                                    if r and r not in seen:
                                        seen.add(r)
                                        merged.append(r)
                                # 3) 最后放通用候选
                                for r in alternative_readings:
                                    if r and r not in seen:
                                        seen.add(r)
                                        merged.append(r)
                                alternative_readings = merged
                            # 针对“僕”等敏感字：如果外部词典带来了不可信的读音，依赖白名单进行剪裁
                            if surface == "僕":
                                allow = set(get_reading_whitelist(surface) or [])
                                if allow:
                                    alternative_readings = [r for r in alternative_readings if r in allow or r == reading_hiragana]
                            # 若为多汉字组合（且各字都在白名单），尝试拼接组合读音，并放到前列
                            combo = compose_whitelist_reading(surface)
                            if combo:
                                alternative_readings = [combo] + [r for r in alternative_readings if r != combo]
                            # 候选重排：已移除 KenLM，保持原有启发式顺序
                            # 全局防错：若为“单个汉字”，用 KANJIDIC2 + 白名单 作为允许集合剪裁候选
                            alternative_readings = restrict_to_kanjidic_allowlist(surface, alternative_readings, reading_hiragana)
                            # 全局对齐：按 token 的完整读音与后续送假名进行前缀对齐，保留能匹配的候选
                            nh = collect_next_hiragana(tokens, idx, max_chars=2)
                            token_full_reading = katakana_to_hiragana(reading) if reading and reading != "*" else reading_hiragana
                            # 皆：在非复合词、后续为助词/动词等情况下，常读作「みんな」。将其加入强保留清单
                            keep_always = []
                            if surface == "皆":
                                keep_always.append("みんな")
                            alternative_readings = filter_readings_by_alignment(token_full_reading or "", nh, alternative_readings, reading_hiragana, keep_always)
                            # 针对『下』：细化规则（在对齐规则之后进一步收敛）
                            if surface == "下":
                                alternative_readings = filter_readings_for_shita(nh, alternative_readings, reading_hiragana)
                            # 训读优先排序，并为候选打上音/训标签
                            if alternative_readings:
                                labeled_sorted = sort_with_kun_priority(surface, alternative_readings, reading_hiragana, pos[0], nh, token_full_reading or "")
                                alternative_readings = [r for r, t in labeled_sorted]
                                # 仍以上下文读音为默认；若无上下文读音，则取排序后首项
                                if reading_hiragana:
                                    reading_hiragana = reading_hiragana
                                else:
                                    reading_hiragana = alternative_readings[0]
                            else:
                                pass
                        # 单 token 内部“基字+送假名”容错过滤：若 surface 末尾带平假名，剔除把该送假名首字换成清/浊/半浊变体的候选
                        # 例：surface=一人ぼっち, reading=ひとりぼっち, 剔除 ひとりぽ/ひとりぽっち 这类候选
                        surf_tail = extract_trailing_hiragana(surface)
                        if surf_tail and reading_hiragana and reading_hiragana.endswith(surf_tail):
                            base = reading_hiragana[:-len(surf_tail)] if len(surf_tail) <= len(reading_hiragana) else reading_hiragana
                            vset = voicing_variants(surf_tail[0])
                            bad_forms = set()
                            for v in vset:
                                if v == surf_tail[0]:
                                    continue
                                bad_forms.add(base + v)
                                bad_forms.add(base + v + surf_tail[1:])
                            if bad_forms:
                                alternative_readings = [r for r in alternative_readings if r not in bad_forms]
                        # 规则：明くる → 「あくる」；当分词为单独「明」且后随「く/くる/る」时，明读作「あく」
                        if surface in {"明", "明くる", "明る"}:
                            n1 = tokens[idx + 1] if idx + 1 < len(tokens) else None
                            n2 = tokens[idx + 2] if idx + 2 < len(tokens) else None
                            n1s = n1.surface() if n1 else ""
                            n2s = n2.surface() if n2 else ""
                            if surface == "明くる" or (surface == "明る" and n1s in {"日", "朝", "年"}):
                                reading_hiragana = "あくる"
                            elif surface == "明" and (n1s in {"る", "く", "くる"} or (n1s == "く" and n2s == "る")):
                                # 「明」+「く/くる」→ 「あく」
                                reading_hiragana = "あく"
                            # 提供候选（防误拼：只针对当前词，不把后续送假名拼进候选）
                            if surface == "明" and reading_hiragana == "あく":
                                # 单独「明」后续含送假名时，不提供含送假名的候选，避免「あくるる」
                                cand = [reading_hiragana, "あか"]
                            elif reading_hiragana == "あくる":
                                cand = [reading_hiragana, "あかる"]
                            else:
                                cand = [reading_hiragana, "あか", "あかる"]
                            seen = set()
                            alternative_readings = [c for c in cand if c and not (c in seen or seen.add(c))]
                        # 特例："何" + 助词（も/か/が/を/に/へ/と）多为「なに」
                        if surface == "何":
                            next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
                            if next_token is not None:
                                next_surface = next_token.surface()
                                next_pos0 = next_token.part_of_speech()[0]
                                if next_pos0 == "助詞" and next_surface in {"も", "か", "が", "を", "に", "へ", "と"}:
                                    reading_hiragana = "なに"
                            # 方案B：无论上下文，始终提供「なに/なん」两个选项
                            alt_set = set(alternative_readings) if alternative_readings else set()
                            alt_set.update(["なに", "なん"])
                            # 优先把当前读音放在第一位
                            ordered = [reading_hiragana] + [r for r in alt_set if r != reading_hiragana]
                            alternative_readings = ordered
                        # 通用防误拼：若下一段连续平假名与当前读音拼接会形成“读音+送假名”模式，则从候选中移除这类合成项
                        next_hira = collect_next_hiragana(tokens, idx, max_chars=2)
                        if next_hira:
                            bad_suffixes = {next_hira, next_hira[:1]}
                            # 扩展：将送假名首字的浊/半浊音变体也视为不合法结尾（例：ぼ ↔ ぽ）
                            first = next_hira[0]
                            variants = voicing_variants(first)
                            for v in variants:
                                bad_suffixes.add(v)
                                if len(next_hira) > 1:
                                    bad_suffixes.add(v + next_hira[1:])
                            alternative_readings = [r for r in alternative_readings if not any(r.endswith(suf) for suf in bad_suffixes if suf)]
                            # 进一步：若候选恰为「默认读音 + (送假名首字的变体)」，同样剔除（例：ひとり + ぽ）
                            if reading_hiragana:
                                ban_heads = {reading_hiragana + v for v in variants}
                                alternative_readings = [r for r in alternative_readings if r not in ban_heads]
                            # 同步更新排序
                            try:
                                labeled_sorted = sort_with_kun_priority(surface, alternative_readings, reading_hiragana, pos[0], next_hira, token_full_reading if 'token_full_reading' in locals() else '')
                                alternative_readings = [r for r, _t in labeled_sorted]
                            except Exception:
                                pass
                    else:
                        # Sudachi 无读音：仅当英文在本地词表命中时才转换，未命中则不注音
                        if re.fullmatch(r"[A-Za-z]+", surface):
                            reading_hiragana = english_wordlist_to_hiragana(surface)
                        else:
                            reading_hiragana = ""
            
            # 最后保障：若仍无读音且为英文字母词，执行英→かな回退
            if (not reading_hiragana) and re.fullmatch(r"[A-Za-z]+", surface or ""):
                # 最后保障：仍仅词表驱动，未命中则留空
                reading_hiragana = english_wordlist_to_hiragana(surface)
            
            line_result.append({
                "surface": surface,
                "reading": reading_hiragana,
                "alternatives": alternative_readings,
                "has_alternatives": len(alternative_readings) > 1
            })
        processed_lines.append(line_result)
    
    return jsonify(processed_lines)

if __name__ == "__main__":
    app.run(debug=True, port=5000)