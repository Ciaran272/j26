/**
 * Ruby标签生成器
 * 处理日语注音的HTML生成
 */

import { isHiragana, isKatakana } from './kana-utils.js';
import { escapeHtml, escapeJsonForAttribute } from './security.js';

/**
 * 生成高级Ruby标签
 * 智能处理送假名（okurigana）
 */
export function generateAdvancedRuby(surface, reading) {
    if (surface === reading || !reading) {
        return { baseMain: surface, suffix: '', rt: null };
    }

    // 片假名特殊处理
    if (isKatakana(surface) && reading) {
        return { baseMain: surface, suffix: '', rt: reading };
    }

    // 查找共同后缀
    let commonSuffixLength = 0;
    const minLength = Math.min(surface.length, reading.length);
    
    for (let i = 1; i <= minLength; i++) {
        const surfaceChar = surface[surface.length - i];
        const readingChar = reading[reading.length - i];
        if (surfaceChar === readingChar && isHiragana(surfaceChar)) {
            commonSuffixLength++;
        } else {
            break;
        }
    }

    if (commonSuffixLength === 0) {
        return { baseMain: surface, suffix: '', rt: reading };
    } else {
        const surfaceBase = surface.substring(0, surface.length - commonSuffixLength);
        const commonSuffix = surface.substring(surface.length - commonSuffixLength);
        const readingBase = reading.substring(0, reading.length - commonSuffixLength);
        
        if (!surfaceBase || surfaceBase === readingBase) {
            return { baseMain: surface, suffix: '', rt: null };
        }
        return { baseMain: surfaceBase, suffix: commonSuffix, rt: readingBase };
    }
}

/**
 * 生成完整的单词HTML
 */
export function generateWordHtml(token) {
    const surface = token?.surface || '';
    const reading = token?.reading || '';
    const alternatives = token?.alternatives || [];
    const hasAlternatives = token?.has_alternatives || false;
    const safeReading = (reading === '*' ? '' : reading);
    const result = generateAdvancedRuby(surface, safeReading);
    
    // HTML转义防止XSS
    const escapedBaseMain = escapeHtml(result.baseMain);
    const escapedRt = escapeHtml(result.rt);
    const escapedSuffix = escapeHtml(result.suffix);
    const escapedSafeReading = escapeHtml(safeReading);
    
    // 为有多音读音的单词添加特殊的类名和数据属性
    const multiReadClass = hasAlternatives ? ' multi-reading' : '';
    const alternativesData = hasAlternatives ? ` data-alternatives='${escapeJsonForAttribute(alternatives)}'` : '';
    const currentReadingData = ` data-current-reading='${escapedSafeReading}'`;
    
    let wordHtml = `<span class="word-unit${multiReadClass}"${alternativesData}${currentReadingData}><span class="stack">`;
    
    if (result.rt) {
        wordHtml += `<span class="ruby-wrap"><ruby><rb>${escapedBaseMain}</rb><rt class="reading-text">${escapedRt}</rt></ruby>`;
        wordHtml += `</span>`;
    } else {
        wordHtml += `<span class="ruby-wrap"><ruby><rb>${escapedBaseMain}</rb></ruby>`;
        wordHtml += `</span>`;
    }
    
    if (result.suffix) {
        wordHtml += `<span class="okurigana">${escapedSuffix}</span>`;
    }
    
    wordHtml += `</span></span>`;
    
    return wordHtml;
}

