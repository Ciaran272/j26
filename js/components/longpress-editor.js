/**
 * 长按编辑组件
 * 处理注音的长按编辑功能
 */

import { appState } from '../state.js';
import { CONFIG } from '../config.js';

export class LongpressEditorManager {
    constructor() {
        this.state = appState;
    }
    
    /**
     * 设置长按编辑交互
     */
    setupLongpressEditInteraction() {
        if (!this.state.settings.longpressEdit) return;
        
        const readingElements = document.querySelectorAll('.reading-text');
        
        readingElements.forEach(element => {
            let longPressTimer;
            let isLongPress = false;
            let touchMoved = false;

            const isEnabled = () => this.state.settings.longpressEdit;
            
            // 开始长按（鼠标或触摸）
            const startLongPress = (e) => {
                if (!isEnabled()) return;
                
                isLongPress = false;
                touchMoved = false;
                
                longPressTimer = setTimeout(() => {
                    if (!isEnabled() || touchMoved) {
                        return;
                    }
                    isLongPress = true;
                    this.enterEditMode(element);
                }, CONFIG.LONG_PRESS_DURATION);
                
                // 阻止默认行为（文本选择、上下文菜单）
                e.preventDefault();
            };
            
            // 结束长按
            const endLongPress = () => {
                if (!isEnabled()) return;
                clearTimeout(longPressTimer);
            };
            
            // 触摸移动时取消长按
            const handleTouchMove = () => {
                touchMoved = true;
                clearTimeout(longPressTimer);
            };
            
            // 防止点击事件与长按冲突
            const handleClick = (e) => {
                if (!isEnabled()) return;
                if (isLongPress) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            };
            
            // 阻止移动端上下文菜单
            const preventContextMenu = (e) => {
                if (!isEnabled()) return;
                e.preventDefault();
                return false;
            };
            
            // 鼠标事件（桌面端）
            element.addEventListener('mousedown', (e) => {
                if (e.button === 0) startLongPress(e);
            });
            element.addEventListener('mouseup', endLongPress);
            element.addEventListener('mouseleave', endLongPress);
            
            // 触摸事件（移动端）
            element.addEventListener('touchstart', startLongPress, { passive: false });
            element.addEventListener('touchend', endLongPress);
            element.addEventListener('touchcancel', endLongPress);
            element.addEventListener('touchmove', handleTouchMove, { passive: false });
            
            // 通用事件
            element.addEventListener('click', handleClick);
            element.addEventListener('contextmenu', preventContextMenu);
        });
    }
    
    /**
     * 进入编辑模式
     */
    enterEditMode(readingElement) {
        // 检查是否已经在编辑模式或功能已禁用
        if (!this.state.settings.longpressEdit) return;
        if (readingElement.classList.contains('editing')) return;
        
        const originalText = readingElement.textContent;
        
        // 创建输入框
        const input = document.createElement('input');
        input.type = 'text';
        input.value = originalText;
        input.className = 'reading-editor';
        
        // 隐藏原文本并插入输入框
        readingElement.style.display = 'none';
        readingElement.classList.add('editing');
        readingElement.parentNode.insertBefore(input, readingElement.nextSibling);
        
        // 聚焦并选中文本
        input.focus();
        input.select();
        
        // 处理完成编辑的事件
        const finishEdit = () => {
            const newText = input.value.trim();
            
            // 只有在用户输入了有效内容且与原文不同时才更新
            if (newText && newText !== originalText) {
                readingElement.textContent = newText;
                // 更新对应的word-unit的数据属性
                const wordUnit = readingElement.closest('.word-unit');
                if (wordUnit) {
                    wordUnit.dataset.currentReading = newText;
                }
                console.log(`用户修改注音: ${originalText} -> ${newText}`);
            } else if (!newText) {
                console.log(`用户取消修改注音，保持原注音: ${originalText}`);
            }
            
            // 恢复原状态
            readingElement.style.display = '';
            readingElement.classList.remove('editing');
            input.remove();
        };
        
        // 回车完成编辑
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                finishEdit();
            } else if (e.key === 'Escape') {
                // ESC 取消编辑
                readingElement.style.display = '';
                readingElement.classList.remove('editing');
                input.remove();
            }
        });
        
        // 失去焦点完成编辑
        input.addEventListener('blur', finishEdit);
    }
}

