/**
 * 应用主入口文件
 * 初始化应用并绑定所有事件
 */

import { appState } from './state.js';
import { ConverterService } from './services/converter.js';
import { ExporterService } from './services/exporter.js';
import { ReadingMenuManager } from './components/reading-menu.js';
import { LongpressEditorManager } from './components/longpress-editor.js';
import { KatakanaToggleManager } from './components/katakana-toggle.js';
import { CONFIG } from './config.js';

class App {
    constructor() {
        this.state = appState;
        this.converter = new ConverterService();
        this.exporter = new ExporterService();
        this.readingMenu = new ReadingMenuManager();
        this.longpressEditor = new LongpressEditorManager();
        this.themeMediaQuery = null;
        this.hasManualThemeSelection = false;
    }
    
    /**
     * 初始化应用
     */
    init() {
        // 初始化DOM元素
        this.state.initElements();
        this.themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.initTheme();
        
        // 绑定事件
        this.bindEvents();
        
        // 初始化闪烁光标
        this.initBlinkingCursor();
        
        console.log('应用初始化完成');
    }
    
    /**
     * 初始化主题设置
     */
    initTheme() {
        this.hasManualThemeSelection = false;
        this.applyTheme(CONFIG.DEFAULT_THEME);

        if (this.themeMediaQuery?.addEventListener) {
            this.themeMediaQuery.addEventListener('change', (event) => this.handleSystemThemeChange(event));
        } else if (this.themeMediaQuery?.addListener) {
            // 兼容旧浏览器
            this.themeMediaQuery.addListener((event) => this.handleSystemThemeChange(event));
        }
    }

    /**
     * 应用指定主题
     */
    applyTheme(theme) {
        const normalizedTheme = theme === 'dark' ? 'dark' : 'light';
        this.state.updateSetting('theme', normalizedTheme);
        document.body.setAttribute('data-theme', normalizedTheme);

        const toggle = this.state.elements.themeToggle;
        if (toggle) {
            toggle.classList.toggle('is-dark', normalizedTheme === 'dark');
        }
    }

    /**
     * 切换主题
     */
    toggleTheme() {
        const currentTheme = this.state.settings.theme;
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.hasManualThemeSelection = true;
        this.applyTheme(nextTheme);
    }

    /**
     * 响应系统主题变更（仅当用户未手动设置时）
     */
    handleSystemThemeChange(event) {
        if (this.hasManualThemeSelection) {
            return;
        }
        const systemTheme = event.matches ? 'dark' : 'light';
        this.applyTheme(systemTheme);
    }

    /**
     * 初始化闪烁光标控制
     */
    initBlinkingCursor() {
        const input = this.state.elements.lyricsInput;
        const cursor = document.querySelector('.blinking-cursor');
        
        if (!cursor) return;
        
        const updateCursor = () => {
            // 只在输入框为空且未聚焦时显示光标
            if (input.value === '' && document.activeElement !== input) {
                cursor.style.display = 'block';
            } else {
                cursor.style.display = 'none';
            }
        };
        
        // 初始检查
        updateCursor();
        
        // 监听输入和焦点变化
        input.addEventListener('input', updateCursor);
        input.addEventListener('focus', updateCursor);
        input.addEventListener('blur', updateCursor);
    }
    
    /**
     * 绑定所有事件
     */
    bindEvents() {
        if (this.state.elements.themeToggle) {
            this.state.elements.themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
        
        // 转换按钮
        this.state.elements.convertBtn.addEventListener('click', async () => {
            const success = await this.converter.convert();
            if (success) {
                // 重新设置交互
                this.readingMenu.setupMultiReadingInteraction();
                this.longpressEditor.setupLongpressEditInteraction();
            }
        });
        
        // 清空按钮
        this.state.elements.clearBtn.addEventListener('click', () => {
            this.converter.clear();
        });
        
        // 导出按钮
        this.state.elements.exportBtn.addEventListener('click', async () => {
            await this.exporter.export();
        });
        
        // 片假名转换选项
        this.state.elements.toggleKatakana.addEventListener('change', (e) => {
            this.state.updateSetting('katakanaConversion', e.target.checked);
            // 如果已有输出，使用即时切换
            if (this._hasValidOutput()) {
                KatakanaToggleManager.toggleKatakanaDisplay(e.target.checked);
            }
        });
        
        // 长按编辑选项
        this.state.elements.toggleLongpressEdit.addEventListener('change', (e) => {
            this.state.updateSetting('longpressEdit', e.target.checked);
            // 当选项变化时重新设置长按编辑交互
            if (this._hasValidOutput()) {
                this.longpressEditor.setupLongpressEditInteraction();
            }
        });
        
        // 输入框变化监听（防抖）- 即时自动更新
        this.state.elements.lyricsInput.addEventListener('input', () => {
            this.state.setTimer('inputDebounce', async () => {
                if (this._hasValidOutput()) {
                    // 自动重新生成注音
                    const success = await this.converter.convert();
                    if (success) {
                        // 重新设置交互
                        this.readingMenu.setupMultiReadingInteraction();
                        this.longpressEditor.setupLongpressEditInteraction();
                    }
                }
            }, CONFIG.INPUT_DEBOUNCE_DELAY);
        });
        
        // 点击页面其他地方时隐藏菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.multi-reading') && !e.target.closest('.reading-menu')) {
                this.readingMenu.hideReadingMenu();
            }
        });
    }
    
    /**
     * 检查是否有有效输出
     */
    _hasValidOutput() {
        const output = this.state.elements.lyricsOutput.innerHTML.trim();
        return output !== '' && 
               !output.includes('正在连接Render') && 
               !output.includes('处理失败');
    }
}

// DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init();
});

