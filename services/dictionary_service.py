"""
词典服务模块
负责加载和管理外部词典数据
"""
import json
import logging
from typing import Dict, List, Optional
from config import config


logger = logging.getLogger(__name__)


class DictionaryService:
    """词典服务类，管理所有外部词典"""
    
    def __init__(self):
        self.jmdict_readings: Dict[str, List[str]] = {}
        self.kanjidic2_readings: Dict = {}
        self.kanji_readings: Dict[str, List[str]] = {}
        self.phrase_override_readings: Dict[str, List[str]] = {}
        self._initialize_dictionaries()
    
    def _initialize_dictionaries(self) -> None:
        """初始化所有词典"""
        self.jmdict_readings = self._load_dictionary(
            config.JMDICT_PATH, "JMdict"
        )
        self.kanjidic2_readings = self._load_dictionary(
            config.KANJIDIC2_PATH, "Kanjidic2"
        )
        # kanji_readings 已合并到 kanjidic2_readings 中，不再单独加载
        self._load_phrase_overrides()
        
        logger.info(f"词典加载完成: JMdict={len(self.jmdict_readings)}, "
                   f"Kanjidic2={len(self.kanjidic2_readings)}")
    
    def _load_dictionary(self, path: str, name: str) -> Dict:
        """
        加载JSON词典文件
        
        Args:
            path: 词典文件路径
            name: 词典名称（用于日志）
            
        Returns:
            词典数据字典
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.warning(f"{name}格式不正确，应为字典类型")
                    return {}
                logger.info(f"✓ {name}加载成功: {len(data)}条")
                return data
        except FileNotFoundError:
            logger.warning(f"⚠ {name}文件不存在: {path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"✗ {name} JSON解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"✗ {name}加载失败: {e}")
            return {}
    
    def _load_phrase_overrides(self) -> None:
        """加载短语优先读音"""
        # 内置的基础覆盖
        self.phrase_override_readings = {
            "薄暮": ["はくぼ", "うすぐれ"],
            "今日": ["きょう", "こんにち"],
            "昨日": ["きのう", "さくじつ"],
            "明日": ["あした", "みょうにち"],
            "明後日": ["あさって", "みょうごにち"],
        }
        
        # 尝试加载外部覆盖文件
        try:
            with open(config.MODERN_OVERRIDES_PATH, 'r', encoding='utf-8') as f:
                modern_ext = json.load(f)
                if isinstance(modern_ext, dict):
                    for k, v in modern_ext.items():
                        if isinstance(v, list) and v:
                            self.phrase_override_readings[k] = v
                    logger.info(f"✓ 现代覆盖词典加载成功: {len(modern_ext)}条")
        except FileNotFoundError:
            logger.debug("现代覆盖词典文件不存在，使用内置规则")
        except Exception as e:
            logger.warning(f"现代覆盖词典加载失败: {e}")
    
    def get_jmdict_readings(self, surface: str) -> List[str]:
        """获取JMdict中的读音"""
        return self.jmdict_readings.get(surface, [])
    
    def get_kanjidic2_readings(self, kanji: str) -> Optional[Dict]:
        """获取Kanjidic2中单字的读音"""
        return self.kanjidic2_readings.get(kanji)
    
    def get_kanji_readings(self, kanji: str) -> List[str]:
        """
        获取单字的多音读音
        注：kanji_readings 已废弃，改用内置多音字字典
        """
        return self.kanji_readings.get(kanji, [])
    
    def get_phrase_override(self, surface: str) -> Optional[List[str]]:
        """获取短语的优先读音"""
        return self.phrase_override_readings.get(surface)


# 全局词典服务实例
dictionary_service = DictionaryService()

