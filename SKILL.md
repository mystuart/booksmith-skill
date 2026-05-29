---
name: booksmith
version: 1.2.0
description: |
  出版级技术书制作引擎——当用户想要创建一本技术书籍、手册、PDF 文档时使用。
  即使用户没有明确说"写书"，只要提到"帮我整理成文档""做个技术手册""出一本教程""把这些问题整理成册""我想把这些内容变成一本完整的书""写一本技术指南""做个操作手册""把知识沉淀成一本书"，都应触发本 Skill。
  支持多 Agent 并行调研、风格锚定、逐章顺序写作（上下文累积）、达尔文进化质量验证（种群进化 + trainable/holdout 分割）、双 Agent 精炼、排版出 PDF。
  触发词：「写本书」「出本书」「做本电子书」「ebook」「写个小册子」「做个手册」「技术书」「帮我写一本」「出版级」「写技术书」「整理成书」「做个教程」「出一本教程」「把内容整理成册」「技术指南」「操作手册」
---

# Booksmith — 出版级技术书制作引擎

> 借鉴 darwinian-evolver 的达尔文进化机制和 Phase 间的独立验证，将写书拆解为可验证的分阶段流水线。
> 核心理念：**调研先行 → 风格锚定 → 逐章递进 → 独立验证 → 精炼交付**

## 配置文件

本 Skill 由以下文件组成：

| 文件 | 职责 | 何时修改 |
|------|------|--------|
| `SKILL.md`（本文件） | 主流程、Phase 定义、关键原则 | 改流程逻辑时 |
| `references/phase-instructions.md` | 各 Phase 详细执行指令和 Agent 模板 | 改具体执行细节时 |
| `references/style-guide.md` | 出版风格：O'Reilly/Academic/Handbook 三种风格模板 | 改写作风格时 |
| `layout.md` | 排版规范：配色、字体、间距、对齐、分页、PDF 命令 | 改排版风格时 |
| `illustration.md` | 插图规范：生图工具、风格模板、比例、压缩 | 改插图风格时 |
| `references/typography-standards.md` | 排版参数行业标准参考：行距、段距、标题间距最佳实践 | 调整间距时 |
| `references/examples.md` | 各 Phase 的 Input/Output 示例 | 改示例时 |
| `references/extend-schema.md` | 偏好系统 JSON Schema 完整定义 | 改偏好字段时 |
| `references/iron-rules.md` | 全局铁律：写作/排版/命名/调研铁律、禁止事项、已知陷阱、诚实边界 | 查阅规则时 |
| `EXTEND.md` | Booksmith Extend 偏好系统 — 用户级跨项目偏好记忆 | 理解偏好机制时 |
| `cache/darwinian-evolver/` | DarwinianEvolver 上游克隆（达尔文进化引擎） | Phase 4 进化写作时 |

**执行时必须读取前 6 个文件。其余为开发调试用。**

## 总体流程

```
Phase 0  需求确认 & 项目初始化
Phase 1  深度调研（多 Agent 并行）
Phase 1.5  调研 Review 检查点
Phase 2  内容架构 & 风格锚定
Phase 3  逐章顺序写作（上下文累积）
Phase 4  质量验证
Phase 5  排版 & 插图 & PDF
Phase 6  双 Agent 精炼
Phase 7  交付
```

---

# Phase 0：需求确认 & 项目初始化

## 需求确认

触发后，向用户确认以下参数（能从指令推断的不问）：

> **收到，准备制作技术书。请确认：**
>
> 1. **书名**：「{推断}」，可以吗？
> 2. **目标读者**：小白 / 有基础 / 专业人士？
> 3. **出版风格**：O'Reilly（对话式技术书）/ Academic（学术报告）/ Handbook（操作手册）？
> 4. **篇幅偏好**：精简（8-12 章）/ 详尽（15+ 章）？
> 5. **是否需要插图**：是 / 否？
> 6. **末尾引导**：需要加公众号/个人品牌引导吗？
>
> 直接回复修改项即可，没问题的我直接开始。

**快捷模式**：用户指令信息充分时跳过确认直接执行。

**关键词快捷模式**：用户指令中出现以下词汇时，自动推断参数，无需逐项确认：

| 用户关键词 | 推断参数 |
|-----------|---------|
| 「手册」「操作手册」「指南」「菜谱」 | 出版风格：Handbook |
| 「AI 大模型」「LLM」「GPT」「Claude」 | 出版风格：O'Reilly（默认 AI/技术类） |
| 「学术」「论文」「研究报告」 | 出版风格：Academic |
| 「8-12 章」「精简」「薄」 | 篇幅：精简（8-12 章） |
| 「15+」「详尽」「厚」 | 篇幅：详尽（15+ 章） |
| 「插图」「配图」「有图」 | 插图：是 |

快捷模式下仍展示确认列表，用户可直接修改任何项。

**参数默认值**：
- 目标读者：小白
- 出版风格：O'Reilly
- 篇幅：精简（10-12 章）
- 插图：否
- 末尾引导：无

## 项目初始化

确认后立即创建书籍项目目录：

```
~/Books/[english-slug]/
├── project.json           # 项目参数（必须使用下方标准模板）
├── research/              # 调研产物
├── manuscript/            # 逐章手稿（必须扁平结构，禁止子目录）
│   ├── ch01.md            # 第一章
│   ├── ch02.md            # 第二章
│   └── glossary.md        # 术语追踪表
├── illustrations/         # 插图文件
├── anchor-sample.md       # 风格锚定样板（Phase 2 确认后生成）
└── report.md              # 工作报告（Phase 7 生成）
```

> **命名规则**：目录名和文件名一律使用英文（kebab-case），如 `docker-basics`、`ch01.md`、`research/01-architecture.md`。正文内容使用中文不受此限制。
>
> **目录结构铁律**：
> - `manuscript/` 必须是扁平结构，所有章节文件直接放在此目录下
> - 禁止使用 `manuscript/phase-1/`、`manuscript/chapters/` 等子目录
> - 章节文件命名：`ch01.md`、`ch02.md`...`ch10.md`、`appendix-a.md`
> - 不遵循此结构将导致 PDF 生成失败

**project.json 结构**（必须严格遵循此模板，禁止自定义字段名）：

```json
{
  "title": "书名",
  "subtitle": "副标题",
  "author": "作者名",
  "target_reader": "小白|有基础|专业人士",
  "style": "oreilly|academic|handbook|custom",
  "layout_style": "modern",
  "chapters_planned": 12,
  "has_illustrations": false,
  "brand": { "name": "", "cta": "", "wechat": "", "website": "" },
  "status": "initialized",
  "created": "YYYY-MM-DD",
  "current_phase": 0,
  "chapters_completed": [],
  "delivered_pdf": "ebook.pdf"
}
```

> **字段约束**：
> - `title`：必填，书籍主标题
> - `subtitle`：可选，副标题
> - `author`：可选，作者名
> - `target_reader`：必填，目标读者群体描述
> - `style`：必填，出版风格（oreilly / academic / handbook / custom）
> - `layout_style`：可选，排版风格（classic / modern / academic / minimal），默认 modern。注意与 `style` 字段独立——写作风格和排版风格可以任意组合
> - `chapters_planned`：必填，计划章节数
> - `has_illustrations`：必填，是否有插图（true / false）
> - `status`：必填，项目状态（initialized / researching / anchored / writing / reviewing / layouting / refining / completed）
> - `current_phase`：必填，当前阶段（0-7）
> - `chapters_completed`：必填，已完成章节列表（如 `["ch01","ch02"]`）
> - `delivered_pdf`：可选，输出 PDF 文件名
>
> **禁止行为**：不得使用自定义字段名（如 `book_type`、`target_audience`、`estimated_length` 等），不得修改字段类型。

---

# Phase 1：深度调研

详见 `references/phase-instructions.md` — 「Phase 1 调研 Agent 模板」。

**核心原则：**
- 根据主题拆分为 4-5 个独立方向，派出**真正的并行子 agent**搜索
- 每个子 agent **必须把调研结果写入** `research/0X-[方向简述].md`
- 不存文件的调研等于没做
- **信源分级**：S（一手）/ A（权威）/ B（从业者）/ C（社区）
- **质量要求**：信源总数 ≥ 20，S/A ≥ 50%，关键事实 ≥ 2 独立信源交叉验证
- **黑名单**：不使用百度百科、百度知道

---

# Phase 1.5：调研 Review 检查点

详见 `references/phase-instructions.md` — 「Phase 1.5 调研 Review 表格模板」。

所有 Agent 完成后，**暂停**展示调研质量摘要，供用户确认。

调研质量决定全书上限。垃圾进垃圾出，在这里拦截比写完再返工成本低得多。

---

# Phase 2：内容架构 & 风格锚定

## 2a. 大纲生成

基于调研结果，生成章节大纲。每章包含：
- 章节编号和标题
- 本章覆盖的核心概念（3-8 个）
- 一句话概括本章价值
- 章节间的递进关系

展示给用户确认后继续。

## 2b. 风格锚定

详见 `references/style-guide.md` — 对应风格的「风格锚定执行规范」。

**这是防止全书风格漂移的关键步骤。**

1. 根据选定的出版风格，读取 `references/style-guide.md` 中对应风格的完整模板
2. 用第一章内容，**严格按模板结构**写出完整样板章
3. 展示样板章给用户确认（节奏、深度、板块增删）
4. 用户确认 → 样板存入 `[项目目录]/anchor-sample.md`
5. 更新 `project.json`：`"current_phase": 2, "style_anchored": true`

**锚定样板是全书风格一致性的唯一判据。** 后续章节写作时，必须以样板为风格基准。

---

# Phase 3：逐章顺序写作

详见 `references/phase-instructions.md` — 「Phase 3 逐章写作上下文累积规则」。

**关键设计：刻意不并行。**

虽然并行写所有章节效率更高，但真人写书不是这么干的。每章回看前文，确保行文连贯、叙事递进。这是违反效率直觉但对质量至关重要的设计。

## 执行流程（每章）

```
for each chapter in 大纲顺序:

  1. 读取上下文
     - outline.md（大纲）
     - 已完成的前 N-1 章手稿（最近 2-3 章）
     - anchor-sample.md（风格基准）
     - glossary.md（术语表）
     - 本章相关的调研材料

  2. 定向补充（如需要）
     如果本章涉及调研中未充分覆盖的子主题，
     针对该子主题做定向 WebSearch 补充

  3. 按出版风格模板写完整一章
     - 严格遵循 anchor-sample.md 的风格
     - 遵循 references/style-guide.md 对应风格的结构

  4. 自检
     - 术语在前面是否已定义？如有，引用而非重复定义
     - 与上一章的叙事是否有递进关系？
     - 全书核心论点是否在逐步深化？
     - 与锚定样板风格是否一致？

  5. 写入手稿
     存入 manuscript/chXX.md

  6. 更新术语表
     将本章新定义的术语追加到 manuscript/glossary.md

  7. 展示摘要（可选，章数多时推荐）
     展示本章标题 + 一句话概括 + 引用的前文概念 + 本章字数
```

## 上下文累积规则

详见 `references/phase-instructions.md` — 「Phase 3 逐章写作上下文累积规则」。

---

# Phase 4：质量验证（达尔文进化）

详见 `references/phase-instructions.md` — 「Phase 4 质量验证详细指令」。

**借鉴 darwinian-evolver 的达尔文进化机制。**

Phase 4 不再是两轮"主 agent 检查 + 不通过就重写"的硬判断，而是**章节种群进化**——每章维护一个种群，最优个体持续进化，过拟合由 holdout 机制检测。

## 核心概念

| 概念 | 含义 |
|------|------|
| **Organism** | 一章手稿（原始 markdown 字符串） |
| **Population** | 某章的所有进化个体，等权采样父本 |
| **Evaluator** | 质量评分器：split into trainable / holdout failure cases |
| **Mutator** | LLM 读取 failure cases → 提出改进章节 |
| **Trainable FC** | 暴露给 Mutator 的质量问题 |
| **Holdout FC** | 保留不暴露，用于检测过拟合 |
| **Fitness score** | 加权多维质量分（0–1，越高越好） |

## 质量维度与权重

| 维度 | 权重 | 含义 |
|------|------|------|
| 可读性 | 25% | 段落长度、CJK 密度、碎片化程度 |
| 技术准确性 | 25% | 代码示例、数据表格、数值支撑 |
| 叙事递进 | 20% | 过渡句密度、章末承启、孤儿句比例 |
| 风格一致性 | 15% | Tip/Warning 框、场景开头、无风格违规 |
| 引用质量 | 15% | URL 引用、来源标注 |

## 执行流程（每章）

```
for each chapter in 大纲顺序:

  1. 初始化种群
     将 Phase 3 写出的手稿作为初始 Organism（score=0.6 基准）
     其余父本通过 Mutator 并发生成 N-1 个变异体

  2. 进化循环（5 次迭代，可配置）
     for iter in 1..N:
       a. 加权采样选择父本（sigmoid 性能 × 多样性奖励）
       b. Mutator 并发产生变异体（每父本 1–2 个）
       c. Evaluator 并发评分（trainable + holdout failure cases）
       d. 所有个体加入种群

  3. 过拟合检测
     若 holdout failure cases 比例 > 40%，说明 Mutator 在过拟合 trainable
     → 降低 trainable 暴露比例，增加随机父本选择权重

  4. 选取最优个体
     取种群中 fitness 最高的 Organism 作为本章最终手稿
     记录进化日志（iteration、score、change_summary）

  5. 汇总全书的分数分布
     输出：每章最优分、全书中位数、方差
     用于决定进入 Phase 5 或返回 Phase 3 定向补充
```

## 通过标准（进化视角）

| 信号 | 含义 | 处理 |
|------|------|------|
| 全书中位分 ≥ 0.70 | 整体质量达标 | → Phase 5 |
| 任意章最优分 < 0.50 | 该章存在严重缺陷 | 定向回到 Phase 3 重写该章 |
| holdout 失败率 > 40% | 过拟合信号 | 减少 trainable 暴露，继续进化 |
| 迭代 5 次后中位分无提升（Δ < 0.02） | 进化收敛 | 停止，在工作报告中标注该章薄弱 |

**继续交付条件**：至少 70% 的章节中位分 ≥ 0.60。
其余章节在工作报告中标注薄弱维度，不阻塞交付。

## 达尔文进化脚本

```bash
# 安装（一次性）
mkdir -p ~/.claude/skills/booksmith/cache/darwinian-evolver
cd ~/.claude/skills/booksmith/cache/darwinian-evolver
git clone --depth 1 https://github.com/imbue-ai/darwinian_evolver.git .

# 运行单章进化
cd ~/.claude/skills/booksmith/cache/darwinian-evolver/darwinian_evolver
ANTHROPIC_API_KEY=... uv run --with anthropic python \\
    ~/.claude/skills/booksmith/scripts/booksmith_chapter_evolver.py \\
    --chapter_path ~/Books/[project]/manuscript/ch05.md \\
    --anchor_sample_path ~/Books/[project]/anchor-sample.md \\
    --glossary_path ~/Books/[project]/manuscript/glossary.md \\
    --target_reader 有基础 \\
    --output_dir /tmp/ch05_evolve \\
    --num_iterations 5 --num_parents_per_iteration 4 \\
    --mutator_concurrency 4 --evaluator_concurrency 4

# 查看快照
uv run --with openai python \\
    ~/.claude/skills/booksmith/scripts/show_snapshot.py \\
    /tmp/ch05_evolve/snapshots/iteration_5.pkl
```

> **脚本依赖**：`scripts/booksmith_chapter_evolver.py` 实现 `Organism/Evaluator/Mutator` 接口，
> 调用 `EvolveProblemLoop` 驱动达尔文进化。AGPL-3.0 许可，只在用户本地运行，不上传任何数据。
> 上游 darwinian-evolver 克隆在 `cache/darwinian-evolver/`。

---

# Phase 5：排版 & 插图 & PDF

详见 `references/phase-instructions.md` — 「Phase 5 排版 & 插图 & PDF 详细指令」。

**排版参数**：`layout.md`
**插图参数**：`illustration.md`

## 格式优先建议

**排版前**，如果检测到手稿文件存在明显的 Markdown 格式问题（如粗体标点 `**你好,**`、中英间距不当），**主动建议用户先格式化手稿**，再进行排版。具体判断标准见 `layout.md`「格式优先建议」章节。

此为建议性提示，不阻塞流程——用户选择直接排版时照做。

## 执行流程

1. 格式优先检查（如手稿存在格式问题，提示用户是否要先格式化）
2. 排版自检（对照 layout.md 排版规范）
3. 选择版面风格：从 layout.md 读取 `layout_style`（classic / modern / academic / minimal），或用 `--style` 强制指定
4. 如需插图：规划数量和位置 → 生成锚定图确认 → **prompt 先写入 `illustrations/prompts/`** → 批量生成 → 下载压缩
5. **PDF 生成：调用 `scripts/booksmith-typst.py` 脚本**（Typst 排版引擎，原生 CJK，自动书签，单遍出 TOC）
   ```bash
   # 默认风格（从 layout.md 读取）
   python3 scripts/booksmith-typst.py \
     ~/Books/[project-dir] --output [output-name].pdf

   # 强制指定版面风格
   python3 scripts/booksmith-typst.py \
     ~/Books/[project-dir] --output [output-name].pdf --style modern

   # 保存 .typ 源码用于调试
   python3 scripts/booksmith-typst.py \
     ~/Books/[project-dir] --save-typ debug.typ
   ```
   - 自动读取 `project.json` 获取书名
   - 自动合并 `manuscript/*.md`（按 ch01-chNN → appendix-a/b 排序）
   - 解析 `layout.md` 提取配色、版面风格、字号、边距作为样式源
   - 支持 4 种版面风格：classic（经典书籍）、modern（技术书默认）、academic（学术紧凑）、minimal（极简留白）
   - 支持亮色/暗色代码主题（`code_theme: light | dark`）
   - Typst 原生 CJK 混排（无需字体候选表、无 CJK 检测 hack）
   - 生成封面 + 可点击 TOC（带页码）+ PDF 书签 + 页码
   - 若 Typst 不可用，回退到 `scripts/booksmith-rl.py`（ReportLab 版）

---

# Phase 6：双 Agent 精炼

详见 `references/phase-instructions.md` — 「Phase 6 双 Agent 精炼详细指令」。

**借鉴 nuwa Phase 5 的双 Agent 精炼机制。**

**并行启动两个 Agent**：
- **Agent A（内容审查）**：技术准确性、代码可运行性、引用有效性
- **Agent B（排版审查）**：对照 layout.md 检查对齐、宽度、分页、视觉统一

主 Agent 综合两份报告，应用不冲突的改进，展示变更摘要请用户确认。

精炼标准：改动必须让书「读起来更流畅」，不只是增加内容。

---

# Phase 7：交付

## 交付动作

1. 打开生成的 PDF：`open "[项目目录]/ebook.pdf"`
2. 报告文件大小
3. 汇总关键数据

## 工作报告

详见 `references/phase-instructions.md` — 「Phase 7 交付工作报告模板」。

更新 `project.json`：`"current_phase": 7, "status": "completed"`

---

# 全局规则

详见 `references/iron-rules.md`（写作铁律、排版铁律、命名铁律、调研铁律、禁止事项、已知陷阱、诚实边界）。

## 断点续写机制

本 Skill 生成的书籍项目可能有数万字，跨多个会话才能完成。通过 `project.json` 实现断点续写：

**每次启动时**，读取 `project.json` 的 `current_phase` 和 `chapters_completed`：
- `current_phase: 0` → 从 Phase 0 开始
- `current_phase: 3, chapters_completed: ["ch01","ch02"]` → 从 ch03 继续写
- `current_phase: 4` → 直接进入质量验证
- `current_phase: 5` → 直接进入排版

**续写时的上下文恢复**：
1. 读取 `project.json` 获取全部参数
2. 读取 `outline.md` 获取大纲
3. 读取 `anchor-sample.md` 获取风格基准
4. 读取已完成的最后 2-3 章手稿（而非全部，节省 context）
5. 从断点继续

**用户触发续写**：「继续写[书名]」「接着上次的书写」

---

已知陷阱和诚实边界见 `references/iron-rules.md`。
