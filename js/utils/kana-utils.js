/**
 * 假名工具函数模块
 */

/**
 * 检查字符是否为平假名
 */
export function isHiragana(char) {
    return /[\u3040-\u309f]/.test(char);
}

/**
 * 检查文本是否全为片假名
 */
export function isKatakana(text) {
    return /^[\u30A0-\u30FF\u30FC]+$/.test(text);
}

/**
 * 片假名转平假名
 */
export function katakanaToHiragana(katakanaString) {
    let hiraganaString = "";
    for (let char of katakanaString) {
        if ('ァ' <= char && char <= 'ヶ') {
            const hiraganaChar = String.fromCharCode(char.charCodeAt(0) - 96);
            hiraganaString += hiraganaChar;
        } else {
            hiraganaString += char;
        }
    }
    return hiraganaString;
}

