/**
 * 安全工具函数
 * 防止XSS攻击
 */

/**
 * HTML实体转义
 * 防止XSS注入
 */
export function escapeHtml(text) {
    if (!text) return '';
    
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * JSON安全转义（用于HTML属性）
 */
export function escapeJsonForAttribute(obj) {
    const json = JSON.stringify(obj);
    return escapeHtml(json);
}

