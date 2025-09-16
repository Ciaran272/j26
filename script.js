document.addEventListener('DOMContentLoaded', () => {
    const convertBtn = document.getElementById('convert-btn');
    const lyricsInput = document.getElementById('lyrics-input');
    const lyricsOutput = document.getElementById('lyrics-output');
    const clearBtn = document.getElementById('clear-btn');
    const exportBtn = document.getElementById('export-btn');
    const toggleKatakana = document.getElementById('toggle-katakana');
    const toggleLongpressEdit = document.getElementById('toggle-longpress-edit');
    // 根据环境选择API地址
    const API_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:5000/api/furigana"
        : "https://zforest.onrender.com/api/furigana";

    convertBtn.addEventListener('click', async () => {
        const inputText = lyricsInput.value;
        if (inputText.trim() === '') { lyricsOutput.innerHTML = ''; return; }
        
        convertBtn.disabled = true;
        convertBtn.textContent = '生成中...';
        lyricsOutput.innerHTML = '<span class="loading-hint">后端启动中（首次较慢）...</span>';
        
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    lyrics: inputText,
                    katakana: toggleKatakana.checked
                }),
            });
            
            if (!response.ok) { throw new Error(`服务器错误: ${response.statusText}`); }
            
            const lines = await response.json();
            if (!Array.isArray(lines)) {
                throw new Error('响应格式异常：期望数组');
            }
            
            const outputHtml = lines.map(lineTokens => {
                if (!Array.isArray(lineTokens)) return '<p></p>';
                
                const lineContent = lineTokens.map(token => {
                    const surface = token?.surface || '';
                    const reading = token?.reading || '';
                    const alternatives = token?.alternatives || [];
                    const hasAlternatives = token?.has_alternatives || false;
                    const safeReading = (reading === '*' ? '' : reading);
                    const result = generateAdvancedRuby(surface, safeReading);
                    
                    // 为有多音读音的单词添加特殊的类名和数据属性
                    const multiReadClass = hasAlternatives ? ' multi-reading' : '';
                    const alternativesData = hasAlternatives ? ` data-alternatives='${JSON.stringify(alternatives)}'` : '';
                    const currentReadingData = ` data-current-reading='${safeReading}'`;
                    
                    let wordHtml = `<span class="word-unit${multiReadClass}"${alternativesData}${currentReadingData}><span class="stack">`;
                    if (result.rt) {
                        wordHtml += `<span class="ruby-wrap"><ruby><rb>${result.baseMain}</rb><rt class="reading-text">${result.rt}</rt></ruby>`;
                        wordHtml += `</span>`;
                    } else {
                        wordHtml += `<span class="ruby-wrap"><ruby><rb>${result.baseMain}</rb></ruby>`;
                        wordHtml += `</span>`;
                    }
                    if (result.suffix) {
                        wordHtml += `<span class="okurigana">${result.suffix}</span>`;
                    }
                    
                    wordHtml += `</span></span>`;
                    
                    return wordHtml;
                }).join('');
                
                return `<p>${lineContent}</p>`;
            }).join('');
            
            lyricsOutput.innerHTML = outputHtml;
            
            // 为多音字单词添加交互事件
            setupMultiReadingInteraction();
            // 为注音添加长按编辑功能
            setupLongpressEditInteraction();
        } catch (error) {
            console.error("请求失败:", error);
            lyricsOutput.textContent = `处理失败，请确保后端服务器正在运行。错误: ${error.message}`;
        } finally {
            convertBtn.disabled = false;
            convertBtn.textContent = '生成注音';
        }
    });
    
    clearBtn.addEventListener('click', () => {
        lyricsInput.value = '';
        lyricsOutput.innerHTML = '';
    });

    // 导出图片功能
    exportBtn.addEventListener('click', async () => {
        // 检查是否有内容可以导出
        if (lyricsOutput.innerHTML.trim() === '') {
            alert('请先生成注音内容再导出图片');
            return;
        }

        exportBtn.disabled = true;
        exportBtn.textContent = '导出中...';

        try {
            await exportToImage();
        } catch (error) {
            console.error('导出图片失败:', error);
            alert('导出图片失败，请重试');
        } finally {
            exportBtn.disabled = false;
            exportBtn.textContent = '导出图片';
        }
    });
    
    // 片假名转换复选框的即时切换功能
    toggleKatakana.addEventListener('change', () => {
        // 只有在已经有输出结果时才重新处理
        if (lyricsOutput.innerHTML.trim() !== '' && !lyricsOutput.textContent.includes('后端启动中（首次较慢）') && !lyricsOutput.textContent.includes('处理失败')) {
            toggleKatakanaDisplay(toggleKatakana.checked);
        }
    });

    // 长按修改选项的变化监听
    toggleLongpressEdit.addEventListener('change', () => {
        // 切换body的CSS类以控制样式
        document.body.classList.toggle('longpress-edit-enabled', toggleLongpressEdit.checked);
        
        // 当选项变化时重新设置长按编辑交互
        if (lyricsOutput.innerHTML.trim() !== '' && !lyricsOutput.textContent.includes('后端启动中（首次较慢）') && !lyricsOutput.textContent.includes('处理失败')) {
            setupLongpressEditInteraction();
        }
    });
    
    // 输入框内容变化的即时同步功能
    let inputChangeTimeout;
    lyricsInput.addEventListener('input', () => {
        // 防抖处理，避免频繁触发
        clearTimeout(inputChangeTimeout);
        inputChangeTimeout = setTimeout(() => {
            // 只有在已经有输出结果时才同步更新
            if (lyricsOutput.innerHTML.trim() !== '' && !lyricsOutput.textContent.includes('后端启动中（首次较慢）') && !lyricsOutput.textContent.includes('处理失败')) {
                syncLyricsFormat();
            }
        }, 500); // 500ms 延迟，避免用户输入时频繁触发
    });
    
    const generateAdvancedRuby = (surface, reading) => {
        if (surface === reading || !reading) {
            return { baseMain: surface, suffix: '', rt: null };
        }

        if (isKatakana(surface) && isHiragana(reading)) {
            return { baseMain: surface, suffix: '', rt: reading };
        }

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
    };

    const isHiragana = (char) => /[\u3040-\u309f]/.test(char);
    const isKatakana = (text) => /^[\u30A0-\u30FF\u30FC]+$/.test(text);
    
    function setupMultiReadingInteraction() {
        const multiReadingElements = document.querySelectorAll('.multi-reading');
        
        multiReadingElements.forEach(element => {
            let hoverTimeout;
            let menuElement = null;
            
            // 鼠标悬停事件
            element.addEventListener('mouseenter', (e) => {
                clearTimeout(hoverTimeout);
                hoverTimeout = setTimeout(() => {
                    showReadingMenu(element);
                }, 300); // 300ms 延迟，避免误触发
            });
            
            element.addEventListener('mouseleave', (e) => {
                clearTimeout(hoverTimeout);
                // 延迟隐藏菜单，给用户时间移动到菜单上
                setTimeout(() => {
                    if (menuElement && !menuElement.matches(':hover') && !element.matches(':hover')) {
                        hideReadingMenu();
                    }
                }, 200);
            });
        });
    }
    
    function showReadingMenu(element) {
        // 移除现有菜单
        hideReadingMenu();
        
        const alternatives = JSON.parse(element.dataset.alternatives || '[]');
        const altsLabeled = [];
        const currentReading = element.dataset.currentReading || '';
        // 重建完整的 surface（基体+送假名），用于规范化读音显示
        const baseMainText = element.querySelector('rb')?.textContent || '';
        const okuriText = element.querySelector('.okurigana')?.textContent || '';
        const fullSurface = baseMainText + okuriText;
        // 规范化：把候选读音通过与 fullSurface 比较，剥离会与送假名重复的部分
        const normalized = [];
        const labeledOut = [];
        const seen = new Set();
        // 兼容：若有带标签的结构优先使用
        for (const r of alternatives) {
            const res = generateAdvancedRuby(fullSurface, r);
            const norm = res.rt || r;
            if (!norm) continue;
            if (!seen.has(norm)) { seen.add(norm); normalized.push(norm); labeledOut.push({reading: norm}); }
        }
        
        if (alternatives.length <= 1) return;
        
        // 创建菜单元素
        const menu = document.createElement('div');
        menu.className = 'reading-menu';
        menu.innerHTML = labeledOut.map(item => {
            return `<div class="reading-option ${item.reading === currentReading ? 'current' : ''}" data-reading="${item.reading}">${item.reading}</div>`;
        }).join('');
        
        // 定位菜单 - 使用更精确的定位方法
        const rect = element.getBoundingClientRect();
        const container = document.querySelector('.lyrics-container');
        const containerRect = container.getBoundingClientRect();
        
        // 计算元素在容器内的相对位置
        const relativeLeft = rect.left - containerRect.left + container.scrollLeft;
        const relativeTop = rect.bottom - containerRect.top + container.scrollTop;
        
        menu.style.position = 'absolute';
        menu.style.left = relativeLeft + 'px';
        menu.style.top = (relativeTop + 5) + 'px';
        menu.style.zIndex = '1000';
        
        // 检查菜单是否会超出容器边界，如果是则调整位置
        container.appendChild(menu);
        
        // 获取菜单尺寸并调整位置以避免溢出
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
        
        // 为菜单选项添加点击事件
        menu.querySelectorAll('.reading-option').forEach(option => {
            option.addEventListener('click', () => {
                let newReading = option.dataset.reading;
                // 再次进行规范化，确保不会与送假名重复
                const baseMainText = element.querySelector('rb')?.textContent || '';
                const okuriText = element.querySelector('.okurigana')?.textContent || '';
                const fullSurface = baseMainText + okuriText;
                const res = generateAdvancedRuby(fullSurface, newReading);
                newReading = res.rt || newReading || '';
                updateWordReading(element, newReading);
                hideReadingMenu();
            });
        });
        
        // 菜单悬停事件
        menu.addEventListener('mouseenter', () => {
            // 保持菜单显示
        });
        
        menu.addEventListener('mouseleave', () => {
            setTimeout(() => {
                if (!element.matches(':hover')) {
                    hideReadingMenu();
                }
            }, 200);
        });
        
        // 记录菜单元素
        window.currentReadingMenu = menu;
    }
    
    function hideReadingMenu() {
        if (window.currentReadingMenu) {
            window.currentReadingMenu.remove();
            window.currentReadingMenu = null;
        }
    }
    
    function updateWordReading(element, newReading) {
        // 更新显示的读音
        const readingElement = element.querySelector('.reading-text');
        if (readingElement) {
            readingElement.textContent = newReading;
        }
        
        // 更新数据属性
        element.dataset.currentReading = newReading;
        
        // 可以在这里添加保存用户选择的逻辑
        console.log(`用户选择了新读音: ${element.querySelector('rb').textContent} -> ${newReading}`);
    }
    
    // 长按编辑功能
    function setupLongpressEditInteraction() {
        if (!toggleLongpressEdit.checked) return;
        
        const readingElements = document.querySelectorAll('.reading-text');
        
        readingElements.forEach(element => {
            let longPressTimer;
            let isLongPress = false;
            
            // 鼠标按下开始计时
            element.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return; // 只响应左键
                
                isLongPress = false;
                longPressTimer = setTimeout(() => {
                    isLongPress = true;
                    enterEditMode(element);
                }, 1000); // 1秒长按
                
                e.preventDefault(); // 防止选中文本
            });
            
            // 鼠标抬起取消计时
            element.addEventListener('mouseup', (e) => {
                clearTimeout(longPressTimer);
            });
            
            // 鼠标离开取消计时
            element.addEventListener('mouseleave', (e) => {
                clearTimeout(longPressTimer);
            });
            
            // 防止点击事件与长按冲突
            element.addEventListener('click', (e) => {
                if (isLongPress) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        });
    }
    
    function enterEditMode(readingElement) {
        // 检查是否已经在编辑模式
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
                // 如果输入框为空，保持原来的注音不变
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
    
    // 片假名转换即时切换功能
    function toggleKatakanaDisplay(showKatakanaReading) {
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
    
    // 片假名转平假名的辅助函数
    function katakanaToHiragana(katakanaString) {
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
    
    // 同步歌词格式的函数
    function syncLyricsFormat() {
        const inputText = lyricsInput.value;
        const inputLines = inputText.split('\n');
        const outputParagraphs = lyricsOutput.querySelectorAll('p');
        
        // 创建新的输出HTML
        let newOutputHtml = '';
        
        // 为每个输入行创建对应的输出段落
        for (let i = 0; i < inputLines.length; i++) {
            const inputLine = inputLines[i];
            
            if (!inputLine.trim()) {
                // 空行
                newOutputHtml += '<p></p>';
                continue;
            }
            
            // 查找对应的已有段落
            let matchingParagraph = null;
            for (let j = 0; j < outputParagraphs.length; j++) {
                const existingP = outputParagraphs[j];
                const existingText = getPlainTextFromParagraph(existingP);
                
                // 如果找到匹配的内容，使用现有的注音
                if (existingText.trim() === inputLine.trim()) {
                    matchingParagraph = existingP;
                    break;
                }
            }
            
            if (matchingParagraph) {
                // 使用现有的注音段落
                newOutputHtml += `<p>${matchingParagraph.innerHTML}</p>`;
            } else {
                // 这是新增的行，需要重新生成注音
                newOutputHtml += `<p><span class="pending-generation" data-text="${inputLine}">[待生成: ${inputLine}]</span></p>`;
            }
        }
        
        // 更新输出区域
        lyricsOutput.innerHTML = newOutputHtml;
        
        // 为新增的行生成注音
        const pendingElements = lyricsOutput.querySelectorAll('.pending-generation');
        if (pendingElements.length > 0) {
            generatePendingLines();
        }
        
        // 重新设置多音字交互
        setupMultiReadingInteraction();
        // 重新设置长按编辑交互
        setupLongpressEditInteraction();
    }
    
    // 从段落元素中提取纯文本内容
    function getPlainTextFromParagraph(paragraph) {
        const rbElements = paragraph.querySelectorAll('rb');
        if (rbElements.length > 0) {
            return Array.from(rbElements).map(rb => rb.textContent).join('');
        } else {
            return paragraph.textContent || '';
        }
    }
    
    // 为新增的行生成注音
    async function generatePendingLines() {
        const pendingElements = lyricsOutput.querySelectorAll('.pending-generation');
        
        for (const element of pendingElements) {
            const text = element.dataset.text;
            element.textContent = '生成中...';
            
            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        lyrics: text,
                        katakana: toggleKatakana.checked
                    }),
                });
                
                if (!response.ok) {
                    throw new Error(`服务器错误: ${response.statusText}`);
                }
                
                const lines = await response.json();
                if (Array.isArray(lines) && lines.length > 0) {
                    const lineTokens = lines[0];
                    if (Array.isArray(lineTokens)) {
                        const lineContent = lineTokens.map(token => {
                            const surface = token?.surface || '';
                            const reading = token?.reading || '';
                            const alternatives = token?.alternatives || [];
                            const altsLabeled = [];
                            const hasAlternatives = token?.has_alternatives || false;
                            const safeReading = (reading === '*' ? '' : reading);
                            const result = generateAdvancedRuby(surface, safeReading);
                            
                            const multiReadClass = hasAlternatives ? ' multi-reading' : '';
                            const alternativesData = hasAlternatives ? ` data-alternatives='${JSON.stringify(alternatives)}'` : '';
                            const altsLabeledData = '';
                            const currentReadingData = ` data-current-reading='${safeReading}'`;
                            
                            let wordHtml = `<span class="word-unit${multiReadClass}"${alternativesData}${altsLabeledData}${currentReadingData}><span class="stack">`;
                            if (result.rt) {
                                wordHtml += `<span class="ruby-wrap"><ruby><rb>${result.baseMain}</rb><rt class="reading-text">${result.rt}</rt></ruby></span>`;
                            } else {
                                wordHtml += `<span class="ruby-wrap"><ruby><rb>${result.baseMain}</rb></ruby></span>`;
                            }
                            if (result.suffix) {
                                wordHtml += `<span class="okurigana">${result.suffix}</span>`;
                            }
                            
                            
                            wordHtml += `</span></span>`;
                            
                            return wordHtml;
                        }).join('');
                        
                        element.outerHTML = lineContent;
                    }
                }
            } catch (error) {
                console.error("生成新行注音失败:", error);
                element.textContent = `[生成失败: ${text}]`;
                element.style.color = '#ff6b6b';
            }
        }
        
        // 重新设置多音字交互
        setupMultiReadingInteraction();
        // 重新设置长按编辑交互
        setupLongpressEditInteraction();
    }
    
    // 导出图片功能实现
    async function exportToImage() {
        // 获取标题和歌词内容
        const titleElement = document.getElementById('output-title-input');
        const lyricsElement = document.getElementById('lyrics-output');
        const title = titleElement.value || '标题';
        
        // 创建导出专用的容器
        const exportContainer = document.createElement('div');
        exportContainer.style.cssText = `
            position: fixed;
            top: -10000px;
            left: 0;
            background: white;
            padding: 40px;
            font-family: 'Noto Sans JP', sans-serif;
            box-sizing: border-box;
            min-height: 400px;
            width: auto;
            display: inline-block;
        `;
        
        // 添加标题
        const titleDiv = document.createElement('div');
        titleDiv.style.cssText = `
            font-size: 2em;
            font-weight: bold;
            color: #333;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #008B8B;
        `;
        titleDiv.textContent = title;
        
        // 复制歌词内容
        const lyricsDiv = document.createElement('div');
        lyricsDiv.innerHTML = lyricsElement.innerHTML;
        lyricsDiv.style.cssText = `
            font-size: 1.3em;
            line-height: 2.8;
            color: #333;
            width: auto;
            display: inline-block;
        `;
        
        // 设置导出时的ruby样式
        const style = document.createElement('style');
        style.textContent = `
            .export-container ruby {
                ruby-position: over;
                ruby-align: center;
                line-height: 1;
            }
            .export-container ruby rt {
                font-size: 0.7em;
                color: #FF4500;
                white-space: nowrap;
                text-align: center;
            }
            .export-container ruby rb {
                line-height: 1;
            }
            .export-container p {
                margin: 0 0 10px 0;
                line-height: 2.8;
                white-space: nowrap;
                overflow: visible;
                display: inline-block;
                width: auto;
            }
            .export-container p:empty {
                height: 1.7em;
            }
            .export-container .word-unit {
                display: inline-block;
                margin: 0 0.3em;
                vertical-align: baseline;
                position: relative;
                line-height: 1;
            }
            .export-container .stack {
                display: inline-block;
                vertical-align: baseline;
                text-align: center;
            }
            .export-container .ruby-wrap {
                line-height: 1;
            }
            .export-container .okurigana {
                line-height: 1;
                padding-left: 0.05em;
            }
        `;
        
        exportContainer.className = 'export-container';
        exportContainer.appendChild(titleDiv);
        exportContainer.appendChild(lyricsDiv);
        document.head.appendChild(style);
        document.body.appendChild(exportContainer);
        
        // 自动检测内容宽度并进行缩放调整
        const targetWidth = 900; // 目标宽度
        
        // 测量标题宽度
        const titleWidth = titleDiv.scrollWidth;
        
        // 测量每行歌词的宽度，找到最宽的行
        const paragraphs = lyricsDiv.querySelectorAll('p');
        let maxLyricsWidth = 0;
        
        paragraphs.forEach(p => {
            if (p.textContent.trim()) { // 跳过空行
                const pWidth = p.scrollWidth;
                if (pWidth > maxLyricsWidth) {
                    maxLyricsWidth = pWidth;
                }
            }
        });
        
        // 取标题和歌词中的最大宽度，加上padding
        const actualContentWidth = Math.max(titleWidth, maxLyricsWidth);
        const actualWidth = actualContentWidth + 80; // 加上左右padding (40px * 2)
        
        let scaleRatio = 1;
        let finalWidth = Math.max(targetWidth, actualWidth);
        let finalHeight = Math.max(400, exportContainer.scrollHeight + 80);
        
        if (actualWidth > targetWidth) {
            // 内容超宽，需要缩放
            scaleRatio = targetWidth / actualWidth;
            console.log(`内容过宽 (实际:${actualWidth}px，目标:${targetWidth}px)，应用缩放比例: ${scaleRatio.toFixed(3)}`);
            
            // 应用缩放变换
            exportContainer.style.transform = `scale(${scaleRatio})`;
            exportContainer.style.transformOrigin = 'top left';
            
            // 调整容器尺寸以适应缩放后的内容
            finalWidth = targetWidth;
            finalHeight = Math.max(400, exportContainer.scrollHeight * scaleRatio + 80);
            
            // 设置容器的实际尺寸
            exportContainer.style.width = `${actualWidth}px`;
        } else {
            // 内容宽度正常，不需要缩放
            exportContainer.style.width = `${actualWidth}px`;
            finalWidth = actualWidth;
            console.log(`内容宽度正常 (${actualWidth}px)，无需缩放`);
        }
        
        try {
            // 使用html2canvas生成高清图片
            const canvas = await html2canvas(exportContainer, {
                scale: 3, // 3倍分辨率，确保高清
                backgroundColor: '#ffffff',
                useCORS: true,
                allowTaint: true,
                width: finalWidth,
                height: finalHeight,
                scrollX: 0,
                scrollY: 0,
                logging: false
            });
            
            // 创建下载链接
            const link = document.createElement('a');
            link.download = `${title}_注音歌词_${new Date().getFullYear()}${(new Date().getMonth() + 1).toString().padStart(2, '0')}${new Date().getDate().toString().padStart(2, '0')}.png`;
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
            
            console.log('图片导出成功');
            
        } finally {
            // 清理临时元素
            document.body.removeChild(exportContainer);
            document.head.removeChild(style);
        }
    }
    
    // 点击页面其他地方时隐藏菜单
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multi-reading') && !e.target.closest('.reading-menu')) {
            hideReadingMenu();
        }
    });
});