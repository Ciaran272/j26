/**
 * 读音菜单组件
 * 处理多音字的读音选择菜单
 */

import { appState } from '../state.js';
import { CONFIG } from '../config.js';
import { generateAdvancedRuby } from '../utils/ruby-generator.js';
import { escapeHtml } from '../utils/security.js';

export class ReadingMenuManager {
    constructor() {
        this.state = appState;
    }
    
    /**
     * 设置多音字交互
     */
    setupMultiReadingInteraction() {
        const multiReadingElements = document.querySelectorAll('.multi-reading');
        
        multiReadingElements.forEach(element => {
            let hoverTimeout;
            
            // 鼠标悬停事件
            element.addEventListener('mouseenter', (e) => {
                clearTimeout(hoverTimeout);
                hoverTimeout = setTimeout(() => {
                    this.showReadingMenu(element);
                }, CONFIG.READING_MENU_HOVER_DELAY);
            });
            
            element.addEventListener('mouseleave', (e) => {
                clearTimeout(hoverTimeout);
                // 延迟隐藏菜单，给用户时间移动到菜单上
                setTimeout(() => {
                    const menu = this.state.currentMenu;
                    if (menu && !menu.matches(':hover') && !element.matches(':hover')) {
                        this.hideReadingMenu();
                    }
                }, CONFIG.READING_MENU_HIDE_DELAY);
            });
        });
    }
    
    /**
     * 显示读音菜单
     */
    showReadingMenu(element) {
        // 移除现有菜单
        this.hideReadingMenu();
        
        const alternatives = JSON.parse(element.dataset.alternatives || '[]');
        const rawCurrentReading = element.dataset.currentReading || '';
        
        // 重建完整的 surface（基体+送假名）
        const baseMainText = element.querySelector('rb')?.textContent || '';
        const okuriText = element.querySelector('.okurigana')?.textContent || '';
        const fullSurface = baseMainText + okuriText;
        
        // 规范化读音
        const normalized = [];
        const seen = new Set();

        let currentReadingNormalized = rawCurrentReading;
        if (rawCurrentReading) {
            const currentResult = generateAdvancedRuby(fullSurface, rawCurrentReading);
            if (currentResult.rt) {
                currentReadingNormalized = currentResult.rt;
            }
        }
        
        for (const r of alternatives) {
            const result = generateAdvancedRuby(fullSurface, r);
            const norm = result.rt || r;
            if (norm && !seen.has(norm)) {
                seen.add(norm);
                normalized.push(norm);
            }
        }
        
        if (normalized.length <= 1) return;
        
        // 创建菜单元素
        const menu = document.createElement('div');
        menu.className = 'reading-menu';
        menu.innerHTML = normalized.map(reading => {
            const escapedReading = escapeHtml(reading);
            const isCurrent = reading === currentReadingNormalized;
            return `<div class="reading-option ${isCurrent ? 'current' : ''}" data-reading="${escapedReading}">${escapedReading}</div>`;
        }).join('');
        
        // 定位菜单
        this._positionMenu(menu, element);
        
        // 为菜单选项添加点击事件
        menu.querySelectorAll('.reading-option').forEach(option => {
            option.addEventListener('click', () => {
                let newReading = option.dataset.reading;
                this.updateWordReading(element, newReading);
                this.hideReadingMenu();
            });
        });
        
        // 菜单悬停事件
        menu.addEventListener('mouseleave', () => {
            setTimeout(() => {
                if (!element.matches(':hover')) {
                    this.hideReadingMenu();
                }
            }, CONFIG.READING_MENU_HIDE_DELAY);
        });
        
        // 记录菜单元素
        this.state.setCurrentMenu(menu);
    }
    
    /**
     * 定位菜单
     */
    _positionMenu(menu, element) {
        const container = document.querySelector('.lyrics-container');
        const rect = element.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        
        // 计算元素在容器内的相对位置
        const relativeLeft = rect.left - containerRect.left + container.scrollLeft;
        const relativeTop = rect.bottom - containerRect.top + container.scrollTop;
        
        menu.style.position = 'absolute';
        menu.style.left = relativeLeft + 'px';
        menu.style.top = (relativeTop + 5) + 'px';
        menu.style.zIndex = '1000';
        
        container.appendChild(menu);
        
        // 调整位置以避免溢出
        const menuRect = menu.getBoundingClientRect();
        const containerBounds = container.getBoundingClientRect();
        
        // 如果菜单右边超出容器，向左调整
        if (menuRect.right > containerBounds.right) {
            const overflow = menuRect.right - containerBounds.right;
            menu.style.left = (relativeLeft - overflow - 10) + 'px';
        }
        
        // 如果菜单下边超出容器，显示在元素上方
        if (menuRect.bottom > containerBounds.bottom) {
            const elementTop = rect.top - containerRect.top + container.scrollTop;
            menu.style.top = (elementTop - menuRect.height - 5) + 'px';
        }
    }
    
    /**
     * 隐藏读音菜单
     */
    hideReadingMenu() {
        this.state.clearCurrentMenu();
    }
    
    /**
     * 更新单词读音
     */
    updateWordReading(element, newReading) {
        const readingElement = element.querySelector('.reading-text');
        if (readingElement) {
            readingElement.textContent = newReading;
        }
        
        // 更新数据属性
        element.dataset.currentReading = newReading;
        
        console.log(`用户选择了新读音: ${element.querySelector('rb').textContent} -> ${newReading}`);
    }
}

