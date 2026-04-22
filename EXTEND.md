---
name: booksmith-extend
version: 1.0.0
description: |
  Booksmith 偏好系统 — 在 project.json 之外建立用户级偏好记忆，
  使书籍制作越来越贴合用户的写作风格和个人品牌，而非每次重置。
---

# Booksmith Extend — 用户偏好系统

> ⚠️ Intended design — not yet integrated into SKILL.md execution flow.
> 每本书都在学习你。下次写书，应该更快、更像你。

## 核心概念

Booksmith 在两个层面存储信息：

| 层面 | 存储位置 | 内容 | 生命周期 |
|------|---------|------|---------|
| **项目层** | `~/Books/[slug]/project.json` | 单本书的参数（风格、篇幅、读者） | 随书存在 |
| **用户偏好层** | `~/.claude/booksmith-preferences.json` | 跨项目的个人写作偏好 | 永久积累 |

偏好层会让 Booksmith 一次比一次更懂你——你的常用风格、你的排版偏好、你的品牌信息。

## 偏好数据

详见 `references/extend-schema.md` — 完整字段定义和类型。

### 读取时机

每次 Phase 0 启动时：

```
1. 读取 ~/.claude/booksmith-preferences.json
2. 读取 ~/Books/[slug]/project.json
3. project.json 覆盖 preferences.json（即项目级参数优先）
4. 未在 project.json 中指定的项 → 回退到 preferences.json 的值
```

### 写入时机

**自动积累**（无需用户确认）：

| 时机 | 写入内容 |
|------|---------|
| Phase 2 完成 | 风格锚定结果 → `preferred_style` |
| Phase 3 章节写作 | 章节字数、节奏偏好 → `writing_patterns` |
| Phase 5 完成 | 排版参数（字体、配色）→ `layout_preferences` |
| Phase 6 完成 | 精炼采纳的修改方向 → `refinement_tendencies` |

**用户主动更新**（任何时候）：

用户说「以后的书都这样排版」「记住我这个风格偏好」→ 立即更新 `~/.claude/booksmith-preferences.json`。

### 偏好字段一览

```json
{
  "preferred_style": "oreilly | academic | handbook | custom",
  "target_reader_default": "小白 | 有基础 | 专业人士",
  "preferred_chapter_length": "short | medium | long  // 影响 project.json 的 chapters_planned：short→8-10章，medium→10-12章，long→15+章",
  "illustration_default": true | false,
  "brand": { "name": "...", "cta": "...", "wechat": "..." },
  "layout_preferences": { "font_scale": 1.0, "chapter_gap": "medium", ... },
  "writing_patterns": { "analogy_density": "high", "code_ratio": 0.2, ... },
  "refinement_tendencies": { "prefer_concision": true, "prefer_depth": false, ... },
  "preferred_image_style": { "palette": "purple-blue", "ratio": "3:2", ... },
  "exclude_from_preferences": [],
  "last_updated": "YYYY-MM-DD"
}
```

详见 `references/extend-schema.md` 的完整 schema 定义。

## 偏好应用规则

### 规则一：项目覆盖偏好

`project.json` 中的任何字段都会覆盖 preferences.json 的对应值。用户在一个项目中说「这本用 Academic 风格」不会改变默认偏好。

### 规则二：用户可声明例外

用户说「这本例外，用 Academic」→ 这次 project.json 记 Academic，后续新书仍用原偏好。

### 规则三：敏感字段需确认

`brand`（品牌信息）涉及对外展示，写入前必须展示给用户确认：

```
检测到品牌信息变更：
  名称：XXX
  引导语：XXX
  公众号：XXX
  → 确认写入个人偏好？[确认/修改/跳过]
```

### 规则四：排除字段

`exclude_from_preferences` 数组中的字段不会被自动积累。
例如用户说「这本不要记住」→ 把这本的特殊选择加入排除列表。

## 偏好查看 & 修改

用户可以随时：

- 「查看我的书籍偏好」→ 读取并展示 `~/.claude/booksmith-preferences.json`
- 「修改偏好设置」→ 展示当前值 → 用户修改 → 写入文件
- 「清除偏好」→ 重置为默认状态（保留空文件，仅含默认字段）

## 与其他 Skill 的协作

### 与格式化工具

偏好系统通过 `layout_preferences` 提供格式默认值。
Phase 5 格式优先检查时，优先使用用户偏好的格式参数而非硬编码默认值。

### 与插图工具

插图偏好（`preferred_image_style`）在插图规划阶段作为默认参数。
用户风格偏好变化时（通过 Phase 5 锚定确认），同步更新 `preferred_image_style`。

## 文件位置

```
~/.claude/booksmith-preferences.json   ← 用户偏好（gitignored）
```

> 注意：偏好文件不应提交到 Git，应在 `~/.gitignore` 中排除：
> ```
> # Booksmith user preferences
> .claude/booksmith-preferences.json
> ```
