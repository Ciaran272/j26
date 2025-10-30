"""
假名转换工具模块
处理片假名和平假名之间的转换
"""
from typing import Optional


def katakana_to_hiragana(katakana_string: str) -> str:
    """
    将片假名转换为平假名
    
    Args:
        katakana_string: 片假名字符串
        
    Returns:
        转换后的平假名字符串
    """
    hiragana_string = ""
    for char in katakana_string:
        if 'ァ' <= char <= 'ヶ':
            hiragana_char = chr(ord(char) - 96)
            hiragana_string += hiragana_char
        else:
            hiragana_string += char
    return hiragana_string


def is_all_katakana(text: str) -> bool:
    """
    检查文本是否全部为片假名
    
    Args:
        text: 待检查的文本
        
    Returns:
        True如果全部为片假名，否则False
    """
    if not text:
        return False
    for char in text:
        if not ('ァ' <= char <= 'ヶ' or char == 'ー'):
            return False
    return True


def is_hiragana(char: str) -> bool:
    """
    检查字符是否为平假名
    
    Args:
        char: 单个字符
        
    Returns:
        True如果是平假名，否则False
    """
    return '\u3040' <= char <= '\u309f'


def is_hiragana_text(text: str) -> bool:
    """
    检查文本是否全部为平假名
    
    Args:
        text: 待检查的文本
        
    Returns:
        True如果全部为平假名，否则False
    """
    if not text:
        return False
    for ch in text:
        if not ('\u3040' <= ch <= '\u309f'):
            return False
    return True


def is_katakana(text: str) -> bool:
    """
    检查文本是否为片假名（支持长音符）
    
    Args:
        text: 待检查的文本
        
    Returns:
        True如果是片假名，否则False
    """
    if not text:
        return False
    for char in text:
        if not ('\u30A0' <= char <= '\u30FF' or char == '\u30FC'):
            return False
    return True

