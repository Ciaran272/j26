/**
 * 前端配置模块
 */

const resolveApiUrl = () => {
    const localHosts = new Set(['localhost', '127.0.0.1']);
    if (typeof window !== 'undefined') {
        const override = window.__FURIGANA_CONFIG__?.API_URL;
        if (override) {
            return override;
        }
        if (localHosts.has(window.location.hostname)) {
            return 'http://127.0.0.1:5000/api/furigana';
        }
    }
    return 'https://zforest.onrender.com/api/furigana';
};

export const CONFIG = {
    // API配置
    API_URL: resolveApiUrl(),

    // 长按编辑配置
    LONG_PRESS_DURATION: 1000, // 毫秒
    
    // 输入防抖配置
    INPUT_DEBOUNCE_DELAY: 800, // 毫秒（即时更新延迟，避免频繁请求）
    
    // 多音字菜单配置
    READING_MENU_HOVER_DELAY: 300, // 毫秒
    READING_MENU_HIDE_DELAY: 200, // 毫秒
    
    // 导出配置
    EXPORT_SCALE: 3, // 导出图片的分辨率倍数
    EXPORT_TARGET_WIDTH: 900, // 目标宽度
    
    // 其他配置
    MAX_NEXT_HIRAGANA_CHARS: 2, // 收集后续假名的最大字符数

    // 主题配置
    DEFAULT_THEME: "light"
};

