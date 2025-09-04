# 日语平假名注音器

网页版 https://ciaran272.github.io/j26/
-首次加载后端会略久
-一个为日语文本（自用于日语歌词）自动生成平假名注音的小工具，支持多音字候选、片假名→平假名即时切换。

- 分词/读音：Sudachi + `sudachidict-full`
- 多音字：结合上下文、白名单与外部词典（JMdict/Kanjidic2，可选）
- 前端：即时渲染 `<ruby>`，段落与片假名转换实时同步
- 同源服务：Flask 托管前端静态文件与 API

## 目录结构

```
index.html
script.js
style.css
server.py
requirements.txt
start.bat
```

## 本地版（Windows）

1) 双击 `start.bat`
- 创建并激活虚拟环境 `.venv`
- 安装依赖（含 `sudachidict-full`，首次较慢）
- 启动 Flask 服务

2) 浏览器访问 `http://127.0.0.1:5000/`
- 在文本框粘贴日语文本
- 点击“生成注音”获取结果

## 手动启动（可选）

```powershell
# 进入项目目录
cd <项目路径>

# 可选：创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动后端
python server.py
```

## API 说明

- 路径：`POST /api/furigana`
- 请求体：
```json
{ "lyrics": "あなたがいた夏", "katakana": true }
```
- 响应：按行返回分词结果。每个 token：
  - `surface`: 原文
  - `reading`: 平假名读音（可能为空字符串）
  - `alternatives`: 备选读音（字符串数组）
  - `has_alternatives`: 是否存在多个可选读音

```json
[
  [
    { "surface": "夏", "reading": "なつ", "alternatives": ["なつ"], "has_alternatives": false }
  ]
]
```
- 说明：
  - 对空白和标点保持原样
  - 纯片假名且长度>1 的词是否显示注音由 `katakana` 控制（即时切换）


## 常见问题

- Q: 首次安装很久？
  - A: `sudachidict-full` 体积较大，下载时间较长属正常现象。

- Q: 按下“生成注音”无响应？
  - A: 确认终端中 `server.py` 正在运行且无错误；刷新页面重试。

- Q: 想让长行自动换行？
  - A: 在 `style.css` 中将 `.lyrics-container p { white-space: nowrap; }` 改为 `white-space: normal;`。

- Q: 我能不用 `full` 字典吗？
  - A: 可以改为 `sudachidict-core`，安装更快，但覆盖较少。你的场景推荐继续使用 `full`。

## 

- 后端入口：`server.py`（Flask + Sudachi）
- 前端逻辑：`script.js`（调用 `/api/furigana` 并渲染注音）
- 样式：`style.css`

## 许可与数据来源

- 代码：遵循各依赖的开源许可（Flask BSD/MIT，SudachiPy Apache-2.0 等）。
- 词典数据：本项目使用 EDRDG 的 JMdict 与 KANJIDIC2 数据，按 CC BY-SA 4.0 许可使用与分发；我们对数据做了格式转换/裁剪。
  - EDRDG: https://www.edrdg.org/
  - CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/