"""
API路由定义
处理/api/furigana端点的请求
"""
import logging
import re
from typing import List, Dict, Any
from flask import Blueprint, request, jsonify

from config import config
from utils.kana_converter import (
    katakana_to_hiragana, is_all_katakana, is_hiragana_text
)
from utils.text_processor import contains_kanji, collect_next_hiragana
from services.tokenizer_service import tokenizer_service
from services.reading_service import reading_service


logger = logging.getLogger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/furigana', methods=['POST'])
def get_furigana() -> tuple:
    """
    获取日语文本的假名注音
    
    请求体:
        {
            "lyrics": "日语文本",
            "katakana": true/false
        }
    
    返回:
        按行返回的token列表，每个token包含:
        - surface: 词表面形式
        - reading: 读音
        - alternatives: 备选读音列表
        - has_alternatives: 是否有多个读音
    """
    try:
        data = request.get_json()
        
        if not data or "lyrics" not in data:
            return jsonify({"error": "缺少lyrics参数"}), 400
        
        lyrics_text = data["lyrics"]
        
        # 验证文本类型
        if not isinstance(lyrics_text, str):
            return jsonify({"error": "lyrics参数必须是字符串类型"}), 400
        
        # 验证文本长度
        if len(lyrics_text) > config.MAX_TEXT_LENGTH:
            return jsonify({
                "error": f"文本过长，最大长度为{config.MAX_TEXT_LENGTH}字符"
            }), 400
        
        want_katakana_conversion = bool(data.get("katakana", True))
        lines = lyrics_text.split('\n')
        
        processed_lines = []
        
        for line in lines:
            if not line.strip():
                processed_lines.append([])
                continue
            
            # 使用智能分词
            tokens = tokenizer_service.smart_tokenize(line)
            line_result = []
            
            for idx, m in enumerate(tokens):
                surface = m.surface()
                reading = m.reading_form()
                pos = m.part_of_speech()
                
                reading_hiragana = ""
                alternative_readings = []
                
                # 处理空白和符号
                if surface.isspace() or pos[0] == "補助記号":
                    reading_hiragana = surface
                else:
                    # 检查是否为片假名单词
                    if is_all_katakana(surface) and len(surface) > 1:
                        if want_katakana_conversion:
                            reading_hiragana = katakana_to_hiragana(surface)
                        else:
                            reading_hiragana = ""
                    # 非片假名单词
                    else:
                        if reading and reading != "*":
                            reading_hiragana = katakana_to_hiragana(reading)
                            
                            # 英文不注音
                            if re.fullmatch(r"[A-Za-z\s]+", surface or ""):
                                reading_hiragana = ""
                            
                            # 助词/助动词/符号/纯假名不出多音菜单
                            if reading_service.should_skip_alternatives(pos[0], surface):
                                alternative_readings = []
                            # 为汉字单词获取多音字选项
                            elif contains_kanji(surface):
                                alternative_readings = reading_service.get_alternative_readings_with_primary(
                                    surface,
                                    reading_hiragana,
                                    line
                                )
                                
                                # 融合外部词典
                                alternative_readings = reading_service.add_external_dictionary_candidates(
                                    surface, 
                                    alternative_readings
                                )
                                
                                # 白名单合并
                                white = reading_service.get_reading_whitelist(surface)
                                if white:
                                    alternative_readings = _merge_with_whitelist(
                                        reading_hiragana,
                                        white,
                                        alternative_readings
                                    )
                                
                                # 特殊字符处理
                                if surface == "僕":
                                    allow = set(reading_service.get_reading_whitelist(surface) or [])
                                    if allow:
                                        alternative_readings = [
                                            r for r in alternative_readings 
                                            if r in allow or r == reading_hiragana
                                        ]
                                
                                # 全局裁剪
                                alternative_readings = reading_service.restrict_to_kanjidic_allowlist(
                                    surface, 
                                    alternative_readings, 
                                    reading_hiragana
                                )
                                
                                # 特殊词汇处理
                                alternative_readings, reading_hiragana = _handle_special_words(
                                    surface, tokens, idx, reading_hiragana, alternative_readings
                                )
                                
                                # 过滤候选
                                alternative_readings = _filter_with_context(
                                    tokens, idx, reading, reading_hiragana, 
                                    surface, alternative_readings
                                )
                        else:
                            reading_hiragana = ""
                
                line_result.append({
                    "surface": surface,
                    "reading": reading_hiragana,
                    "alternatives": alternative_readings,
                    "has_alternatives": len(alternative_readings) > 1
                })
            
            processed_lines.append(line_result)
        
        return jsonify(processed_lines)
    
    except Exception as e:
        logger.error(f"处理请求时发生错误: {e}", exc_info=True)
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


def _merge_with_whitelist(
    reading_hiragana: str,
    white: List[str],
    alternative_readings: List[str]
) -> List[str]:
    """合并白名单和候选读音"""
    merged = []
    seen = set()
    
    # 1) 先放当前上下文读音
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
    
    return merged


def _handle_special_words(
    surface: str,
    tokens: List,
    idx: int,
    reading_hiragana: str,
    alternative_readings: List[str]
) -> tuple:
    """
    处理特殊词汇的读音
    返回: (alternative_readings, reading_hiragana)
    """
    from utils.text_processor import extract_trailing_hiragana, voicing_variants
    
    # 1. 送假名内部容错过滤
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
    
    # 2. "明"字特殊处理
    if surface in {"明", "明くる", "明る"}:
        n1 = tokens[idx + 1] if idx + 1 < len(tokens) else None
        n2 = tokens[idx + 2] if idx + 2 < len(tokens) else None
        n1s = n1.surface() if n1 else ""
        n2s = n2.surface() if n2 else ""
        
        if surface == "明くる" or (surface == "明る" and n1s in {"日", "朝", "年"}):
            reading_hiragana = "あくる"
        elif surface == "明" and (n1s in {"る", "く", "くる"} or (n1s == "く" and n2s == "る")):
            reading_hiragana = "あく"
        
        # 提供候选
        if surface == "明" and reading_hiragana == "あく":
            cand = [reading_hiragana, "あか"]
        elif reading_hiragana == "あくる":
            cand = [reading_hiragana, "あかる"]
        else:
            cand = [reading_hiragana, "あか", "あかる"]
        
        seen = set()
        alternative_readings = [c for c in cand if c and not (c in seen or seen.add(c))]
    
    # 3. "何"字特殊处理
    if surface == "何":
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
        if next_token is not None:
            next_surface = next_token.surface()
            next_pos0 = next_token.part_of_speech()[0]
            if next_pos0 == "助詞" and next_surface in {"も", "か", "が", "を", "に", "へ", "と"}:
                reading_hiragana = "なに"
        
        # 始终提供「なに/なん」两个选项
        alt_set = set(alternative_readings) if alternative_readings else set()
        alt_set.update(["なに", "なん"])
        ordered = [reading_hiragana] + [r for r in alt_set if r != reading_hiragana]
        alternative_readings = ordered
    
    return alternative_readings, reading_hiragana


def _filter_with_context(
    tokens: List,
    idx: int,
    reading: str,
    reading_hiragana: str,
    surface: str,
    alternative_readings: List[str]
) -> List[str]:
    """基于上下文过滤候选读音"""
    from utils.text_processor import voicing_variants
    
    # 收集后续平假名
    next_hira = collect_next_hiragana(tokens, idx, max_chars=2)
    
    # 特殊处理：皆
    keep_always = []
    if surface == "皆":
        keep_always.append("みんな")
    
    # 通用防误拼
    if next_hira:
        bad_suffixes = {next_hira, next_hira[:1]}
        
        # 浊音变体
        first = next_hira[0]
        variants = voicing_variants(first)
        for v in variants:
            bad_suffixes.add(v)
            if len(next_hira) > 1:
                bad_suffixes.add(v + next_hira[1:])
        
        alternative_readings = [
            r for r in alternative_readings 
            if not any(r.endswith(suf) for suf in bad_suffixes if suf)
        ]
        
        # 进一步过滤：默认读音 + 变体
        if reading_hiragana:
            ban_heads = {reading_hiragana + v for v in variants}
            alternative_readings = [r for r in alternative_readings if r not in ban_heads]
    
    return alternative_readings

