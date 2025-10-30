"""
读音处理服务模块
处理日语文本的读音生成、多音字处理等核心业务逻辑
"""
import logging
from typing import List, Dict, Optional, Tuple, Set
from sudachipy import tokenizer

from utils.kana_converter import katakana_to_hiragana, is_hiragana_text
from utils.text_processor import (
    contains_kanji, extract_trailing_hiragana, 
    collect_next_hiragana, voicing_variants
)
from services.dictionary_service import dictionary_service
from services.tokenizer_service import tokenizer_service


logger = logging.getLogger(__name__)


class ReadingService:
    """读音处理服务类"""
    
    def __init__(self):
        self.dict_service = dictionary_service
        self.tokenizer = tokenizer_service
    
    def get_common_multireadings(self, surface: str) -> List[str]:
        """
        返回常见多音字的已知读音选项
        
        Args:
            surface: 词表面形式
            
        Returns:
            读音列表
        """
        # 内置常见多音字字典
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
            "僕": ["ぼく", "しもべ", "やつがれ"],
            "皆": ["みんな", "みな"],
            # ... 更多多音字
        }
        
        # 优先使用外部词典
        external = self.dict_service.get_kanji_readings(surface)
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
    
    def get_reading_whitelist(self, surface: str) -> List[str]:
        """
        获取高频汉字的有效读音白名单（按优先级）
        
        Args:
            surface: 词表面形式
            
        Returns:
            读音白名单列表
        """
        whitelist = {
            "東": ["とう", "ひがし", "あずま"],
            "西": ["せい", "さい", "にし"],
            "南": ["なん", "みなみ"],
            "北": ["ほく", "きた"],
            "行": ["こう", "ぎょう", "い", "ゆ"],
            "僕": ["ぼく", "しもべ", "やつがれ"],
            "皆": ["みんな", "みな", "みんなさん"],
            "何": ["なに", "なん"],
            # ... 更多白名单
        }
        return whitelist.get(surface, [])
    
    def filter_alternative_readings(
        self, 
        surface: str, 
        readings: List[str]
    ) -> List[str]:
        """
        过滤无效的候选读音
        
        Args:
            surface: 词表面形式
            readings: 原始读音列表
            
        Returns:
            过滤后的读音列表
        """
        if not readings:
            return readings
        
        seen = set()
        filtered = []
        allow_short = set(self.get_common_multireadings(surface))
        
        for r in readings:
            if not r:
                continue
            # 过滤明显无效的单假名候选
            if (contains_kanji(surface) and is_hiragana_text(r) and 
                len(r) <= 1 and r not in allow_short):
                continue
            if r not in seen:
                seen.add(r)
                filtered.append(r)
        
        return filtered
    
    def add_external_dictionary_candidates(
        self, 
        surface: str, 
        candidates: List[str]
    ) -> List[str]:
        """
        融合外部词典候选读音
        
        Args:
            surface: 词表面形式
            candidates: 现有候选列表
            
        Returns:
            合并后的候选列表
        """
        merged = list(candidates) if candidates else []
        seen = set(merged)
        
        # JMdict读音
        jm = self.dict_service.get_jmdict_readings(surface)
        if jm:
            for r in jm:
                hira = katakana_to_hiragana(r)
                if hira and hira not in seen:
                    seen.add(hira)
                    merged.append(hira)
        
        # Kanjidic2读音（仅单字）
        if len(surface) == 1 and contains_kanji(surface):
            kj_data = self.dict_service.get_kanjidic2_readings(surface)
            if kj_data:
                kj_list = kj_data if isinstance(kj_data, list) else []
                for r in kj_list:
                    hira = katakana_to_hiragana(r)
                    if hira and hira not in seen:
                        seen.add(hira)
                        merged.append(hira)
        
        return merged
    
    def restrict_to_kanjidic_allowlist(
        self,
        surface: str,
        candidates: List[str],
        preferred: str
    ) -> List[str]:
        """
        对单个汉字使用Kanjidic2和白名单进行候选裁剪
        
        Args:
            surface: 词表面形式
            candidates: 候选读音列表
            preferred: 首选读音
            
        Returns:
            裁剪后的候选列表
        """
        if not candidates:
            return candidates
        if not (len(surface) == 1 and contains_kanji(surface)):
            return candidates
        
        allow = set()
        
        # 从Kanjidic2获取允许的读音
        kj_data = self.dict_service.get_kanjidic2_readings(surface)
        if kj_data:
            kj_list = kj_data if isinstance(kj_data, list) else []
            allow.update(katakana_to_hiragana(r) for r in kj_list if r)
        
        # 添加白名单
        wl = self.get_reading_whitelist(surface) or []
        allow.update(wl)
        
        # 保留首选读音
        if preferred:
            allow.add(preferred)
        
        if not allow:
            return candidates
        
        # 按原顺序过滤
        filtered = [r for r in candidates if r in allow]
        return filtered or candidates
    
    def get_alternative_readings_with_primary(
        self,
        surface: str,
        primary_reading: str,
        context: str
    ) -> List[str]:
        """
        获取多音字的所有候选读音（含首选读音）
        
        Args:
            surface: 词表面形式
            primary_reading: 主要读音
            context: 上下文文本
            
        Returns:
            候选读音列表（按优先级排序）
        """
        readings = []
        best_reading = primary_reading
        
        # 特殊处理"如何"这个词
        if surface == "如何":
            best_reading = self._handle_nani_reading(surface, context, primary_reading)
        
        # 添加最佳读音
        if best_reading:
            readings.append(best_reading)
        
        # 短语级覆盖
        phrase = self.dict_service.get_phrase_override(surface)
        if phrase:
            for r in phrase:
                if r not in readings:
                    readings.append(r)
            # 置顶短语首选
            readings = [phrase[0]] + [r for r in readings if r != phrase[0]]
        
        # 添加常见多音字读音
        common_multireadings = self.get_common_multireadings(surface)
        if common_multireadings:
            for alt_reading in common_multireadings:
                if alt_reading not in readings:
                    readings.append(alt_reading)
        
        # 通用候选收集（不同分词模式）
        try:
            alt_set = set(readings)
            for mode in ['A', 'B', 'C']:
                tokens = self.tokenizer.tokenize(surface, mode)
                for token in tokens:
                    if token.surface() == surface:
                        r = token.reading_form()
                        if r and r != "*":
                            alt_set.add(katakana_to_hiragana(r))
            
            # 重新排序
            merged = [best_reading] + [
                r for r in sorted(alt_set, key=lambda x: (len(x), x)) 
                if r != best_reading
            ]
        except Exception as e:
            logger.warning(f"收集候选读音时出错: {e}")
            merged = readings if readings else [best_reading] if best_reading else []
        
        return self.filter_alternative_readings(surface, merged)
    
    def _handle_nani_reading(
        self, 
        surface: str, 
        context: str, 
        primary_reading: str
    ) -> str:
        """
        特殊处理"如何"的读音选择
        
        Args:
            surface: 词表面形式
            context: 上下文
            primary_reading: 原始读音
            
        Returns:
            优化后的读音
        """
        word_pos = context.find(surface)
        if word_pos == -1:
            return primary_reading
        
        after_word = context[word_pos + len(surface):word_pos + len(surface) + 6]
        
        # 在特定上下文中，"如何"读作"どう"
        if (after_word.startswith("か") or after_word.startswith("し") or
            after_word.startswith("だ") or after_word.startswith("考え") or
            after_word.startswith("思") or "思う" in context or "考え" in context):
            return "どう"
        elif after_word.startswith("です"):
            return "いかが"
        
        return primary_reading
    
    def should_skip_alternatives(self, pos0: str, surface: str) -> bool:
        """
        判断是否跳过多音候选
        
        Args:
            pos0: 词性
            surface: 词表面形式
            
        Returns:
            True如果应该跳过
        """
        if pos0 in ("助詞", "助動詞", "補助記号"):
            return True
        if is_hiragana_text(surface):
            return True
        return False


# 全局读音服务实例
reading_service = ReadingService()

