# Booksmith Extend — 偏好 Schema

本文件定义 `~/.hermes/booksmith-preferences.json` 的完整 JSON Schema。

---

## 完整 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {

    "preferred_style": {
      "type": "string",
      "enum": ["oreilly", "academic", "handbook", "custom"],
      "description": "默认出版风格"
    },

    "target_reader_default": {
      "type": "string",
      "enum": ["小白", "有基础", "专业人士"],
      "description": "默认目标读者"
    },

    "illustration_default": {
      "type": "boolean",
      "description": "默认是否需要插图"
    },

    "preferred_chapter_length": {
      "type": "string",
      "enum": ["short", "medium", "long"],
      "description": "单章偏好长度：short(2000-3000字) / medium(3000-5000字) / long(5000+字)"
    },

    "brand": {
      "type": "object",
      "properties": {
        "name":           { "type": "string", "description": "个人/品牌名称" },
        "cta":            { "type": "string", "description": "末尾引导语，如「欢迎关注我的公众号 XXX」" },
        "wechat":         { "type": "string", "description": "公众号 ID 或二维码图片路径" },
        "weibo":          { "type": "string", "description": "微博 ID" },
        "website":        { "type": "string", "description": "个人网站 URL" }
      },
      "additionalProperties": false
    },

    "layout_preferences": {
      "type": "object",
      "properties": {
        "font_scale":        { "type": "number",  "default": 1.0,  "description": "正文字号缩放系数" },
        "chapter_gap":       { "type": "string",  "enum": ["compact", "medium", "spacious"], "default": "medium" },
        "code_theme":        { "type": "string",  "default": "github-light", "description": "代码高亮主题" },
        "tip_style":         { "type": "string",  "enum": ["bordered", "filled", "icon"], "default": "bordered" },
        "color_scheme":      { "type": "string",  "description": "自定义配色方案名" },
        "page_margin":        { "type": "string",  "description": "自定义页边距，如 '2cm'" },
        "custom_css":         { "type": "string",  "description": "追加在 layout.md CSS 之后的自定义 CSS" }
      },
      "additionalProperties": false
    },

    "writing_patterns": {
      "type": "object",
      "properties": {
        "analogy_density":    { "type": "string",  "enum": ["low", "medium", "high"], "default": "high" },
        "code_ratio":        { "type": "number",  "minimum": 0, "maximum": 1, "default": 0.2 },
        "scene_intro":       { "type": "boolean", "default": true, "description": "是否每章都以场景/故事开头" },
        "chapter_summary":   { "type": "boolean", "default": false, "description": "是否在章末写小结" },
        "cross_ref_style":   { "type": "string",  "enum": ["chapter", "figure", "table", "none"], "default": "chapter" },
        "preferred_tone":     { "type": "string",  "enum": ["conversational", "semi-formal", "formal"], "default": "conversational" }
      },
      "additionalProperties": false
    },

    "refinement_tendencies": {
      "type": "object",
      "description": "精炼阶段持续体现的偏好方向",
      "properties": {
        "prefer_concision":   { "type": "boolean", "default": true },
        "prefer_depth":       { "type": "boolean", "default": false },
        "prefer_readability": { "type": "boolean", "default": true },
        "trim_redundancy":    { "type": "boolean", "default": true },
        "strengthen_logic":   { "type": "boolean", "default": false }
      },
      "additionalProperties": false
    },

    "preferred_image_style": {
      "type": "object",
      "properties": {
        "palette":   { "type": "string", "description": "插图主色调，如 'purple-blue'" },
        "ratio":     { "type": "string", "description": "默认插图比例，如 '3:2'" },
        "modifiers": { "type": "array", "items": { "type": "string" }, "description": "偏好修饰词，如 ['kawaii', 'minimal']" },
        "tools":     { "type": "array", "items": { "type": "string" }, "description": "偏好工具，['minimax', 'glm', 'seedream']" }
      },
      "additionalProperties": false
    },

    "exclude_from_preferences": {
      "type": "array",
      "items": { "type": "string" },
      "description": "排除字段数组。如 ['brand', 'preferred_style'] — 这些字段不会被自动积累写入"
    },

    "books_history": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "slug":        { "type": "string" },
          "title":       { "type": "string" },
          "style":       { "type": "string" },
          "chapters":    { "type": "integer" },
          "word_count":  { "type": "integer" },
          "completed":   { "type": "string", "format": "date" },
          "quality_notes": { "type": "string" }
        }
      },
      "description": "历史书籍记录，用于分析长期偏好趋势"
    },

    "last_updated": {
      "type": "string",
      "format": "date",
      "description": "最后更新时间，ISO 8601"
    }

  },
  "additionalProperties": false
}
```

---

## 字段优先级

```
用户 project.json  ← 最高优先级（项目级覆盖）
    ↓
~/.hermes/booksmith-preferences.json  ← 中间优先级（偏好积累）
    ↓
SKILL.md 硬编码默认值  ← 最低优先级（兜底）
```

---

## 写入校验规则

写入前必须校验：

| 字段 | 校验规则 |
|------|---------|
| `brand` | 涉及用户个人信息，写入前必须展示给用户确认 |
| `preferred_style` | 必须是有效枚举值，否则拒绝写入 |
| `layout_preferences.custom_css` | 不允许 `@page` 规则（PDF 分页在 layout.md 中统一控制） |
| `exclude_from_preferences` | 只允许包含顶级字段名（不含嵌套路径） |
| `books_history` | 最多保留 20 条记录，超出时删除最早的 |

---

## JSON Schema 版本声明

当前版本：`draft-07`（JSON Schema 标准的成熟版本，广泛工具支持）。

如需严格验证，可使用 Python `jsonschema` 库：

```python
import json, jsonschema

with open("references/extend-schema.md") as f:
    schema = json.loads(f.read().split("```json")[1].split("```")[0])

# 验证偏好文件
with open(os.path.expanduser("~/.hermes/booksmith-preferences.json")) as f:
    prefs = json.load(f)
    jsonschema.validate(prefs, schema)
```

（`references/extend-schema.md` 中嵌入 JSON Schema 的方式：在 ` ```json ` 代码块中放完整 schema，读取时解析该代码块即可。）
