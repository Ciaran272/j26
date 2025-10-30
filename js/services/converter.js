/**
 * 注音转换服务
 * 负责调用API并渲染结果
 */

import { appState } from '../state.js';
import { fetchFurigana } from '../api.js';
import { generateWordHtml } from '../utils/ruby-generator.js';
import { batchUpdateDOM } from '../utils/dom-utils.js';

export class ConverterService {
    constructor() {
        this.state = appState;
        this.currentAbortController = null;
    }
    
    /**
     * 转换输入文本为注音
     */
    async convert() {
        const inputText = this.state.elements.lyricsInput.value;
        
        if (inputText.trim() === '') {
            this.state.elements.lyricsOutput.innerHTML = '';
            return;
        }
        
        if (this.currentAbortController) {
            this.currentAbortController.abort();
        }

        const abortController = new AbortController();
        this.currentAbortController = abortController;

        // 设置加载状态
        this._setLoadingState(true);
        this.state.elements.lyricsOutput.innerHTML = '<span class="loading-hint">正在连接Render...</span>';
        
        try {
            const lines = await fetchFurigana(
                inputText,
                this.state.settings.katakanaConversion,
                abortController.signal
            );

            if (abortController.signal.aborted) {
                return false;
            }
            
            this._renderLines(lines);
            
            return true;
        } catch (error) {
            console.error("请求失败:", error);
            this.state.elements.lyricsOutput.textContent = 
                `处理失败，请确保后端服务器正在运行。错误: ${error.message}`;
            return false;
        } finally {
            if (this.currentAbortController === abortController) {
                this.currentAbortController = null;
            }
            this._setLoadingState(false);
        }
    }
    
    /**
     * 渲染行数据（优化版 - 使用批量更新）
     */
    _renderLines(lines) {
        const outputHtmlArray = lines.map(lineTokens => {
            if (!Array.isArray(lineTokens) || lineTokens.length === 0) {
                return '';
            }
            
            const lineContent = lineTokens.map(token => generateWordHtml(token)).join('');
            return lineContent;
        });
        
        // 使用批量更新提高性能
        batchUpdateDOM(this.state.elements.lyricsOutput, outputHtmlArray);
    }
    
    /**
     * 设置加载状态
     */
    _setLoadingState(isLoading) {
        this.state.isConverting = isLoading;
        this.state.elements.convertBtn.disabled = isLoading;
        this.state.elements.convertBtn.textContent = isLoading ? '生成中...' : '生成注音';
    }
    
    /**
     * 清空输入和输出
     */
    clear() {
        this.state.elements.lyricsInput.value = '';
        this.state.elements.lyricsOutput.innerHTML = '';
    }
}

