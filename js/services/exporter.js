/**
 * 图片导出服务
 * 使用html2canvas导出注音结果为图片
 */

import { appState } from '../state.js';
import { CONFIG } from '../config.js';

export class ExporterService {
    constructor() {
        this.state = appState;
    }
    
    /**
     * 导出为图片
     */
    async export() {
        const lyricsElement = this.state.elements.lyricsOutput;
        const titleElement = this.state.elements.outputTitleInput;
        
        // 检查是否有内容
        if (lyricsElement.innerHTML.trim() === '') {
            alert('请先生成注音内容再导出图片');
            return false;
        }
        
        this._setExportingState(true);
        
        try {
            const title = titleElement.value || '标题';
            await this._exportToImage(title, lyricsElement);
            return true;
        } catch (error) {
            console.error('导出图片失败:', error);
            alert('导出图片失败，请重试');
            return false;
        } finally {
            this._setExportingState(false);
        }
    }
    
    /**
     * 执行图片导出
     */
    async _exportToImage(title, lyricsElement) {
        // 创建导出容器
        const exportContainer = this._createExportContainer(title, lyricsElement);
        document.body.appendChild(exportContainer.container);
        
        try {
            // 计算缩放
            const dimensions = this._calculateDimensions(
                exportContainer.container,
                exportContainer.titleDiv,
                exportContainer.lyricsDiv
            );
            
            // 生成canvas
            const canvas = await html2canvas(exportContainer.container, {
                scale: CONFIG.EXPORT_SCALE,
                backgroundColor: '#ffffff',
                useCORS: true,
                allowTaint: true,
                width: dimensions.finalWidth,
                height: dimensions.finalHeight,
                scrollX: 0,
                scrollY: 0,
                logging: false
            });
            
            // 下载图片
            this._downloadImage(canvas, title);
            
            console.log('图片导出成功');
        } finally {
            // 清理
            document.body.removeChild(exportContainer.container);
            document.head.removeChild(exportContainer.style);
        }
    }
    
    /**
     * 创建导出容器
     */
    _createExportContainer(title, lyricsElement) {
        const exportContainer = document.createElement('div');
        const theme = this.state.settings.theme === 'dark' ? 'dark' : 'light';
        const themeStyles = this._getContainerStylesByTheme(theme);
        exportContainer.style.cssText = themeStyles.container;
        
        // 标题
        const titleDiv = document.createElement('div');
        titleDiv.style.cssText = themeStyles.title;
        titleDiv.textContent = title;
        
        // 歌词
        const lyricsDiv = document.createElement('div');
        lyricsDiv.innerHTML = lyricsElement.innerHTML;
        lyricsDiv.style.cssText = themeStyles.lyrics;
        this._normalizeRubyMarkup(lyricsDiv);
        
        // 样式
        const style = document.createElement('style');
        style.textContent = this._getExportStyles(theme);
        
        exportContainer.className = 'export-container';
        exportContainer.appendChild(titleDiv);
        exportContainer.appendChild(lyricsDiv);
        document.head.appendChild(style);
        
        return { container: exportContainer, titleDiv, lyricsDiv, style };
    }
    
    /**
     * 计算导出尺寸
     */
    _calculateDimensions(container, titleDiv, lyricsDiv) {
        const targetWidth = CONFIG.EXPORT_TARGET_WIDTH;
        const titleWidth = titleDiv.scrollWidth;
        
        // 找最宽的歌词行
        const paragraphs = lyricsDiv.querySelectorAll('p');
        let maxLyricsWidth = 0;
        
        paragraphs.forEach(p => {
            if (p.textContent.trim()) {
                const pWidth = p.scrollWidth;
                if (pWidth > maxLyricsWidth) {
                    maxLyricsWidth = pWidth;
                }
            }
        });
        
        const actualContentWidth = Math.max(titleWidth, maxLyricsWidth);
        const actualWidth = actualContentWidth + 80; // 加上左右padding
        
        // 设置容器宽度（确保段落能正确显示）
        const containerWidth = Math.max(targetWidth, actualWidth);
        container.style.width = `${containerWidth}px`;
        
        let scaleRatio = 1;
        let finalWidth = containerWidth;
        let finalHeight = container.scrollHeight;
        
        // 如果内容过宽，进行缩放
        if (actualWidth > targetWidth) {
            scaleRatio = targetWidth / actualWidth;
            container.style.transform = `scale(${scaleRatio})`;
            container.style.transformOrigin = 'top left';
            finalWidth = targetWidth;
            finalHeight = container.scrollHeight * scaleRatio;
        }
        
        return { finalWidth, finalHeight };
    }
    
    /**
     * 下载图片
     */
    _downloadImage(canvas, title) {
        const link = document.createElement('a');
        const date = new Date();
        const dateStr = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
        link.download = `${title}_注音歌词_${dateStr}.png`;
        link.href = canvas.toDataURL('image/png', 1.0);
        link.click();
    }
    
    /**
     * 获取导出样式 - 与当前页面样式保持一致
     */
    _getContainerStylesByTheme(theme) {
        if (theme === 'dark') {
            return {
                container: `
                    position: fixed;
                    top: -10000px;
                    left: 0;
                    background: radial-gradient(circle at 20% 20%, #111529 0%, #0a0f22 55%, #060916 100%);
                    padding: 48px;
                    font-family: 'Inter', 'Noto Sans JP', sans-serif;
                    box-sizing: border-box;
                    min-height: 400px;
                    width: auto;
                    display: block;
                `,
                title: `
                    font-size: 24px;
                    font-weight: 600;
                    color: #f6f7ff;
                    text-align: center;
                    margin-bottom: 32px;
                    padding-bottom: 16px;
                    border-bottom: 1px solid rgba(110, 120, 200, 0.25);
                `,
                lyrics: `
                    font-size: 1.6em;
                    line-height: 3.2;
                    color: #e6e9ff;
                    width: 100%;
                    display: block;
                    background: linear-gradient(145deg, rgba(21, 26, 51, 0.96) 0%, rgba(14, 20, 40, 0.98) 100%);
                    padding: 32px;
                    border-radius: 12px;
                    border: 1px solid rgba(90, 110, 190, 0.45);
                    box-shadow: 0 26px 60px rgba(4, 6, 16, 0.65);
                `
            };
        }

        return {
            container: `
                position: fixed;
                top: -10000px;
                left: 0;
                background: linear-gradient(180deg, #fefdfb 0%, #f9f8fb 15%, #f3f2f8 35%, #ebe9f5 55%, #e3e0f2 75%, #d8d5ed 100%);
                padding: 48px;
                font-family: 'Inter', 'Noto Sans JP', sans-serif;
                box-sizing: border-box;
                min-height: 400px;
                width: auto;
                display: block;
            `,
            title: `
                font-size: 24px;
                font-weight: 600;
                color: #1d1d1f;
                text-align: center;
                margin-bottom: 32px;
                padding-bottom: 16px;
                border-bottom: 1px solid rgba(24, 32, 56, 0.12);
            `,
            lyrics: `
                font-size: 1.6em;
                line-height: 3.2;
                color: #1d1d1f;
                width: 100%;
                display: block;
                background: #ffffff;
                padding: 32px;
                border-radius: 12px;
                border: 1px solid rgba(24, 32, 56, 0.12);
            `
        };
    }

    _getExportStyles(theme) {
        const isDark = theme === 'dark';
        const baseRubyColor = isDark ? '#ff8a8a' : '#ff6b6b';
        const baseTextColor = isDark ? '#e6e9ff' : '#1d1d1f';

        return `
            .export-container {
                color: ${baseTextColor} !important;
            }
            .export-container p {
                margin: 0 0 0.5em 0;
                line-height: 3.2;
                white-space: nowrap;
                overflow: visible;
                display: block;
                width: 100%;
                text-align: center;
                color: ${baseTextColor} !important;
            }
            .export-container p:last-child {
                margin-bottom: 0;
            }
            .export-container p:empty {
                height: 3.2em;
            }
            .export-container ruby {
                ruby-position: over;
                ruby-align: center;
                line-height: 1;
            }
            .export-container .export-ruby-stack {
                display: inline-flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start;
                line-height: 1;
                min-width: 0;
            }
            .export-container .export-ruby-rt {
                font-size: 0.7em;
                color: ${baseRubyColor} !important;
                white-space: nowrap;
                text-align: center;
                font-weight: 500;
                margin-bottom: 0.1em;
            }
            .export-container .export-ruby-rb {
                color: ${baseTextColor} !important;
                text-align: center;
                line-height: 1;
            }
            .export-container ruby rt {
                font-size: 0.7em;
                color: ${baseRubyColor} !important;
                white-space: nowrap;
                text-align: center;
                font-weight: 500;
            }
            .export-container ruby rb {
                color: ${baseTextColor} !important;
            }
            .export-container .word-unit {
                display: inline-block;
                margin: 0 0.3em;
                vertical-align: baseline;
                position: relative;
                line-height: 1;
                color: ${baseTextColor} !important;
            }
            .export-container .stack {
                display: inline-block;
                vertical-align: baseline;
                text-align: center;
                color: ${baseTextColor} !important;
            }
            .export-container .ruby-wrap {
                line-height: 1;
                color: ${baseTextColor} !important;
            }
            .export-container .okurigana {
                line-height: 1;
                padding-left: 0.05em;
                color: ${baseTextColor} !important;
            }
            .export-container .reading-text,
            .export-container .reading-text {
                color: ${baseRubyColor} !important;
            }
        `;
    }
    
    _normalizeRubyMarkup(root) {
        const rubies = root.querySelectorAll('ruby');
        rubies.forEach(ruby => {
            const base = ruby.querySelector('rb');
            const reading = ruby.querySelector('rt');

            const stack = document.createElement('span');
            stack.className = 'export-ruby-stack';

            if (reading) {
                const readingSpan = document.createElement('span');
                readingSpan.className = 'export-ruby-rt reading-text';
                readingSpan.textContent = reading.textContent;
                stack.appendChild(readingSpan);
            }

            const baseSpan = document.createElement('span');
            baseSpan.className = 'export-ruby-rb';
            baseSpan.textContent = base ? base.textContent : ruby.textContent;
            stack.appendChild(baseSpan);

            ruby.replaceWith(stack);
        });
    }

    /**
     * 设置导出状态
     */
    _setExportingState(isExporting) {
        this.state.elements.exportBtn.disabled = isExporting;
        this.state.elements.exportBtn.textContent = isExporting ? '导出中...' : '导出图片';
    }
}

