"""
分词服务模块
封装Sudachi分词器的使用
"""
import logging
from typing import List
from sudachipy import tokenizer, dictionary


logger = logging.getLogger(__name__)


class TokenizerService:
    """分词服务类"""
    
    def __init__(self, dict_type: str = "full"):
        """
        初始化分词器
        
        Args:
            dict_type: 词典类型，可选 "small", "core", "full"
        """
        try:
            self.tokenizer_obj = dictionary.Dictionary(dict_type=dict_type).create()
            logger.info(f"✓ Sudachi分词器初始化成功 (dict_type={dict_type})")
        except Exception as e:
            logger.error(f"✗ Sudachi分词器初始化失败: {e}")
            raise
    
    def tokenize(
        self, 
        text: str, 
        mode: str = 'B'
    ) -> List:
        """
        对文本进行分词
        
        Args:
            text: 输入文本
            mode: 分词模式 'A' (短单元), 'B' (中等), 'C' (长单元)
            
        Returns:
            Token列表
        """
        mode_map = {
            'A': tokenizer.Tokenizer.SplitMode.A,
            'B': tokenizer.Tokenizer.SplitMode.B,
            'C': tokenizer.Tokenizer.SplitMode.C
        }
        
        split_mode = mode_map.get(mode, tokenizer.Tokenizer.SplitMode.B)
        return self.tokenizer_obj.tokenize(text, split_mode)
    
    def smart_tokenize(self, text: str) -> List:
        """
        智能分词，自动选择最佳分词模式
        对于歌词文本，使用模式B通常能得到更好的结果
        
        Args:
            text: 输入文本
            
        Returns:
            Token列表
        """
        return self.tokenize(text, mode='B')


# 全局分词器实例
tokenizer_service = TokenizerService()

