/**
 * 应用状态管理模块
 */

class AppState {
    constructor() {
        // UI元素引用
        this.elements = {
            convertBtn: null,
            lyricsInput: null,
            lyricsOutput: null,
            clearBtn: null,
            exportBtn: null,
            toggleKatakana: null,
            toggleLongpressEdit: null,
            outputTitleInput: null,
            themeToggle: null
        };
        
        // 状态
        this.currentMenu = null;
        this.editingElement = null;
        this.isConverting = false;
        
        // 设置
        this.settings = {
            katakanaConversion: true,
            longpressEdit: false,
            theme: "light"
        };
        
        // 定时器
        this.timers = {
            inputDebounce: null,
            menuHover: null
        };
    }
    
    /**
     * 初始化DOM元素引用
     */
    initElements() {
        this.elements.convertBtn = document.getElementById('convert-btn');
        this.elements.lyricsInput = document.getElementById('lyrics-input');
        this.elements.lyricsOutput = document.getElementById('lyrics-output');
        this.elements.clearBtn = document.getElementById('clear-btn');
        this.elements.exportBtn = document.getElementById('export-btn');
        this.elements.toggleKatakana = document.getElementById('toggle-katakana');
        this.elements.toggleLongpressEdit = document.getElementById('toggle-longpress-edit');
        this.elements.outputTitleInput = document.getElementById('output-title-input');
        this.elements.themeToggle = document.getElementById('theme-toggle');
        
        // 初始化设置
        this.settings.katakanaConversion = this.elements.toggleKatakana.checked;
        this.settings.longpressEdit = this.elements.toggleLongpressEdit.checked;

        this.updateSetting('longpressEdit', this.settings.longpressEdit);
    }
    
    /**
     * 设置当前菜单
     */
    setCurrentMenu(menu) {
        if (this.currentMenu) {
            this.currentMenu.remove();
        }
        this.currentMenu = menu;
    }
    
    /**
     * 清除当前菜单
     */
    clearCurrentMenu() {
        if (this.currentMenu) {
            this.currentMenu.remove();
            this.currentMenu = null;
        }
    }
    
    /**
     * 更新设置
     */
    updateSetting(key, value) {
        this.settings[key] = value;
        
        // 更新UI状态
        if (key === 'longpressEdit') {
            document.body.classList.toggle('longpress-edit-enabled', value);
        }

        if (key === 'theme') {
            document.body.setAttribute('data-theme', value);
        }
    }
    
    /**
     * 清除定时器
     */
    clearTimer(timerName) {
        if (this.timers[timerName]) {
            clearTimeout(this.timers[timerName]);
            this.timers[timerName] = null;
        }
    }
    
    /**
     * 设置定时器
     */
    setTimer(timerName, callback, delay) {
        this.clearTimer(timerName);
        this.timers[timerName] = setTimeout(callback, delay);
    }
}

// 导出单例
export const appState = new AppState();

