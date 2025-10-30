"""
应用配置模块
统一管理所有配置项和环境变量
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """应用配置类"""
    
    # 服务器配置
    HOST: str = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 词典路径配置
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(BASE_DIR, 'data')
    
    # 外部词典文件路径
    JMDICT_PATH: str = os.getenv(
        'JMDICT_JSON',
        os.path.join(BASE_DIR, 'jmdict_readings.json')
    )
    KANJIDIC2_PATH: str = os.getenv(
        'KANJIDIC2_JSON',
        os.path.join(BASE_DIR, 'kanjidic2_readings.json')
    )
    KANJI_READINGS_PATH: str = os.path.join(BASE_DIR, 'kanji_readings.json')
    MODERN_OVERRIDES_PATH: str = os.getenv(
        'MODERN_OVERRIDES',
        os.path.join(BASE_DIR, 'modern_overrides.json')
    )
    
    # 业务配置
    MAX_TEXT_LENGTH: int = int(os.getenv('MAX_TEXT_LENGTH', '10000'))
    DEFAULT_TOKENIZER_MODE: str = 'B'  # A, B, or C
    
    # CORS配置
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', '*')
    
    # 静态文件配置
    STATIC_FOLDER: str = '.'
    STATIC_URL_PATH: str = ''
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量创建配置实例"""
        return cls()
    
    def validate(self) -> None:
        """验证配置的有效性"""
        if self.PORT < 1 or self.PORT > 65535:
            raise ValueError(f"无效的端口号: {self.PORT}")
        
        if self.MAX_TEXT_LENGTH <= 0:
            raise ValueError(f"最大文本长度必须大于0: {self.MAX_TEXT_LENGTH}")
        
        if self.DEFAULT_TOKENIZER_MODE not in ['A', 'B', 'C']:
            raise ValueError(f"无效的分词模式: {self.DEFAULT_TOKENIZER_MODE}")


# 全局配置实例
config = Config.from_env()

