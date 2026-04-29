#!/usr/bin/env python3
"""booksmith-typst.py — Generate book PDF using Typst typesetting engine.

Reads layout.md for styling, project.json for metadata, manuscript/*.md for content.
Outputs a PDF with cover page, clickable TOC, bookmarks, and CJK-native typesetting.

v2.0 — 大幅改进排版引擎：
- 4 种可配置版面风格（classic/modern/academic/minimal）
- 修复代码块转义问题，原生语法高亮
- 重新设计间距系统（行距/段距/heading间距/列表间距）
- 美化次级标题、引用块、代码块样式
- 图片路径通过 root 参数正确解析

Usage:
    python3 booksmith-typst.py ~/Books/project-dir --output ebook.pdf
"""

import argparse
import json
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import typst

_SKILL_DIR = Path(__file__).resolve().parent.parent
_LAYOUT_PATH = _SKILL_DIR / "layout.md"


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Style Presets
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StylePreset:
    """A layout style preset with complete typographic parameters."""
    name: str
    body_font: str
    heading_font: str
    code_font: str
    body_size: float
    chapter_size: float
    section_size: float
    subsection_size: float
    cover_title_size: float
    leading: float          # 行内行距（line height within paragraph）
    paragraph_spacing: float  # 段落间距（between paragraphs）
    first_line_indent: str   # "2em" | "0em" | "1.5em"
    justify: bool
    h1_above: float
    h1_below: float
    h2_above: float
    h2_below: float
    h3_above: float
    h3_below: float
    list_spacing: float
    code_inset: float
    code_radius: float
    quote_left_border: bool
    quote_background: bool
    page_margin_top: float
    page_margin_right: float
    page_margin_bottom: float
    page_margin_left: float


_STYLE_PRESETS: dict[str, StylePreset] = {
    "classic": StylePreset(
        name="classic",
        body_font="Noto Serif SC",
        heading_font="Noto Serif SC",
        code_font="JetBrains Mono",
        body_size=11.0,
        chapter_size=20.0,
        section_size=14.0,
        subsection_size=12.0,
        cover_title_size=32.0,
        leading=1.8,
        paragraph_spacing=1.2,
        first_line_indent="2em",
        justify=True,
        h1_above=2.0,
        h1_below=1.2,
        h2_above=1.5,
        h2_below=1.0,
        h3_above=1.2,
        h3_below=0.8,
        list_spacing=0.6,
        code_inset=10.0,
        code_radius=4.0,
        quote_left_border=True,
        quote_background=True,
        page_margin_top=22.0,
        page_margin_right=20.0,
        page_margin_bottom=28.0,
        page_margin_left=20.0,
    ),
    "modern": StylePreset(
        name="modern",
        body_font="Noto Sans SC",
        heading_font="Noto Serif SC",
        code_font="JetBrains Mono",
        body_size=11.0,
        chapter_size=20.0,
        section_size=14.0,
        subsection_size=12.0,
        cover_title_size=32.0,
        leading=1.7,
        paragraph_spacing=1.0,
        first_line_indent="0em",
        justify=True,
        h1_above=2.0,
        h1_below=1.2,
        h2_above=1.5,
        h2_below=1.0,
        h3_above=1.2,
        h3_below=0.8,
        list_spacing=0.7,
        code_inset=10.0,
        code_radius=4.0,
        quote_left_border=True,
        quote_background=True,
        page_margin_top=22.0,
        page_margin_right=20.0,
        page_margin_bottom=28.0,
        page_margin_left=20.0,
    ),
    "academic": StylePreset(
        name="academic",
        body_font="Noto Serif SC",
        heading_font="Noto Serif SC",
        code_font="JetBrains Mono",
        body_size=10.5,
        chapter_size=18.0,
        section_size=13.0,
        subsection_size=11.0,
        cover_title_size=28.0,
        leading=1.6,
        paragraph_spacing=0.8,
        first_line_indent="1.5em",
        justify=True,
        h1_above=1.8,
        h1_below=1.0,
        h2_above=1.2,
        h2_below=0.8,
        h3_above=1.0,
        h3_below=0.6,
        list_spacing=0.5,
        code_inset=8.0,
        code_radius=2.0,
        quote_left_border=True,
        quote_background=False,
        page_margin_top=25.0,
        page_margin_right=25.0,
        page_margin_bottom=25.0,
        page_margin_left=25.0,
    ),
    "minimal": StylePreset(
        name="minimal",
        body_font="Noto Sans SC",
        heading_font="Noto Sans SC",
        code_font="JetBrains Mono",
        body_size=11.0,
        chapter_size=22.0,
        section_size=15.0,
        subsection_size=12.5,
        cover_title_size=34.0,
        leading=1.9,
        paragraph_spacing=1.5,
        first_line_indent="0em",
        justify=False,
        h1_above=2.5,
        h1_below=1.5,
        h2_above=1.8,
        h2_below=1.0,
        h3_above=1.5,
        h3_below=0.8,
        list_spacing=0.6,
        code_inset=12.0,
        code_radius=6.0,
        quote_left_border=False,
        quote_background=True,
        page_margin_top=25.0,
        page_margin_right=25.0,
        page_margin_bottom=30.0,
        page_margin_left=25.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Layout Parser
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LayoutConfig:
    colors: dict = field(default_factory=dict)
    style: StylePreset = field(default_factory=lambda: _STYLE_PRESETS["modern"])
    code_theme: str = "light"  # light | dark


_DEFAULT_COLORS = {
    "indigo": "#312E81",
    "indigo-light": "#4338CA",
    "amber": "#D97706",
    "text": "#2D2D2D",
    "gray": "#6B7280",
    "code-bg": "#F5F5F5",
    "code-bg-dark": "#1E1E2E",
    "code-text-dark": "#D9E0EE",
    "tip-bg": "#EEF2FF",
    "tip-border": "#C7D2FE",
    "quote-bg": "#F8F9FA",
    "quote-border": "#4338CA",
    "table-header-bg": "#312E81",
    "table-alt-bg": "#F9F8F5",
    "table-border": "#DDD8C8",
    "link": "#4338CA",
}


def parse_layout(path: Path) -> LayoutConfig:
    """Parse layout.md to extract styling parameters and style preset."""
    if not path.exists():
        print(
            f"\n[WARNING] layout.md not found at {path}\n"
            f"  Expected: {path}\n"
            f"  Using default layout parameters (modern style, default colors).\n"
            f"  To customize, create layout.md with styling parameters.\n",
            file=sys.stderr,
        )
        return LayoutConfig(colors=dict(_DEFAULT_COLORS))

    text = path.read_text(encoding="utf-8")
    colors = _parse_css_vars(text)
    style = _parse_style_preset(text, colors)
    code_theme = _parse_code_theme(text)

    return LayoutConfig(
        colors=colors,
        style=style,
        code_theme=code_theme,
    )


def _parse_css_vars(text: str) -> dict:
    colors = dict(_DEFAULT_COLORS)

    # === New format: YAML code block with semantic names ===
    # Match ```yaml blocks containing "colors:" definitions
    yaml_blocks = re.findall(r"```ya?ml\n(.*?)```", text, re.DOTALL)
    for block in yaml_blocks:
        # Look for colors: section
        in_colors = False
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("colors:"):
                in_colors = True
                continue
            if in_colors:
                # Match "  primary: \"#312E81\"  # comment"
                m = re.match(r"([\w-]+):\s*\"(#[0-9A-Fa-f]{6})\"", stripped)
                if m:
                    name = m.group(1)
                    hex_val = m.group(2).lower()
                    # Map semantic names to internal color keys
                    _SEMANTIC_MAP = {
                        "primary": "indigo",
                        "secondary": "indigo-light",
                        "accent": "amber",
                        "text": "text",
                        "muted": "gray",
                        "code-bg": "code-bg",
                        "tip-bg": "tip-bg",
                        "tip-border": "tip-border",
                    }
                    key = _SEMANTIC_MAP.get(name, name)
                    colors[key] = hex_val
                # Exit colors section if line is not indented (new top-level key)
                elif stripped and not line.startswith(" ") and not line.startswith("\t"):
                    in_colors = False

    # === Legacy format: CSS code block with --varname ===
    css_blocks = re.findall(r"```css\n(.*?)```", text, re.DOTALL)
    for block in css_blocks:
        for m in re.finditer(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block):
            colors[m.group(1)] = m.group(2).lower()

    return colors


def _parse_style_preset(text: str, colors: dict) -> StylePreset:
    """Extract layout style preset from layout.md."""
    # Look for layout_style: xxx in YAML-like blocks
    style_match = re.search(r"layout_style[:\s]+(\w+)", text, re.I)
    style_name = style_match.group(1).lower() if style_match else "modern"

    if style_name not in _STYLE_PRESETS:
        print(f"Warning: Unknown style '{style_name}', using 'modern'", file=sys.stderr)
        style_name = "modern"

    preset = _STYLE_PRESETS[style_name]

    # Allow layout.md to override individual parameters
    # Parse margin overrides
    margin_m = re.search(
        r"margin:\s*([\d.]+)cm\s*([\d.]+)cm\s*([\d.]+)cm\s*([\d.]+)cm", text
    )
    if margin_m:
        margins = tuple(float(x) * 10 for x in margin_m.groups())
        preset = _override_preset(preset, {
            "page_margin_top": margins[0],
            "page_margin_right": margins[1],
            "page_margin_bottom": margins[2],
            "page_margin_left": margins[3],
        })

    # Parse body size override
    pt_match = re.search(r"正文.*?(\d+(?:\.\d+)?)\s*pt", text)
    if pt_match:
        preset = _override_preset(preset, {"body_size": float(pt_match.group(1))})

    # Parse leading override
    leading_m = re.search(r"正文行高[：:]\s*([\d.]+)", text)
    if leading_m:
        preset = _override_preset(preset, {"leading": float(leading_m.group(1))})

    # Parse heading spacing overrides
    # H1
    h1_above_m = re.search(r"H1[\s_]?上方间距[：:]\s*([\d.]+)", text, re.I)
    if h1_above_m:
        preset = _override_preset(preset, {"h1_above": float(h1_above_m.group(1))})
    h1_below_m = re.search(r"H1[\s_]?下方间距[：:]\s*([\d.]+)", text, re.I)
    if h1_below_m:
        preset = _override_preset(preset, {"h1_below": float(h1_below_m.group(1))})

    # H2
    h2_above_m = re.search(r"H2[\s_]?上方间距[：:]\s*([\d.]+)", text, re.I)
    if h2_above_m:
        preset = _override_preset(preset, {"h2_above": float(h2_above_m.group(1))})
    h2_below_m = re.search(r"H2[\s_]?下方间距[：:]\s*([\d.]+)", text, re.I)
    if h2_below_m:
        preset = _override_preset(preset, {"h2_below": float(h2_below_m.group(1))})

    # H3
    h3_above_m = re.search(r"H3[\s_]?上方间距[：:]\s*([\d.]+)", text, re.I)
    if h3_above_m:
        preset = _override_preset(preset, {"h3_above": float(h3_above_m.group(1))})
    h3_below_m = re.search(r"H3[\s_]?下方间距[：:]\s*([\d.]+)", text, re.I)
    if h3_below_m:
        preset = _override_preset(preset, {"h3_below": float(h3_below_m.group(1))})

    # Parse list spacing override
    list_spacing_m = re.search(r"列表项间距[：:]\s*([\d.]+)", text)
    if list_spacing_m:
        preset = _override_preset(preset, {"list_spacing": float(list_spacing_m.group(1))})

    return preset


def _parse_code_theme(text: str) -> str:
    m = re.search(r"code_theme[:\s]+(\w+)", text, re.I)
    theme = m.group(1).lower() if m else "light"
    return theme if theme in ("light", "dark") else "light"


def _override_preset(preset: StylePreset, overrides: dict) -> StylePreset:
    """Create a new preset with overridden fields."""
    kwargs = {k: overrides.get(k, v) for k, v in preset.__dict__.items()}
    return StylePreset(**kwargs)


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Markdown → Typst Converter
# ═══════════════════════════════════════════════════════════════════════

def _to_chinese_num(n: int) -> str:
    """Convert 1–99 to Chinese numerals."""
    nums = "零一二三四五六七八九"
    if n < 10:
        return nums[n]
    if n < 20:
        return "十" + (nums[n % 10] if n % 10 else "")
    tens, ones = divmod(n, 10)
    return nums[tens] + "十" + (nums[ones] if ones else "")


def _extract_title(raw: str) -> str:
    """Extract clean title from booksmith heading formats."""
    # §NN prefix → 第N章
    m = re.match(r"^§(\d+)\s*", raw)
    if m:
        num = int(m.group(1))
        title = re.sub(r"^§\d+\s*", "", raw)
        return f"第{_to_chinese_num(num)}章 {title.strip()}"
    title = re.sub(r"^§\d+\s*", "", raw)
    title = re.sub(r'^"(.+)"$', r"\1", title)
    title = re.sub(r"^Chapter\s+\d+\s*[—–-]\s*", "", title)
    return title.strip()


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in [
        (0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x20000, 0x2A6DF),
        (0x2A700, 0x2B73F), (0x2B740, 0x2B81F), (0x2B820, 0x2CEAF),
        (0xF900, 0xFAFF), (0x2F800, 0x2FA1F),
        (0x3000, 0x303F), (0xFF00, 0xFFEF), (0x3040, 0x309F),
        (0x30A0, 0x30FF), (0xAC00, 0xD7AF),
    ])


def _escape_typst(text: str) -> str:
    """Escape Typst special characters in body text."""
    text = text.replace("\\", "\\\\")
    text = text.replace("#", "\\#")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("@", "\\@")
    text = text.replace("$", "\\$")
    return text


def _convert_inline(text: str) -> str:
    """Convert Markdown inline formatting to Typst."""
    result = []
    i = 0
    while i < len(text):
        # Code span: `text`
        m = re.match(r"`(.+?)`", text[i:])
        if m:
            result.append(f"`{m.group(1)}`")
            i += m.end()
            continue
        # Bold: **text**
        m = re.match(r"\*\*(.+?)\*\*", text[i:])
        if m:
            result.append(f"*{_escape_typst(m.group(1))}*")
            i += m.end()
            continue
        # Italic: *text*
        m = re.match(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", text[i:])
        if m:
            result.append(f"_{_escape_typst(m.group(1))}_")
            i += m.end()
            continue
        # Link: [text](url)
        m = re.match(r"\[(.+?)\]\((.+?)\)", text[i:])
        if m:
            result.append(f'#link("{m.group(2)}")[{_escape_typst(m.group(1))}]')
            i += m.end()
            continue
        # Regular char
        result.append(_escape_typst(text[i]))
        i += 1
    return "".join(result)


def _parse_table_typst(lines: list[str], colors: dict) -> str:
    """Parse markdown table rows into a Typst #table() call."""
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip().strip("|")
        if not line:
            continue
        cells = [c.strip() for c in line.split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return ""

    header = rows[0]
    # Skip separator row (---, :---, etc.)
    data_start = 1
    if data_start < len(rows) and all(
        set(c.strip()) <= set("-: ") for c in rows[data_start]
    ):
        data_start += 1
    data = rows[data_start:]
    if not data:
        return ""

    nc = len(header)
    indigo = colors.get("indigo", "#312e81")
    border = colors.get("table-border", "#ddd8c8")
    alt_bg = colors.get("table-alt-bg", "#f9f8f5")

    cells_typst: list[str] = []
    for h in header:
        cells_typst.append(f'text(fill: white, weight: "bold")[{_escape_typst(h)}]')
    for row in data:
        while len(row) < nc:
            row.append("")
        for c in row[:nc]:
            cells_typst.append(f"[{_escape_typst(c)}]")

    col_spec = ", ".join("auto" for _ in range(nc))
    cells_str = ",\n  ".join(cells_typst)

    return (
        f"#table(\n"
        f"  columns: ({col_spec}),\n"
        f"  align: left,\n"
        f"  stroke: 0.5pt + rgb(\"{border}\"),\n"
        f"  fill: (x, y) => {{\n"
        f"    if y == 0 {{ rgb(\"{indigo}\") }}\n"
        f"    else if calc.rem(y, 2) == 1 {{ rgb(\"{alt_bg}\") }}\n"
        f"  }},\n"
        f"  inset: 6pt,\n"
        f"  {cells_str},\n"
        f")"
    )


def convert_md_to_typst(md_text: str, colors: dict | None = None) -> str:
    """Convert booksmith Markdown to Typst markup."""
    if colors is None:
        colors = dict(_DEFAULT_COLORS)

    lines = md_text.splitlines()
    output: list[str] = []
    in_code = False
    code_buf: list[str] = []
    code_lang = ""
    code_fence = ""   # "```" or "~~~"
    table_buf: list[str] = []
    in_table = False

    def flush_table():
        nonlocal table_buf, in_table
        if table_buf:
            tbl = _parse_table_typst(table_buf, colors)
            if tbl:
                output.append(tbl)
            table_buf = []
            in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- Code blocks (``` or ~~~) ---
        is_fence = stripped.startswith("```") or stripped.startswith("~~~")
        if is_fence:
            fence = "```" if stripped.startswith("```") else "~~~"
            if in_code:
                if fence == code_fence:
                    # Close code block — DO NOT escape content for Typst raw block
                    code_text = "\n".join(code_buf)
                    # If content contains ``` on its own line, Typst raw block
                    # would close early. Use 4 backticks instead.
                    has_triple_backtick = any(
                        l.strip() == "```" for l in code_text.split("\n")
                    )
                    if has_triple_backtick:
                        output.append(f"````{code_lang}\n{code_text}\n````")
                    else:
                        output.append(f"```{code_lang}\n{code_text}\n```")
                    in_code = False
                    code_buf = []
                    code_lang = ""
                    code_fence = ""
                else:
                    # Different fence style inside code block — treat as content
                    code_buf.append(line)
            else:
                flush_table()
                in_code = True
                code_fence = fence
                code_lang = stripped[len(fence):].strip()
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # --- Table rows ---
        if stripped.startswith("|") and stripped.endswith("|"):
            table_buf.append(stripped)
            in_table = True
            i += 1
            continue
        elif in_table:
            flush_table()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # --- H1: Chapter heading ---
        if stripped.startswith("# ") and not stripped.startswith("## "):
            raw_title = stripped[2:].strip()
            if raw_title.startswith("manuscript/") or re.match(
                r"^(ch|appendix)\d+[\s./\-]", raw_title, re.I
            ):
                i += 1
                continue
            title = _extract_title(raw_title)
            if not title:
                i += 1
                continue
            output.append(f"\n#pagebreak()\n= {title}\n")
            i += 1
            continue

        # --- H2: Section heading ---
        if stripped.startswith("## ") and not stripped.startswith("### "):
            title = stripped[3:].strip()
            output.append(f"== {title}")
            i += 1
            continue

        # --- H3: Sub-section heading ---
        if stripped.startswith("### ") and not stripped.startswith("#### "):
            title = stripped[4:].strip()
            output.append(f"=== {title}")
            i += 1
            continue

        # --- H4: Sub-sub-section heading ---
        if stripped.startswith("#### "):
            title = stripped[5:].strip()
            output.append(f"==== {title}")
            i += 1
            continue

        # --- Horizontal rule ---
        if re.match(r"^---+\s*$", stripped):
            output.append("#line(length: 100%, stroke: 0.5pt + rgb(\"#ddd8c8\"))")
            i += 1
            continue

        # --- Image: ![alt](path) or ![alt](path){.banner} ---
        m_img = re.match(r"!\[([^\]]*)\]\(([^)]+)\)(\{\.(\w+)\})?\s*$", stripped)
        if m_img:
            alt_text = m_img.group(1)
            img_path = m_img.group(2)
            css_class = m_img.group(4) or ""
            # Normalize path: ../illustrations/ → illustrations/
            if img_path.startswith("../"):
                img_path = img_path[3:]
            elif img_path.startswith("./"):
                img_path = img_path[2:]
            width = "100%" if css_class == "banner" else "80%"
            alt_escaped = _escape_typst(alt_text) if alt_text else "none"
            caption_part = f',\n  caption: [{alt_escaped}]' if alt_text else ''
            output.append(
                f'#figure(\n'
                f'  image("{img_path}", width: {width}){caption_part}\n'
                f')'
            )
            i += 1
            continue

        # --- Blockquote ---
        if stripped.startswith("> "):
            content = _convert_inline(stripped[2:])
            output.append(f"> {content}")
            i += 1
            continue

        # --- Bullet list ---
        if re.match(r"^[-*]\s", stripped):
            content = _convert_inline(re.sub(r"^[-*]\s+", "", stripped))
            output.append(f"- {content}")
            i += 1
            continue

        # --- Numbered list ---
        if re.match(r"^\d+\.\s", stripped):
            content = _convert_inline(re.sub(r"^\d+\.\s+", "", stripped))
            output.append(f"+ {content}")
            i += 1
            continue

        # --- .tip block ---
        if re.match(r"^\.tip\b", stripped, re.I):
            content = re.sub(r"^\.tip\b\s*", "", stripped)
            content = re.sub(r"[{}]", "", content).strip()
            if content:
                output.append(f"#tip[{_convert_inline(content)}]")
            i += 1
            continue

        # --- .term block ---
        if re.match(r"^\.term\b", stripped, re.I):
            content = re.sub(r"^\.term\b\s*", "", stripped)
            content = re.sub(r"[{}]", "", content).strip()
            if content:
                output.append(f"#term[{_convert_inline(content)}]")
            i += 1
            continue

        # --- Plain paragraph (accumulate consecutive lines) ---
        para_lines = [stripped]
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if (
                not next_line
                or next_line.startswith("#")
                or next_line.startswith("|")
                or next_line.startswith("```")
                or next_line.startswith("- ")
                or next_line.startswith("* ")
                or re.match(r"^\d+\.\s", next_line)
                or next_line.startswith("> ")
                or re.match(r"^\.(tip|term)\b", next_line, re.I)
                or re.match(r"^---+\s*$", next_line)
                or re.match(r"^!\[", next_line)
            ):
                break
            para_lines.append(next_line)
            i += 1

        # Join with CJK awareness
        merged = para_lines[0]
        for pl in para_lines[1:]:
            if _is_cjk(merged[-1]) and _is_cjk(pl[0]):
                merged += pl
            else:
                merged += " " + pl

        output.append(_convert_inline(merged))
        i += 1

    # Flush any remaining table
    flush_table()

    return "\n\n".join(output)


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Typst Template Generator
# ═══════════════════════════════════════════════════════════════════════

def _c(name: str, colors: dict) -> str:
    """Get a color from the palette as Typst rgb()."""
    return f'rgb("{colors.get(name, _DEFAULT_COLORS.get(name, "#000000"))}")'


def _c_hex(name: str, colors: dict) -> str:
    """Get a color hex string."""
    return colors.get(name, _DEFAULT_COLORS.get(name, "#000000")).lower()


def generate_typst(config: dict, layout: LayoutConfig, body: str) -> str:
    """Generate complete .typ file from config, layout, and converted body."""
    c = {k: v.lower() for k, v in layout.colors.items()}
    s = layout.style

    title = config.get("title", "Untitled")
    subtitle = config.get("subtitle", "")
    author = config.get("author", "")
    dt = config.get("date", str(date.today()))

    # Code block colors based on theme
    if layout.code_theme == "dark":
        code_bg = _c("code-bg-dark", c)
        code_text = _c("code-text-dark", c)
        code_stroke = "0.5pt + rgb(\"#3b3b5c\")"
    else:
        code_bg = _c("code-bg", c)
        code_text = _c("text", c)
        code_stroke = f'0.5pt + {_c("table-border", c)}'

    # Quote block style
    quote_parts = []
    if s.quote_background:
        quote_parts.append(f"fill: {_c('quote-bg', c)},")
    if s.quote_left_border:
        quote_parts.append(f"stroke: (left: 3pt + {_c('quote-border', c)}),")
    quote_style = "\n    ".join(quote_parts)

    # Build cover page
    cover_parts = []
    cover_parts.append("#page(numbering: none)[")

    # Top accent bar — brand color anchor
    cover_parts.append(f'  #place(top, rect(width: 100%, height: 8mm, fill: {_c("indigo", c)}))')

    # Small amber square decoration under the bar, left-aligned
    cover_parts.append(f'  #place(top + left, dx: 20mm, dy: 14mm)[#box(width: 10pt, height: 10pt, fill: {_c("amber", c)})]')

    # Title block — positioned at upper-center, NOT dead-center
    cover_parts.append("  #align(center)[")
    cover_parts.append("    #v(32%)")

    # Main title
    cover_parts.append(f'    #text(size: {s.cover_title_size}pt, '
                        f'font: "{s.heading_font}", weight: "bold", fill: {_c("indigo", c)})[{_escape_typst(title)}]')

    # Double-line decoration (indigo + amber)
    cover_parts.append("    #v(14pt)")
    cover_parts.append(f'    #box(width: 50mm, height: 1.2pt, fill: {_c("indigo", c)})')
    cover_parts.append("    #v(3pt)")
    cover_parts.append(f'    #box(width: 30mm, height: 1.2pt, fill: {_c("amber", c)})')

    # Subtitle
    if subtitle:
        cover_parts.append("    #v(16pt)")
        cover_parts.append(f'    #text(size: 13pt, fill: {_c("gray", c)})[{_escape_typst(subtitle)}]')

    # Author
    if author:
        cover_parts.append("    #v(28pt)")
        cover_parts.append(f'    #text(size: 11pt, fill: {_c("gray", c)})[{_escape_typst(author)}]')

    cover_parts.append("  ]")

    # Bottom info bar
    cover_parts.append("  #align(center + bottom)[")
    cover_parts.append("    #v(12mm)")
    cover_parts.append(f'    #line(length: 50mm, stroke: 0.5pt + {_c("table-border", c)})')
    cover_parts.append("    #v(6pt)")
    cover_parts.append(f'    #text(size: 9pt, fill: {_c("gray", c)})[{_escape_typst(dt)}]')

    # Brand name if available
    brand_name = config.get("brand", {}).get("name", "")
    if brand_name:
        cover_parts.append("    #v(4pt)")
        cover_parts.append(f'    #text(size: 8pt, fill: {_c("gray", c)})[{_escape_typst(brand_name)}]')

    cover_parts.append("    #v(10mm)")
    cover_parts.append("  ]")

    cover_parts.append("]")
    cover = "\n".join(cover_parts)

    justify_str = "true" if s.justify else "false"

    # Build heading show rules
    heading_rules = f"""// ═══ Heading styles ═══
#show heading.where(level: 1): set block(above: {s.h1_above}em, below: {s.h1_below}em)
#show heading.where(level: 1): set text(fill: {_c('indigo', c)}, font: "{s.heading_font}", size: {s.chapter_size}pt, weight: "bold")

#show heading.where(level: 2): set block(above: {s.h2_above}em, below: {s.h2_below}em)
#show heading.where(level: 2): set text(fill: {_c('indigo-light', c)}, size: {s.section_size}pt, weight: "bold")

#show heading.where(level: 3): set block(above: {s.h3_above}em, below: {s.h3_below}em)
#show heading.where(level: 3): set text(fill: {_c('indigo-light', c)}, size: {s.subsection_size}pt, weight: "bold")"""

    # Conditionally add H4
    if s.subsection_size > 10:
        h4_size = s.subsection_size - 1
        heading_rules += f"""

#show heading.where(level: 4): set block(above: {s.h3_above * 0.8}em, below: {s.h3_below * 0.8}em)
#show heading.where(level: 4): set text(fill: {_c('indigo-light', c)}, size: {h4_size}pt, weight: "bold")"""

    return f"""// ═══ Document metadata ═══
#set document(
  title: "{_escape_typst(title)}",
  author: "{_escape_typst(author)}",
)

// ═══ Page setup ═══
#set page(
  paper: "a4",
  margin: (top: {s.page_margin_top}mm, right: {s.page_margin_right}mm, bottom: {s.page_margin_bottom}mm, left: {s.page_margin_left}mm),
  numbering: "1",
  number-align: center,
)

// ═══ Text defaults ═══
#set text(
  font: ("{s.body_font}", "{s.heading_font}"),
  size: {s.body_size}pt,
  fill: {_c("text", c)},
  lang: "zh",
  region: "cn",
)

// ═══ Paragraph defaults ═══
#set par(
  justify: {justify_str},
  leading: {s.leading}em,
  first-line-indent: {s.first_line_indent},
)
#show par: set block(spacing: {s.paragraph_spacing}em)

{heading_rules}

// ═══ Code block styling ═══
#show raw.where(block: true): it => block(
  fill: {code_bg},
  stroke: {code_stroke},
  inset: {s.code_inset}pt,
  radius: {s.code_radius}pt,
  width: 100%,
  breakable: true,
)[#it]
#show raw.where(block: true): set text(
  font: "{s.code_font}",
  size: {max(s.body_size - 2.5, 8.0)}pt,
)

// ═══ Inline code ═══
#show raw.where(block: false): set text(
  font: "{s.code_font}",
  fill: {_c("amber", c)},
  size: {max(s.body_size - 2.5, 8.0)}pt,
)

// ═══ Quote / blockquote styling ═══
#show quote: it => block(
  breakable: true,
  width: 100%,
)[
  #rect(
    {quote_style}
    inset: (left: 12pt, top: 8pt, bottom: 8pt, right: 8pt),
    width: 100%,
    radius: 2pt,
  )[#it]
]

// ═══ List styling ═══
#set list(spacing: {s.list_spacing}em, indent: 1.5em)
#set enum(spacing: {s.list_spacing}em, indent: 1.5em)

// ═══ Table styling ═══
#show table: set block(spacing: 1em)

// ═══ Custom blocks ═══
#let tip(body) = block(
  breakable: true,
  width: 100%,
)[
  #rect(
    fill: {_c("tip-bg", c)},
    stroke: 0.5pt + {_c("tip-border", c)},
    inset: 8pt,
    radius: 4pt,
    width: 100%,
  )[#body]
]

#let term(title) = block(
  breakable: true,
  width: 100%,
)[
  #rect(
    fill: {_c("tip-bg", c)},
    stroke: (left: 3pt + {_c("indigo-light", c)}),
    inset: 8pt,
    width: 100%,
  )[*#title*]
]

// ═══ Cover page ═══
{cover}

// ═══ Table of Contents ═══
#page(numbering: none)[
  #align(center)[
    #v(25%)
    #text(size: 20pt, font: "{s.heading_font}", fill: {_c("indigo", c)})[
      目 录
    ]
    #v(6pt)
    #line(length: 25%, stroke: 0.8pt + {_c("indigo", c)})
    #v(18pt)
  ]
  #outline(title: none, indent: auto, depth: 2)
]

// ═══ Body content ═══
{body}
"""


# ═══════════════════════════════════════════════════════════════════════
# Section 5: PDF Compiler
# ═══════════════════════════════════════════════════════════════════════

def discover_font_paths() -> list[str]:
    """Discover system font directories for Typst compiler."""
    plat = platform.system()
    candidates: list[str] = []

    if plat == "Darwin":
        candidates = [
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]
    elif plat == "Windows":
        candidates = [
            os.path.expandvars(r"%SystemRoot%\Fonts"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
        ]
    else:
        candidates = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.local/share/fonts"),
            os.path.expanduser("~/.fonts"),
        ]

    return [c for c in candidates if os.path.isdir(c)]


def compile_pdf(content: str, output_path: str, font_paths: list[str], root: str | None = None) -> None:
    """Compile Typst markup to PDF."""
    try:
        typst.compile(
            content.encode("utf-8"),
            output=output_path,
            font_paths=font_paths,
            root=root,
        )
    except typst.TypstError as e:
        print(f"Typst compilation error:\n{e}", file=sys.stderr)
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# Section 6: CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="Booksmith Typst PDF generator v2")
    parser.add_argument("project_dir", help="Book project directory")
    parser.add_argument("--output", default=None, help="Output PDF filename")
    parser.add_argument("--save-typ", default=None, help="Save .typ source for debugging")
    parser.add_argument("--style", default=None, choices=list(_STYLE_PRESETS.keys()),
                        help="Override layout style (classic/modern/academic/minimal)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    project_json = project_dir / "project.json"
    if not project_json.exists():
        print(
            f"\n[ERROR] project.json not found: {project_json}\n"
            f"\n  Expected directory structure:\n"
            f"    {project_dir}/\n"
            f"    ├── project.json          # Required: book metadata\n"
            f"    ├── manuscript/           # Required: chapter .md files\n"
            f"    │   ├── ch01.md\n"
            f"    │   ├── ch02.md\n"
            f"    │   └── ...\n"
            f"    ├── illustrations/        # Optional: images\n"
            f"    └── layout.md             # Optional: styling parameters\n"
            f"\n  Please ensure the project directory was created with the booksmith skill.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    config = json.loads(project_json.read_text(encoding="utf-8"))

    # Validate required fields in project.json
    required_fields = ["title", "target_reader", "style", "chapters_planned", "has_illustrations", "status", "current_phase", "chapters_completed"]
    missing = [f for f in required_fields if f not in config]
    if missing:
        print(
            f"\n[WARNING] project.json is missing required fields: {', '.join(missing)}\n"
            f"  This may cause errors during PDF generation.\n"
            f"  Required fields: {', '.join(required_fields)}\n"
            f"  See SKILL.md for the complete project.json template.\n",
            file=sys.stderr,
        )

    # Parse layout.md
    layout = parse_layout(_LAYOUT_PATH)

    # Check project.json for layout_style override
    proj_layout_style = config.get("layout_style")
    if proj_layout_style and proj_layout_style in _STYLE_PRESETS:
        layout = LayoutConfig(
            colors=layout.colors,
            style=_STYLE_PRESETS[proj_layout_style],
            code_theme=layout.code_theme,
        )

    # Override style from CLI if provided (highest priority)
    if args.style:
        layout = LayoutConfig(
            colors=layout.colors,
            style=_STYLE_PRESETS[args.style],
            code_theme=layout.code_theme,
        )

    s = layout.style
    print(f"Style: {s.name}")
    print(f"  Body: {s.body_font} {s.body_size}pt, leading={s.leading}em")
    print(f"  Heading: {s.heading_font} H1={s.chapter_size}pt H2={s.section_size}pt")
    print(f"  Margins: {s.page_margin_top}/{s.page_margin_right}/{s.page_margin_bottom}/{s.page_margin_left}mm")

    # Read manuscript files
    manuscript_dir = project_dir / "manuscript"
    if not manuscript_dir.exists():
        print(
            f"\n[ERROR] manuscript/ directory not found: {manuscript_dir}\n"
            f"\n  Expected structure:\n"
            f"    {project_dir}/manuscript/\n"
            f"    ├── ch01.md\n"
            f"    ├── ch02.md\n"
            f"    ├── ...\n"
            f"    ├── ch10.md\n"
            f"    ├── appendix-a.md   # Optional\n"
            f"    └── glossary.md     # Optional\n"
            f"\n  Note: manuscript/ must be flat — no subdirectories.\n"
            f"  Files are sorted alphabetically (ch01-ch99, then appendix-*).\n",
            file=sys.stderr,
        )
        sys.exit(1)

    def sort_key(p: Path) -> tuple:
        return (0, p.stem) if not p.stem.startswith("appendix") else (1, p.stem)

    files = sorted(manuscript_dir.glob("*.md"), key=sort_key)
    files = [f for f in files if f.stem not in ("glossary", "anchor-sample")]
    if not files:
        print(
            f"\n[ERROR] No .md files found in {manuscript_dir}\n"
            f"\n  The manuscript/ directory exists but contains no .md files.\n"
            f"  Expected chapter files like:\n"
            f"    ch01.md, ch02.md, ch03.md, ...\n"
            f"\n  Current directory contents:\n"
            f"    {[p.name for p in manuscript_dir.iterdir()]}\n"
            f"\n  Please write chapter content before compiling.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Manuscript: {len(files)} files")

    # Convert each file to Typst markup
    body_parts: list[str] = []
    for f in files:
        md = f.read_text(encoding="utf-8")
        body_parts.append(convert_md_to_typst(md, layout.colors))

    # Generate complete .typ
    pdf_config = {
        "title": config.get("title", "Untitled"),
        "subtitle": config.get("subtitle", ""),
        "author": config.get("author", ""),
        "date": str(date.today()),
    }
    full_typst = generate_typst(pdf_config, layout, "\n\n".join(body_parts))

    # Discover fonts and compile
    font_paths = discover_font_paths()

    output_name = args.output or config.get("delivered_pdf", "ebook.pdf")
    if not output_name.endswith(".pdf"):
        output_name += ".pdf"
    pdf_path = project_dir / output_name

    print(f"Compiling Typst -> {pdf_path}")
    if args.save_typ:
        save_path = Path(args.save_typ)
        save_path.write_text(full_typst, encoding="utf-8")
        print(f"Saved .typ source -> {args.save_typ}")

    # Pass project_dir as root so image paths resolve correctly
    compile_pdf(full_typst, str(pdf_path), font_paths, root=str(project_dir))

    size = pdf_path.stat().st_size
    print(f"Done: {pdf_path.name} ({size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
