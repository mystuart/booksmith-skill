# 排版规范

本文件定义电子书的排版参数。分为两部分：

**第一部分：通用排版规范** — 用自然语言描述所有排版参数，方便用户理解和调整。  
**第二部分：方案实现示例** — 各排版引擎（Typst / ReportLab / Chrome Headless）的具体实现。

---

## 目录

### 第一部分：通用排版规范
- [页面尺寸](#页面尺寸)
- [版面风格](#版面风格)
- [配色体系](#配色体系)
- [字体体系](#字体体系)
- [字号体系](#字号体系)
- [行距与段距](#行距与段距)
- [标题间距](#标题间距)
- [元素样式](#元素样式)
- [间距体系](#间距体系)
- [分页规则](#分页规则)
- [格式优先建议](#格式优先建议)

### 第二部分：方案实现示例
- [Typst 方案](#typst-方案)
- [ReportLab 方案](#reportlab-方案)
- [Chrome Headless 方案（已弃用）](#chrome-headless-方案已弃用)

---

# 第一部分：通用排版规范

## 页面尺寸

```
纸张：A4
页边距：上 22mm / 右 20mm / 下 28mm / 左 20mm
```

页脚显示页码，底部居中。无页眉。

---

## 版面风格

Booksmith 提供 4 种预设版面风格。每种风格在字体、间距、缩进策略上有显著差异，适配不同类型的书籍。

选择风格：
```yaml
layout_style: modern   # classic | modern | academic | minimal
```

### 风格参数总览

| 风格 | 正文字体 | 标题字体 | 首行缩进 | 行距 | 段距 | H1上 | H1下 | H2上 | H2下 | H3上 | H3下 | 列表间距 | 对齐 | 适用场景 |
|------|---------|---------|---------|------|------|------|------|------|------|------|------|---------|------|---------|
| **classic** | Noto Serif SC | Noto Serif SC | 2em | 1.8 | 1.2 | 2.0 | 1.2 | 1.5 | 1.0 | 1.2 | 0.8 | 0.6 | 两端对齐 | 文学、人文、通识读物 |
| **modern**（默认） | Noto Sans SC | Noto Serif SC | 无 | 1.7 | 1.0 | 2.0 | 1.2 | 1.5 | 1.0 | 1.2 | 0.8 | 0.7 | 两端对齐 | 技术书、科普、商业 |
| **academic** | Noto Serif SC | Noto Serif SC | 1.5em | 1.6 | 0.8 | 1.8 | 1.0 | 1.2 | 0.8 | 1.0 | 0.6 | 0.5 | 两端对齐 | 论文、研究报告 |
| **minimal** | Noto Sans SC | Noto Sans SC | 无 | 1.9 | 1.5 | 2.5 | 1.5 | 1.8 | 1.0 | 1.5 | 0.8 | 0.6 | 左对齐 | 设计类、画册、轻阅读 |

> 上表中所有间距值单位为 em。H1/H2/H3 列表示该级标题的上方/下方间距。此表是排版参数的**唯一真相源**——`booksmith-typst.py` 的硬编码默认值必须与本表严格一致。

### 风格详解

**classic**：传统书籍排版。衬线正文 + 首行缩进 + 较大行距，营造沉浸式阅读体验。适合长段落、叙事性内容。

**modern**：技术书标准排版。无衬线正文（屏幕阅读友好）+ 段落间距分隔（无首行缩进）+ 清晰的标题层次。适合代码、列表、表格密集的内容。

**academic**：紧凑严谨。衬线正文 + 小首行缩进 + 紧凑段距 + 较小字号（10.5pt）。适合参考文献、脚注密集的学术文本。

**minimal**：大量留白。无衬线 + 无缩进 + 最大行距和段距 + 无两端对齐。适合配图多、短段落的内容，如设计书、摄影集。

### 代码主题

```yaml
code_theme: light   # light | dark
```

| 主题 | 代码块背景色 | 代码文字色 | 适用场景 |
|------|-------------|-----------|---------|
| **light**（默认） | `#F5F5F5` 浅灰 | 正文色 | 白底书籍、打印 |
| **dark** | `#1E1E2E` 深紫黑 | `#D9E0EE` 浅紫白 | 深色风格书籍、屏幕阅读 |

### 自定义覆盖

在 `layout.md` 中可以用以下语法覆盖预设参数：

```yaml
# 覆盖正文行高
正文行高：1.75

# 覆盖页边距（单位 cm）
margin: 2.5cm 2.2cm 2.5cm 2.2cm

# 覆盖正文字号
正文字号：10.5pt

# 覆盖标题间距（单位 em）
H1 上方间距：2.5
H1 下方间距：1.5
H2 上方间距：1.8
H2 下方间距：1.2
H3 上方间距：1.5
H3 下方间距：0.8

# 覆盖列表项间距（单位 em）
列表项间距：1.0
```

---

## 配色体系

配色通过语义名称定义，各排版引擎映射到各自的语法。

```yaml
colors:
  primary: "#312E81"      # 主色：章节标题、表头背景
  secondary: "#4338CA"    # 辅色：次级标题、提示框左边框
  accent: "#D97706"       # 强调色：代码文字、命令、操作提示
  text: "#2D2D2D"         # 正文文字
  muted: "#6B7280"        # 次要文字：日期、副标题
  code-bg: "#F5F5F5"      # 代码块背景
  tip-bg: "#EEF2FF"       # 提示框背景
  tip-border: "#C7D2FE"   # 提示框边框
```

> **兼容说明**：上述语义名称在 CSS 方案中对应 `--indigo`、`--indigo-light`、`--amber`、`--text`、`--gray`、`--code-bg`、`--tip-bg`、`--tip-border`。旧项目如需迁移，直接替换变量名即可。

### 配色快捷方案

| 风格 | primary | secondary | accent | tip-bg |
|------|---------|-----------|--------|--------|
| 深靛+琥珀（默认） | #312E81 | #4338CA | #D97706 | #EEF2FF |
| 蓝色调 | #2563EB | #60A5FA | #EA580C | #EFF6FF |
| 绿色调 | #059669 | #34D399 | #D97706 | #ECFDF5 |
| 红棕调 | #B91C1C | #F87171 | #92400E | #FEF2F2 |
| 中性灰 | #374151 | #6B7280 | #B45309 | #F3F4F6 |

---

## 字体体系

| 用途 | 字体 | 字重 |
|------|------|------|
| 正文 | Noto Sans SC（modern/minimal）/ Noto Serif SC（classic/academic） | 400 |
| 加粗 | 同正文 | 700 |
| 标题（封面、章节） | Noto Serif SC | 900 |
| 代码 | JetBrains Mono | 400 |

### 字体安装

| 字体 | 用途 | macOS 安装命令 |
|------|------|---------------|
| Noto Sans SC | 正文（modern/minimal） | `brew install font-noto-sans-cjk-sc` |
| Noto Serif SC | 正文（classic/academic）、标题 | `brew install font-noto-serif-cjk-sc` |
| JetBrains Mono | 代码块 | `brew install font-jetbrains-mono` |

---

## 字号体系

| 元素 | 字号 |
|------|------|
| 正文 | 11pt |
| 章节标题（H1） | 20pt |
| 节标题（H2） | 14pt |
| 子节标题（H3） | 12pt |
| 封面主标题 | 32pt |
| 代码块 | 正文 - 2.5pt（最小 8pt） |
| 内联代码 | 同代码块 |
| 表格 | 同正文 |

---

## 行距与段距

**行内行距**（同一行内的行高倍数）：
```
modern：1.7em
classic：1.8em
academic：1.6em
minimal：1.9em
代码块：1.7em
```

**段落间距**（段落之间的额外间距）：
```
modern：1.0em
classic：1.2em
academic：0.8em
minimal：1.5em
```

---

## 标题间距

各级标题与前后内容之间的间距（per-style 值见上方风格参数总览表）：

> 参数表中已按风格列出 H1/H2/H3 的上方和下方间距。此节保留作为通用参考。

| 级别 | 通用参考值 | 说明 |
|------|---------|------|
| H1（章节标题） | 上 2.0em / 下 1.2em | 各风格可微调 |
| H2（节标题） | 上 1.5em / 下 1.0em | 下方应 < H1 下方 |
| H3（子节标题） | 上 1.2em / 下 0.6em | 下方应明显 < H2 下方 |

---

## 元素样式

### 代码块

- 背景色：`code-bg`（light 主题 `#F5F5F5`，dark 主题 `#1E1E2E`）
- 文字色：正文色（light）/ 浅紫白（dark）
- 字体：JetBrains Mono
- 字号：正文 - 2.5pt（最小 8pt）
- 内边距：10pt
- 圆角：4pt
- 边框：0.5pt 浅灰（light）/ 0.5pt 深灰（dark）
- 语法高亮：支持 json / python / bash 等语言标注

### 内联代码

- 字体：JetBrains Mono
- 颜色：`accent`（琥珀色 `#D97706`）
- 字号：同代码块

### 提示框 / 引用块

- 背景色：`tip-bg`（浅蓝 `#EEF2FF`）
- 左边框：3pt `secondary`（靛蓝）
- 内边距：8pt
- 圆角：2pt

### 表格

- 表头背景：`primary`（深靛蓝）
- 表头文字：白色
- 交替行背景：浅灰 `#F9F8F5`
- 边框：0.5pt 浅棕 `#DDD8C8`
- 单元格内边距：6pt
- 对齐：左对齐

---

## 间距体系

| 元素 | 上下间距 |
|------|---------|
| 代码块 | 1.0em |
| 表格 | 1.0em |
| 图片 | 2.0em |
| 列表项 | 见风格参数总览表（per-style） |

---

## 配置传递流程

排版参数有三层来源，优先级从低到高：

```
Python _STYLE_PRESETS（硬编码默认值，必须匹配本文件风格参数总览表）
    ↓  被覆盖
项目 layout.md 参数覆盖（用户在书籍项目的 layout.md 中用自然语言语法覆盖）
    ↓  被覆盖
--style 命令行参数（强制指定风格，忽略 layout.md 中的 layout_style）
```

**覆盖优先级**：命令行 > 项目 layout.md 覆盖 > Python 硬编码默认值

所有三种来源的参数名称和取值范围以本文件「风格参数总览」表为准。

**参数校验规则**：
- `leading`：允许范围 1.3~2.0，低于 1.5 时警告"行距过紧，中文长段阅读疲劳"
- `paragraph_spacing`：允许范围 0.5~2.0，高于 1.5 时警告"段距过大，页面松散"
- `h3_below`：应 ≤ `h2_below`，否则警告"H3 下方间距大于 H2，层级扁平"
- `list_spacing`：应 < `paragraph_spacing`，否则警告"列表间距 ≥ 段距，失去紧凑感"

---

## 分页规则

- 封面独占一页
- 目录独占一页
- 每章从新页开始
- 提示框/术语卡片不拆页

---

## 格式优先建议

排版前，扫描手稿文件检查以下格式问题。存在任意一项时，建议先格式化手稿：

| 问题类型 | 判断条件 | 修正示例 |
|---------|---------|---------|
| 粗体标点粘连 | `**` 内紧邻中文后面出现标点 | `**你好,**` → `**你好**，` |
| 中英间距 | 中文和直接相邻的英文字符无空格 | `中文text` → `中文 text` |
| 序列标点混用 | 中文内容中混入英文标点 | `Hello, world！你好。` → 统一标点 |
| 代码块过长 | 单个代码块超过 150 行 | 分段或标注省略 |
| 链接文字过长 | Markdown 链接文字超过 40 字符 | 缩短或用锚文字替代 |

---

# 第二部分：方案实现示例

## Typst 方案（默认，推荐）

### 运行命令

```bash
# 默认风格（从 layout.md 读取）
python3 scripts/booksmith-typst.py \
  ~/Books/[project-dir] --output ebook.pdf

# 强制指定版面风格
python3 scripts/booksmith-typst.py \
  ~/Books/[project-dir] --output ebook.pdf --style modern

# 保存 .typ 源码用于调试
python3 scripts/booksmith-typst.py \
  ~/Books/[project-dir] --save-typ debug.typ
```

### 脚本功能

- 自动读取 `project.json` 获取书名
- 自动合并 `manuscript/*.md`（按 ch01-chNN → appendix-a/b 排序）
- 解析 `layout.md` 提取配色、版面风格、字号、边距
- Typst 原生 CJK 混排（无需字体候选表）
- 生成封面 + 可点击 TOC + PDF 书签 + 页码

### 依赖

```bash
pip install typst
```

字体需本地安装（见「字体体系」章节的 macOS 安装命令）。

### 图片路径

手稿中的图片路径应为**相对于项目根目录**：
```markdown
![img1](illustrations/img1.jpg)
```
Typst 编译时以项目目录为 `root`。

### 字体路径

脚本自动扫描以下系统字体目录：
- macOS: `/System/Library/Fonts`、`/Library/Fonts`、`~/Library/Fonts`
- Linux: `/usr/share/fonts`、`~/.local/share/fonts`
- Windows: `C:\Windows\Fonts`

---

## ReportLab 方案（回退）

当 Typst 不可用时使用。

```bash
python3 scripts/booksmith-rl.py \
  ~/Books/[project-dir] --output ebook.pdf
```

ReportLab 方案使用 Python 原生 PDF 生成，不依赖外部排版引擎。但 CJK 支持较弱，排版精度不如 Typst。

---

## Chrome Headless 方案（已弃用）

> ⚠️ **已弃用**。Booksmith v1.0 使用 Chrome headless 生成 PDF，v1.1 起改用 Typst。以下为历史参考，新项目请勿使用。

### 原理

将 Markdown 转换为 HTML，通过 Chrome 的 `--print-to-pdf` 功能生成 PDF。

### 命令

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="输出路径.pdf" \
  "file:///HTML文件路径.html"
```

### 局限

- Chrome 对 CSS `counter(page)` 支持不完善，页码控制困难
- 需要处理字体加载、背景色保留等问题
- CJK 排版需要额外字体配置
- 长文档性能差

### 相关 CSS 参考（历史）

```css
@page {
  size: A4;
  margin: 2.2cm 2cm 2.8cm 2cm;
}

@media print {
  body { font-size: 11pt; }
  .content { max-width: 100%; padding: 0; }

  /* 保留背景色 */
  .tip, th, pre.codeblock {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
```
