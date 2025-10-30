"""
文本处理工具模块
包含汉字检测、假名提取等文本处理功能
"""
from typing import List, Set


def contains_kanji(text: str) -> bool:
    """
    检测文本是否包含汉字
    
    Args:
        text: 待检查的文本
        
    Returns:
        True如果包含汉字，否则False
    """
    for char in text:
        # 汉字的Unicode范围
        if ('\u4e00' <= char <= '\u9fff' or  # CJK统一汉字
            '\u3400' <= char <= '\u4dbf' or  # CJK扩展A
            '\uf900' <= char <= '\ufaff'):   # CJK兼容汉字
            return True
    return False


def extract_trailing_hiragana(text: str) -> str:
    """
    提取文本结尾连续的平假名串
    
    Args:
        text: 输入文本
        
    Returns:
        结尾的平假名串，如果没有则返回空字符串
    """
    if not text:
        return ""
    i = len(text) - 1
    while i >= 0 and ('\u3040' <= text[i] <= '\u309f'):
        i -= 1
    return text[i+1:]


def collect_next_hiragana(tokens: List, current_index: int, max_chars: int = 2) -> str:
    """
    从当前token之后收集连续的平假名（排除助词/助动词/符号）
    
    Args:
        tokens: token列表
        current_index: 当前token的索引
        max_chars: 最多收集的字符数
        
    Returns:
        收集到的平假名字符串
    """
    from .kana_converter import is_hiragana_text
    
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


def voicing_variants(h: str) -> Set[str]:
    """
    返回该平假名的清音/浊音/半浊音变体集合
    
    Args:
        h: 平假名字符
        
    Returns:
        变体字符集合
    """
    # 浊/半浊音分组
    _HIRA_VOICING_GROUPS = [
        ['か','が'], ['き','ぎ'], ['く','ぐ'], ['け','げ'], ['こ','ご'],
        ['さ','ざ'], ['し','じ'], ['す','ず'], ['せ','ぜ'], ['そ','ぞ'],
        ['た','だ'], ['ち','ぢ'], ['つ','づ'], ['て','で'], ['と','ど'],
        ['は','ば','ぱ'], ['ひ','び','ぴ'], ['ふ','ぶ','ぷ'], 
        ['へ','べ','ぺ'], ['ほ','ぼ','ぽ'], ['う','ゔ']
    ]
    
    if not h:
        return set()
    for grp in _HIRA_VOICING_GROUPS:
        if h in grp:
            return set(grp)
    return {h}

