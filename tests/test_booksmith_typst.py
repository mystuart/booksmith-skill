#!/usr/bin/env python3
"""Tests for booksmith-typst.py — Markdown→Typst conversion and layout parsing.

Run: python3 -m pytest tests/test_booksmith_typst.py -v
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts/ to path — must use importlib because filename has hyphen
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
_module_path = SCRIPTS_DIR / "booksmith-typst.py"
_spec = importlib.util.spec_from_file_location("booksmith_typst", _module_path)
booksmith = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(booksmith)
sys.modules["booksmith_typst"] = booksmith

# Now import from the loaded module
_escape_typst = booksmith._escape_typst
_extract_title = booksmith._extract_title
_parse_code_theme = booksmith._parse_code_theme
_parse_style_preset = booksmith._parse_style_preset
_parse_yaml_layout = booksmith._parse_yaml_layout
_STYLE_PRESETS = booksmith._STYLE_PRESETS
_to_chinese_num = booksmith._to_chinese_num
convert_md_to_typst = booksmith.convert_md_to_typst
generate_typst = booksmith.generate_typst
parse_layout = booksmith.parse_layout
LayoutConfig = booksmith.LayoutConfig
StylePreset = booksmith.StylePreset
_DEFAULT_COLORS = booksmith._DEFAULT_COLORS


# ═══════════════════════════════════════════════════════════════
# Section 1: Style Presets Consistency
# ═══════════════════════════════════════════════════════════════


class TestStylePresets:
    """Verify _STYLE_PRESETS values are internally consistent and complete."""

    def test_all_four_styles_exist(self):
        expected = {"classic", "modern", "academic", "minimal"}
        assert set(_STYLE_PRESETS.keys()) == expected

    def test_modern_defaults(self):
        """modern is the default style — verify its key values."""
        m = _STYLE_PRESETS["modern"]
        assert m.name == "modern"
        assert m.leading == 1.7
        assert m.paragraph_spacing == 1.0
        assert m.h3_below == 0.6
        assert m.list_spacing == 0.7
        assert m.first_line_indent == "0em"
        assert m.justify is True

    def test_classic_defaults(self):
        c = _STYLE_PRESETS["classic"]
        assert c.leading == 1.8
        assert c.paragraph_spacing == 1.2
        assert c.h2_below == 1.0
        assert c.h3_below == 0.8
        assert c.list_spacing == 0.6
        assert c.first_line_indent == "2em"

    def test_academic_defaults(self):
        a = _STYLE_PRESETS["academic"]
        assert a.body_size == 10.5
        assert a.leading == 1.6
        assert a.paragraph_spacing == 0.8
        assert a.h3_below == 0.5
        assert a.list_spacing == 0.5

    def test_minimal_defaults(self):
        m = _STYLE_PRESETS["minimal"]
        assert m.leading == 1.9
        assert m.paragraph_spacing == 1.5
        assert m.h3_below == 0.6
        assert m.list_spacing == 0.6
        assert m.justify is False

    def test_heading_hierarchy(self):
        """h3_below must be <= h2_below for all styles."""
        for name, preset in _STYLE_PRESETS.items():
            assert preset.h3_below <= preset.h2_below, (
                f"{name}: h3_below ({preset.h3_below}) > h2_below ({preset.h2_below})"
            )

    def test_list_spacing_less_than_paragraph(self):
        """list_spacing < paragraph_spacing for all styles."""
        for name, preset in _STYLE_PRESETS.items():
            assert preset.list_spacing < preset.paragraph_spacing, (
                f"{name}: list_spacing ({preset.list_spacing}) >= "
                f"paragraph_spacing ({preset.paragraph_spacing})"
            )


# ═══════════════════════════════════════════════════════════════
# Section 2: Layout YAML Parsing
# ═══════════════════════════════════════════════════════════════


class TestYamlLayoutParsing:
    """Test _parse_yaml_layout() reads from the YAML code block."""

    def test_parse_full_yaml_block(self):
        text = '''
```yaml
booksmith_layout:
  layout_style: classic
  code_theme: dark

  margins:
    top: 25
    right: 22
    bottom: 30
    left: 22
```
'''
        preset = _parse_yaml_layout(text)
        assert preset is not None
        # Should return classic preset (from layout_style)
        assert preset.name == "classic"
        # Margins should be overridden
        assert preset.page_margin_top == 25.0
        assert preset.page_margin_right == 22.0
        assert preset.page_margin_bottom == 30.0
        assert preset.page_margin_left == 22.0

    def test_parse_code_theme_from_yaml(self):
        text = """
```yaml
booksmith_layout:
  layout_style: modern
  code_theme: dark
```
"""
        theme = _parse_code_theme(text)
        assert theme == "dark"

    def test_no_yaml_block_returns_none(self):
        text = "Some natural language text with no YAML block."
        assert _parse_yaml_layout(text) is None

    def test_partial_yaml_block_only_leading(self):
        text = """
```yaml
booksmith_layout:
  layout_style: modern
```
"""
        preset = _parse_yaml_layout(text)
        assert preset is not None
        assert preset.name == "modern"
        # h3_below should remain default
        assert preset.h3_below == 0.6


class TestLegacyLayoutParsing:
    """Fallback: legacy regex-based parsing for old layout.md files."""

    def test_parse_legacy_leading(self):
        text = "正文行高：1.75"
        preset = _parse_style_preset(text, {})
        assert preset.leading == 1.75

    def test_parse_legacy_margins_cm(self):
        text = "margin: 2.5cm 2.2cm 2.5cm 2.2cm"
        preset = _parse_style_preset(text, {})
        assert preset.page_margin_top == 25.0
        assert preset.page_margin_right == 22.0
        assert preset.page_margin_bottom == 25.0
        assert preset.page_margin_left == 22.0

    def test_parse_legacy_style(self):
        text = "layout_style: academic"
        preset = _parse_style_preset(text, {})
        assert preset.name == "academic"

    def test_yaml_takes_precedence_over_legacy(self):
        """When both YAML and legacy patterns exist, YAML should win."""
        text = """
```yaml
booksmith_layout:
  layout_style: classic
```
正文行高：1.5
"""
        preset = _parse_style_preset(text, {})
        # YAML says classic
        assert preset.name == "classic"


# ═══════════════════════════════════════════════════════════════
# Section 3: Markdown → Typst Conversion
# ═══════════════════════════════════════════════════════════════


class TestToChineseNum:
    def test_single_digit(self):
        assert _to_chinese_num(1) == "一"
        assert _to_chinese_num(5) == "五"
        assert _to_chinese_num(9) == "九"

    def test_teens(self):
        assert _to_chinese_num(10) == "十"
        assert _to_chinese_num(11) == "十一"
        assert _to_chinese_num(19) == "十九"

    def test_twenties(self):
        assert _to_chinese_num(20) == "二十"
        assert _to_chinese_num(21) == "二十一"


class TestExtractTitle:
    def test_section_prefix(self):
        assert _extract_title("§01 引言") == "第一章 引言"
        assert _extract_title("§05 等待事件") == "第五章 等待事件"
        assert _extract_title("§10 工具链") == "第十章 工具链"

    def test_quoted_title(self):
        assert _extract_title('"Slow SQL"') == "Slow SQL"

    def test_chapter_prefix(self):
        assert _extract_title("Chapter 3 — Performance") == "Performance"


class TestEscapeTypst:
    def test_special_chars(self):
        assert _escape_typst("hello # world") == "hello \\# world"
        assert _escape_typst("a [b] c") == "a \\[b\\] c"
        assert _escape_typst("$50") == "\\$50"

    def test_backslash(self):
        assert _escape_typst("a\\b") == "a\\\\b"


class TestConvertMdToTypst:
    """Integration tests for the full Markdown → Typst converter."""

    def test_h1_chapter(self):
        md = "# §01 引言\n\n这是正文。"
        result = convert_md_to_typst(md)
        assert "第一章 引言" in result
        assert "#pagebreak()" in result

    def test_h2_section(self):
        md = "## 小节标题\n\n正文。"
        result = convert_md_to_typst(md)
        assert "== 小节标题" in result

    def test_h3_subsection(self):
        md = "### 子节标题"
        result = convert_md_to_typst(md)
        assert "=== 子节标题" in result

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = convert_md_to_typst(md)
        assert "```python" in result
        assert "print('hello')" in result

    def test_nested_fence_code_block(self):
        """Code block containing ``` on its own line should use 4-backtick output."""
        md = '~~~markdown\n# Title\n```\ncode snippet\n```\n~~~'
        result = convert_md_to_typst(md)
        # Should use 4-backtick fence for Typst raw block
        assert "````" in result

    def test_tilde_fence(self):
        """~~~ fence should be recognized as code block delimiter."""
        md = "~~~yaml\nkey: value\n~~~"
        result = convert_md_to_typst(md)
        # Content should be preserved as code
        assert "key: value" in result

    def test_blockquote(self):
        md = "> 这是一段引用。"
        result = convert_md_to_typst(md)
        assert "> 这是一段引用。" in result

    def test_bullet_list(self):
        md = "- 第一项\n- 第二项"
        result = convert_md_to_typst(md)
        assert "- 第一项" in result
        assert "- 第二项" in result

    def test_numbered_list(self):
        md = "1. 第一步\n2. 第二步"
        result = convert_md_to_typst(md)
        assert "+ 第一步" in result
        assert "+ 第二步" in result

    def test_horizontal_rule(self):
        md = "---"
        result = convert_md_to_typst(md)
        assert "#line(" in result

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = convert_md_to_typst(md)
        assert "#table(" in result
        assert "columns: (auto, auto)" in result

    def test_image(self):
        md = "![封面](illustrations/cover.jpg){.banner}"
        result = convert_md_to_typst(md)
        assert 'image("illustrations/cover.jpg"' in result
        assert "width: 100%" in result  # .banner → 100%

    def test_image_non_banner(self):
        md = "![图表](illustrations/chart.png)"
        result = convert_md_to_typst(md)
        assert 'width: 80%' in result

    def test_bold_italic(self):
        md = "**加粗文本** 和 *斜体文本*"
        result = convert_md_to_typst(md)
        assert "*加粗文本*" in result
        assert "_斜体文本_" in result

    def test_link(self):
        md = "查看 [文档](https://example.com)"
        result = convert_md_to_typst(md)
        assert '#link("https://example.com")' in result

    def test_skip_manuscript_header(self):
        """Lines starting with manuscript/ or chNN should be skipped as file headers."""
        md = "# manuscript/ch01.md\n\n# §01 真实标题"
        result = convert_md_to_typst(md)
        assert "真实标题" in result
        assert "manuscript" not in result

    def test_cjk_paragraph_merge(self):
        """Consecutive CJK lines should merge without extra space."""
        md = "这是第一行\n这是第二行"
        result = convert_md_to_typst(md)
        # CJK lines should be joined directly (no space between)
        assert "这是第一行这是第二行" in result

    def test_inline_code(self):
        md = "使用 `print()` 函数"
        result = convert_md_to_typst(md)
        assert "`print()`" in result


# ═══════════════════════════════════════════════════════════════
# Section 4: Typst Generation
# ═══════════════════════════════════════════════════════════════


class TestGenerateTypst:
    """Test the complete .typ file generation."""

    def _make_layout(self, style_name="modern"):
        return LayoutConfig(
            colors=dict(_DEFAULT_COLORS),
            style=_STYLE_PRESETS[style_name],
        )

    def test_cover_page(self):
        config = {"title": "测试书", "subtitle": "副标题", "author": "作者"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "正文内容")
        assert "测试书" in result
        assert "副标题" in result
        assert "作者" in result
        assert "#page(numbering: none)" in result  # cover has no page number

    def test_toc_present(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        assert "#outline(" in result
        assert "目 录" in result

    def test_code_block_styling(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        assert 'raw.where(block: true)' in result
        assert "breakable: true" in result

    def test_quote_styling(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        assert "#show quote:" in result
        assert "breakable: true" in result

    def test_list_spacing(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        assert "set list(spacing:" in result

    def test_dark_code_theme(self):
        config = {"title": "Book"}
        layout = LayoutConfig(
            colors=dict(_DEFAULT_COLORS),
            style=_STYLE_PRESETS["modern"],
            code_theme="dark",
        )
        result = generate_typst(config, layout, "")
        # Should use dark code background (lowercase hex in output)
        assert "#1e1e2e" in result

    def test_heading_spacing_levels(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        # Should have rules for all heading levels
        assert 'heading.where(level: 1)' in result
        assert 'heading.where(level: 2)' in result
        assert 'heading.where(level: 3)' in result
        assert 'heading.where(level: 4)' in result  # H4 should exist for modern

    def test_page_setup(self):
        config = {"title": "Book"}
        layout = self._make_layout()
        result = generate_typst(config, layout, "")
        assert 'paper: "a4"' in result
        assert "margin:" in result


# ═══════════════════════════════════════════════════════════════
# Section 5: Integration — Parse layout.md + generate
# ═══════════════════════════════════════════════════════════════


class TestLayoutIntegration:
    """End-to-end: parse the actual layout.md file and verify."""

    def test_parse_skill_layout_md(self):
        """Parse the skill's own layout.md — should find the YAML block."""
        layout_path = SCRIPTS_DIR.parent / "layout.md"
        if not layout_path.exists():
            pytest.skip("layout.md not found")

        layout = parse_layout(layout_path)
        # Should find the YAML block and extract style
        assert layout.style is not None
        assert layout.style.name == "modern"  # default from layout.md

    def test_generate_pdf_with_skill_layout(self):
        """Generate a minimal .typ using the skill's layout.md."""
        layout_path = SCRIPTS_DIR.parent / "layout.md"
        if not layout_path.exists():
            pytest.skip("layout.md not found")

        layout = parse_layout(layout_path)
        config = {"title": "Test Book", "subtitle": "", "author": ""}
        # First convert the markdown body to Typst, then generate
        body = convert_md_to_typst("# §01 测试\n\n这是测试正文。")
        result = generate_typst(config, layout, body)
        # Should be a valid Typst document
        assert "#set document(" in result
        assert "#set page(" in result
        assert "#set text(" in result
        assert "第一章 测试" in result


# ═══════════════════════════════════════════════════════════════
# Section 6: CLI Entry Point Validation
# ═══════════════════════════════════════════════════════════════


class TestCliValidation:
    """Test that the CLI properly validates inputs and exits cleanly."""

    def test_missing_project_dir(self):
        """Should exit with error when project.json is missing."""
        main = booksmith.main
        sys.argv = ["booksmith-typst.py", "/tmp/nonexistent-booksmith-xyz"]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_empty_manuscript_dir(self):
        """Should exit with error when manuscript/ has no .md files."""
        main = booksmith.main
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Create project.json
            (tmp / "project.json").write_text(json.dumps({
                "title": "Test", "target_reader": "有基础", "style": "oreilly",
                "chapters_planned": 1, "has_illustrations": False,
                "status": "initialized", "current_phase": 5,
                "chapters_completed": [],
            }))
            # Create empty manuscript dir
            (tmp / "manuscript").mkdir()
            sys.argv = ["booksmith-typst.py", str(tmp)]
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
