# Booksmith Skill

出版级技术书制作引擎 — 从深度调研到成书的一站式 Claude Code Skill。

## 核心特性

- **出版风格体系** — O'Reilly / Academic / Handbook 三种风格模板，风格锚定防漂移
- **逐章顺序写作** — 上下文累积，确保叙事连贯递进（质量优先于效率）
- **多 Agent 并行调研** — 4-5 个方向同时搜索，信源分级 + 交叉验证
- **独立质量验证** — 子 agent 审查内容质量，不自我评估
- **双 Agent 精炼** — 内容审查 + 排版审查并行，出版前最后一道关
- **AI 插图生成** — MiniMax image-01 / GLM 图像生成 / Seedream API 三选一
- **统一排版** — Typst 排版引擎，原生 CJK 混排，自动书签与目录
- **自包含项目** — 所有产物在一个目录内，可独立分发

## 流程

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

## 文件结构

```
booksmith/
├── EXTEND.md                        # 偏好系统
├── LICENSE                          # MIT License
├── README.md                        # 说明文档
├── SKILL.md                         # 主流程（Phase 0–7 + 1.5 检查点）
├── layout.md                        # 排版规范（配色、字体、间距、页码）
├── illustration.md                  # 插图规范（生图工具、风格模板、压缩）
└── references/
    ├── style-guide.md               # 出版风格（O'Reilly/Academic/Handbook）
    ├── phase-instructions.md        # 各 Phase 详细执行指令和 Agent 模板
    ├── examples.md                  # 关键 Phase 的 Input/Output 示例
    └── extend-schema.md             # 偏好系统 JSON Schema 完整定义
```

## 安装

将整个目录放入 Claude Code 的 Skill 目录：

```
~/.claude/skills/booksmith/
├── SKILL.md
├── layout.md
├── illustration.md
├── EXTEND.md
└── references/
    ├── style-guide.md
    ├── phase-instructions.md
    ├── examples.md
    └── extend-schema.md
```

> 直接将整个项目目录复制到 `~/.claude/skills/` 即可，无需挑选文件。

## 使用

在 Claude Code 中说：

```
帮我写一本关于 [主题] 的技术书
```

或更具体：

```
帮我写一本关于 [主题] 的技术书，O'Reilly 风格，加插图，末尾加公众号 [名称]
```

## 插图工具要求（可选）

如果需要 AI 生成插图，需配置以下工具之一：

| 工具 | 前置条件 |
|------|---------|
| MiniMax image-01（默认） | `MINIMAX_API_KEY` |
| GLM 图像生成 | `BIGMODEL_API_KEY` |
| Seedream API | `ARK_API_KEY` |

## 设计灵感

本 Skill 的设计汲取了以下优秀实践：

| 来源 | 借鉴的设计 |
|------|----------|
| [nuwa-skill](https://github.com/alchaincyf/nuwa-skill) | 阶段间 Review 检查点、独立质量验证（子 agent 审查非自我评估）、双 Agent 精炼、自包含项目目录 |
| [darwin-skill](https://github.com/alchaincyf/darwin-skill) | 棘轮思维（质量不达标则迭代，上限 2 次，不无限打磨） |

## 安全说明

本 Skill 涉及外部调用时的数据处理原则：

| 操作 | 数据发送范围 | 说明 |
|------|------------|------|
| PDF 生成（Typst） | 仅本地 | Typst 在本地编译 PDF，不上传任何数据 |
| 插图生成（MiniMax/GLM/Seedream API） | 仅 prompt | 只发送图像描述文本，不发送用户内容或书稿 |
| 调研 Agent 搜索 | 仅搜索词 | WebSearch 只发送搜索 query，不发送文件内容 |

**不请求、不存储、不发送**：
- 用户的 credentials、tokens、API keys（由用户本地配置）
- `~/.ssh`、`~/.aws` 等敏感目录
- 书稿完整文本内容

**Typst 编译安全注意**：
- PDF 编译在本地完成，路径固定为 `~/Books/[english-slug]/`
- Typst 不执行外部脚本，不访问网络
- 字体从系统目录读取，不加载远程资源

## License

MIT
