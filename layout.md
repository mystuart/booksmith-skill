# 排版规范

本文件定义电子书的排版参数。修改此文件即可全局调整排版风格，无需改动主 Skill。

---

## 目录

- [页面尺寸](#页面尺寸)
- [内容区域](#内容区域)
- [页眉页脚](#页眉页脚)
- [字体](#字体)
- [字号](#字号)
- [行高](#行高)
- [配色](#配色)
- [元素对齐规范](#元素对齐规范)
- [分页规则](#分页规则)
- [间距体系](#间距体系)
- [打印适配](#打印适配)
- [PDF 生成命令](#pdf-生成命令)
- [格式优先建议](#格式优先建议)

---

## 页面尺寸

```
纸张：A4
页边距：上 2.2cm / 下 2.2cm / 左 2cm / 右 2cm
```

## 内容区域

```
正文最大宽度：680px
正文内边距：0 2rem
```

## 页眉页脚

```
页眉：无
页脚：显示页码（默认开启）
```

如果需要关闭页码，注释掉以下 CSS 中的 `@bottom-center` 行。

如果需要额外的页脚文字（如书名/公众号），使用字符串拼接：
```css
@bottom-center { content: "书名 | 公众号 @xxx | 第 " counter(page) " 页"; }
```

---

## 字体

| 用途 | 字体 | 粗细 |
|------|------|------|
| 正文 | Noto Sans SC | 400 |
| 加粗 | Noto Sans SC | 700 |
| 标题（封面、章节） | Noto Serif SC | 900 |
| 代码 | JetBrains Mono | 400 |

字体加载源：
```
https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@600;700;900&family=JetBrains+Mono:wght@400;500&display=swap
```

如果需要离线字体，替换为本地 @font-face 声明。

## 字号

| 元素 | 屏幕字号 | 打印字号 |
|------|---------|---------|
| 正文 | 15px | 11pt |
| 章节标题 | 1.9rem | — |
| 封面主标题 | 2.4-2.8rem | — |
| 术语名称 | 1.25rem | — |
| 英文副标题 | 0.88rem | — |
| 提示框 | 0.92rem | — |
| 表格 | 0.88-0.9rem | — |
| 代码块 | 0.85rem | — |

## 行高

```
正文行高：1.85
提示框行高：1.85
代码块行高：1.7
```

---

## 配色

```css
--indigo: #312E81;       /* 主色：章节标签、术语标题、表头背景 */
--indigo-light: #4338CA;  /* 辅色：提示框左边框 */
--amber: #D97706;         /* 强调色：代码文字、命令、操作提示 */
--text: #2D2D2D;          /* 正文文字 */
--gray: #6B7280;          /* 次要文字：英文名、日期、副标题（WCAG AA 达标） */
--code-bg: #F5F5F5;       /* 代码块背景 */
--tip-bg: #EEF2FF;        /* 提示框背景 */
--tip-border: #C7D2FE;    /* 提示框边框（备用） */
```

如需更换主题色，只改这里的 hex 值即可。其他元素全部通过 var() 引用。

### 配色快捷方案

| 风格 | --indigo | --indigo-light | --amber | --tip-bg |
|------|----------|---------------|---------|----------|
| 深靛+琥珀（默认） | #312E81 | #4338CA | #D97706 | #EEF2FF |
| 蓝色调 | #2563EB | #60A5FA | #EA580C | #EFF6FF |
| 绿色调 | #059669 | #34D399 | #D97706 | #ECFDF5 |
| 红棕调 | #B91C1C | #F87171 | #92400E | #FEF2F2 |
| 中性灰 | #374151 | #6B7280 | #B45309 | #F3F4F6 |

---

## 元素对齐规范

### 铁律：所有内容元素左右对齐

```css
/* 图片 */
.ebook-img {
  width: 100%;
  max-width: 600px;   /* 不超过正文宽度 */
  display: block;
  margin: 2rem auto;
  border-radius: 10px;
}

/* 横幅图（21:9 / 16:9）可以更宽 */
.ebook-img.banner {
  max-width: 100%;
  border-radius: 8px;
}

/* 表格 */
table {
  width: 100%;
  border-collapse: collapse;
}

/* 代码块 */
pre.codeblock {
  width: 100%;
  overflow-x: auto;        /* 屏幕端：长代码可横向滚动 */
  white-space: pre-wrap;   /* 打印/PDF 端：自动换行 */
  word-break: break-all;   /* 超长单词/URL 强制换行 */
}

/* 铁律：pre.codeblock 内部的 code 必须恢复继承，避免强调色背景刺眼 */
pre.codeblock code {
  color: inherit;
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

/* 提示框 */
.tip {
  width: auto;       /* 跟随父容器宽度 */
}
```

### 对齐自检清单

生成 HTML 后，自查以下项目：
- [ ] 所有 `<img>` 都有 `class="ebook-img"` 且居中
- [ ] 所有 `<table>` 都有 `width: 100%`
- [ ] 所有 `<pre>` 都有 `overflow-x: auto` 和 `white-space: pre-wrap; word-break: break-all;`
- [ ] 没有元素的实际渲染宽度超出 `.content` 的 680px
- [ ] 图片、表格、代码块的左右边距视觉一致
- [ ] 提示框没有比正文更窄或更宽

---

## 分页规则

```css
/* 封面独占一页 */
.cover { page-break-after: always; }

/* 目录独占一页 */
.toc { page-break-after: always; }

/* 每章从新页开始 */
.chapter { page-break-before: always; }

/* 术语卡片不拆页 */
.term { page-break-inside: avoid; }

/* 末尾引导页从新页开始 */
.ending { page-break-before: always; }
```

---

## 间距体系

| 元素 | margin-bottom |
|------|-------------|
| 章节引言 (ch-intro) | 2rem |
| 术语块 (term) | 2.5rem |
| 术语分割线 (term-sep) | — (margin-top: 0.5rem) |
| 提示框 (tip) | 0.8rem top / 0.5rem bottom |
| 代码块 (codeblock) | 0.8rem top+bottom |
| 表格 | 1rem top+bottom |
| 图片 | 2rem top+bottom |

---

## 打印适配

```css
@page {
  size: A4;
  margin: 2.2cm 2cm 2.8cm 2cm;  /* 下方多留空间放页码 */
}
```

**页码实现方式**：

Chrome headless 的 `@page` CSS 计数器支持有限。页码通过以下两种方案实现：

**方案 A（推荐）：不加 `--print-to-pdf-no-header`，用 Chrome 默认页脚**

Chrome 默认页脚会显示页码。只需在 PDF 命令中**去掉** `--print-to-pdf-no-header` 和 `--no-pdf-header-footer`，Chrome 会自动在底部居中显示页码。默认格式：`1 / N`。

缺点：同时会显示日期和文件路径在页眉。

**方案 B（精确控制）：HTML 内嵌页码 + JavaScript**

在 HTML 底部加入 JavaScript 计数页码，配合 CSS fixed 定位：

```css
.page-number {
  position: fixed;
  bottom: 0.5cm;
  width: 100%;
  text-align: center;
  font-size: 0.75rem;
  color: #bbb;
}
```

由于 Chrome headless 对 CSS `counter(page)` 支持不完善，实际生产中建议 **方案 A**（接受默认页眉页脚），或在 HTML 末尾手动标注章节页码范围。

**如果用户不要页眉只要页码**：用 `--print-to-pdf-no-header` 去掉所有，然后在 HTML 里用 `position: fixed` 模拟页码（但此方案在长文档中页码不会自动递增，仅适合短文档）。

```css

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

## PDF 生成命令

**带页码版（默认）**：
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="输出路径.pdf" \
  "file:///HTML文件路径.html"
```
Chrome 默认页脚会显示居中页码（格式 `1/N`）。页眉会显示标题和日期。

**无页眉页脚版**：
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="输出路径.pdf" \
  --print-to-pdf-no-header \
  --no-pdf-header-footer \
  "file:///HTML文件路径.html"
```

**默认使用带页码版**，除非用户明确要求不要页码。

---

## 格式优先建议

### 判断标准

Phase 5 HTML 组装前，扫描手稿文件（如 `manuscript/ch01.md`）的 Markdown 源码，检查是否存在以下明显格式问题。存在任意一项时，建议用户先跑 `baoyu-format-markdown` 格式化手稿：

| 问题类型 | 判断条件 | 示例 |
|---------|---------|------|
| 粗体标点粘连 | `**` 内紧邻中文后面出现中英文标点 | `**你好,**`、`**很好。**` → `**你好**，**很好**` |
| 中英间距 | 中文和直接相邻的英文字符无空格 | `中文text`、`中文123` → `中文 text`、`中文 123` |
| 序列标点混用 | 中文内容中混入英文标点（尤其句号/逗号） | `Hello, world！你好。` 需统一 |
| 代码块过长 | 单个代码块超过 150 行（PDF 阅读体验差） | 分段或标注省略 |
| 链接文字过长 | Markdown 链接文字超过 40 字符 | 缩短或用锚文字替代 |

### 触发格式化的好处

- HTML 转换后标点显示正确（无倒叹号、问号问题）
- 中英混排阅读体验更佳
- PDF 排版一致性好，减少 Phase 6 精炼的格式修改负担

### 不触发格式化的条件

以下情况**不**建议先格式化（直接排版即可）：
- 用户已明确说「不用格式化，直接排版」
- 手稿已通过 `baoyu-format-markdown` 处理过
- 格式化会导致明显内容变化（如用户的手动强调被重新格式化）

### baoyu-format-markdown 协作说明

**调用方式**：
```
delegate_task → baoyu-format-markdown skill，处理 manuscript/ 下的所有 .md 文件
```

**输出**：`baoyu-format-markdown` 默认输出为 `{原文件名}-formatted.md`。建议追加 `--replace` 模式直接覆盖原文件（或手动 rename 覆盖）。

**协作流程**：
```
Phase 5 开始
    ↓
格式扫描（Agent 人工判断，不调用工具）
    ↓
发现问题 → 提示用户「建议先跑 baoyu-format-markdown」
    ├── 用户同意 → 调用 baoyu-format-markdown → 排版继续
    └── 用户拒绝 → 直接进入排版自检
    ↓
排版自检 → HTML 组装 → PDF
```

**偏好集成**：`baoyu-format-markdown` 的格式参数（粗体策略、标点规则等）可通过 Booksmith Extend 偏好系统（`EXTEND.md`）积累用户偏好，后续 Phase 5 格式扫描时使用用户偏好的参数而非硬编码默认值。
