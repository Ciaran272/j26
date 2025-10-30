/**
 * 片假名转换组件
 * 处理片假名转平假名的即时切换
 */

import { isKatakana, katakanaToHiragana } from '../utils/kana-utils.js';

export class KatakanaToggleManager {
    /**
     * 切换片假名显示
     */
    static toggleKatakanaDisplay(showKatakanaReading) {
        const allWordUnits = document.querySelectorAll('.word-unit');
        
        allWordUnits.forEach(wordUnit => {
            const surface = wordUnit.querySelector('rb')?.textContent || '';
            const readingElement = wordUnit.querySelector('rt');
            
            // 检查是否为片假名单词
            if (isKatakana(surface) && surface.length > 1) {
                if (showKatakanaReading) {
                    // 显示片假名的平假名注音
                    if (readingElement) {
                        const hiraganaReading = katakanaToHiragana(surface);
                        readingElement.textContent = hiraganaReading;
                        readingElement.style.display = '';
                    } else {
                        // 如果没有rt元素，创建一个
                        const ruby = wordUnit.querySelector('ruby');
                        if (ruby) {
                            const newRt = document.createElement('rt');
                            newRt.className = 'reading-text';
                            newRt.textContent = katakanaToHiragana(surface);
                            ruby.appendChild(newRt);
                        }
                    }
                } else {
                    // 隐藏片假名的注音
                    if (readingElement) {
                        readingElement.textContent = '';
                        readingElement.style.display = 'none';
                    }
                }
            }
        });
    }
}

