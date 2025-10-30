/**
 * API调用模块
 */

import { CONFIG } from './config.js';

/**
 * 调用注音API
 * @param {string} text - 输入文本
 * @param {boolean} katakana - 是否转换片假名
 * @returns {Promise<Array>} 处理后的行数据
 */
export async function fetchFurigana(text, katakana = true, signal) {
    const response = await fetch(CONFIG.API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            lyrics: text,
            katakana: katakana
        }),
        signal
    });
    
    if (!response.ok) {
        throw new Error(`服务器错误: ${response.statusText}`);
    }
    
    const lines = await response.json();
    
    if (!Array.isArray(lines)) {
        throw new Error('响应格式异常：期望数组');
    }
    
    return lines;
}

