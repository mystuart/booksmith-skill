#!/usr/bin/env python3
"""booksmith-typst.py — Generate book PDF using Typst typesetting engine.

Reads layout.md for styling, project.json for metadata, manuscript/*.md for content.
Outputs a PDF with cover page, clickable TOC, bookmarks, and CJK-native typesetting.

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
# Section 2: Layout Parser
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class LayoutConfig:
    colors: dict = field(default_factory=dict)
    body_size: float = 10.5
    chapter_size: float = 18.0
    section_size: float = 13.0
    cover_title_size: float = 30.0
    body_leading_factor: float = 1.85
    code_size: float = 8.0
    code_leading: float = 12.0
    margins_mm: tuple = (22, 20, 28, 20)  # top, right, bottom, left


_DEFAULT_COLORS = {
    "indigo": "#312E81",
    "indigo-light": "#4338CA",
    "amber": "#D97706",
    "text": "#2D2D2D",
    "gray": "#6B7280",
    "code-bg": "#F5F5F5",
    "tip-bg": "#EEF2FF",
    "tip-border": "#C7D2FE",
}


def parse_layout(path: Path) -> LayoutConfig:
    """Parse layout.md to extract styling parameters."""
    if not path.exists():
        print(f"Warning: {path} not found, using defaults", file=sys.stderr)
        return LayoutConfig(colors=dict(_DEFAULT_COLORS))

    text = path.read_text(encoding="utf-8")
    colors = _parse_css_vars(text)
    margins = _parse_margins(text)
    sizes = _parse_sizes(text)
    leading = _parse_leading(text)

    return LayoutConfig(
        colors=colors,
        body_size=sizes.get("body", 10.5),
        chapter_size=sizes.get("chapter", 18.0),
        section_size=sizes.get("section", 13.0),
        cover_title_size=sizes.get("cover", 30.0),
        body_leading_factor=leading.get("body", 1.85),
        code_size=sizes.get("code", 8.0),
        code_leading=leading.get("code", 12.0),
        margins_mm=margins,
    )


def _parse_css_vars(text: str) -> dict:
    colors = dict(_DEFAULT_COLORS)
    css_blocks = re.findall(r"```css\n(.*?)```", text, re.DOTALL)
    for block in css_blocks:
        for m in re.finditer(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block):
            colors[m.group(1)] = m.group(2).lower()
    return colors


def _parse_margins(text: str) -> tuple:
    default = (22, 20, 28, 20)
    m = re.search(
        r"margin:\s*([\d.]+)cm\s*([\d.]+)cm\s*([\d.]+)cm\s*([\d.]+)cm", text
    )
    if m:
        return tuple(float(x) * 10 for x in m.groups())
    return default


def _parse_sizes(text: str) -> dict:
    sizes: dict[str, float] = {}
    pt_match = re.search(r"正文.*?(\d+(?:\.\d+)?)\s*pt", text)
    if pt_match:
        sizes["body"] = float(pt_match.group(1))
    return sizes


def _parse_leading(text: str) -> dict:
    leading: dict[str, float] = {}
    m = re.search(r"正文行高[：:]\s*([\d.]+)", text)
    if m:
        leading["body"] = float(m.group(1))
    m = re.search(r"代码块行高[：:]\s*([\d.]+)", text)
    if m:
        leading["code"] = float(m.group(1))
    return leading


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Markdown → Typst Converter
# ═══════════════════════════════════════════════════════════════════════


def _extract_title(raw: str) -> str:
    """Extract clean title from booksmith heading formats."""
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
    # Escape first, then re-insert formatting
    # We process inline patterns before escaping to preserve them
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
    border = "#ddd8c8"
    alt_bg = "#f9f8f5"

    # Build table content
    cells_typst: list[str] = []
    # Header row
    for h in header:
        cells_typst.append(f'text(fill: white, weight: "bold")[{_escape_typst(h)}]')
    # Data rows
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
        f"  inset: 5pt,\n"
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

        # --- Code blocks ---
        if stripped.startswith("```"):
            if in_code:
                # Close code block
                code_text = "\n".join(code_buf)
                output.append(f"```{code_lang}\n{code_text}\n```")
                in_code = False
                code_buf = []
                code_lang = ""
            else:
                flush_table()
                in_code = True
                code_lang = stripped[3:].strip()
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
        if stripped.startswith("### "):
            title = stripped[4:].strip()
            output.append(f"=== {title}")
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


def generate_typst(config: dict, layout: LayoutConfig, body: str) -> str:
    """Generate complete .typ file from config, layout, and converted body."""
    c = {k: v.lower() for k, v in layout.colors.items()}
    top, right, bottom, left = layout.margins_mm
    # Chinese typesetting: leading = body_leading_factor - 1.0, boosted for readability
    leading_em = layout.body_leading_factor - 1.0 + 0.3

    title = config.get("title", "Untitled")
    subtitle = config.get("subtitle", "")
    author = config.get("author", "")
    dt = config.get("date", str(date.today()))

    # Build cover page
    cover_parts = []
    cover_parts.append("#page(numbering: none)[")
    cover_parts.append("  #align(center + horizon)[")
    cover_parts.append(f"    #rect(width: 40mm, height: 3pt, fill: {_c('indigo', c)})")
    cover_parts.append("    #v(14pt)")
    cover_parts.append('    #box(rotate(45deg)[#rect(width: 8pt, height: 8pt, fill: '
                        f'{_c("amber", c)})])')
    cover_parts.append("    #v(20pt)")
    cover_parts.append(f'    #text(size: {layout.cover_title_size}pt, '
                        f'font: "Noto Serif SC", fill: {_c("indigo", c)})[{_escape_typst(title)}]')
    if subtitle:
        cover_parts.append("    #v(24pt)")
        cover_parts.append(f'    #text(size: 13pt, fill: {_c("gray", c)})['
                           f'{_escape_typst(subtitle)}]')
    if author:
        cover_parts.append("    #v(24pt)")
        cover_parts.append(f'    #text(size: 11pt, fill: {_c("gray", c)})['
                           f'{_escape_typst(author)}]')
    cover_parts.append("    #v(1fr)")
    cover_parts.append(f'    #line(length: 60mm, stroke: 0.5pt + {_c("indigo", c)})')
    cover_parts.append("    #v(18pt)")
    cover_parts.append(f'    #text(size: 9pt, fill: {_c("gray", c)})[{_escape_typst(dt)}]')
    cover_parts.append("  ]")
    cover_parts.append("]")
    cover = "\n".join(cover_parts)

    return f"""// ═══ Document metadata ═══
#set document(
  title: "{_escape_typst(title)}",
  author: "{_escape_typst(author)}",
)

// ═══ Page setup ═══
#set page(
  paper: "a4",
  margin: (top: {top}mm, right: {right}mm, bottom: {bottom}mm, left: {left}mm),
  numbering: "1",
  number-align: center,
)

// ═══ Text defaults ═══
#set text(
  font: ("Noto Sans SC", "Noto Serif SC"),
  size: {layout.body_size}pt,
  fill: {_c("text", c)},
  lang: "zh",
)
#set par(
  justify: true,
  leading: {leading_em:.2f}em,
  first-line-indent: 2em,
)
// Paragraph block spacing = leading for grid alignment
#show par: set block(spacing: {leading_em:.2f}em)

// ═══ Heading styles ═══
// Chinese typesetting standard: heading spacing proportional to body size
// H1: above 1.5em, below 1.2em | H2: above 1em, below 0.8em | H3: above 0.8em, below 0.5em
// Force indent on first paragraph after heading (Chinese convention: ALL paragraphs indent 2em)
#show heading.where(level: 1): it => {{
  set block(above: 1.5em, below: 1.2em)
  set text(fill: {_c('indigo', c)}, font: "Noto Serif SC", size: {layout.chapter_size}pt, weight: "bold")
  it
  par()[#h(0em)]
}}

#show heading.where(level: 2): it => {{
  set block(above: 1em, below: 0.8em)
  set text(fill: {_c("indigo-light", c)}, size: {layout.section_size}pt, weight: "bold")
  it
  par()[#h(0em)]
}}

#show heading.where(level: 3): it => {{
  set block(above: 0.8em, below: 0.5em)
  set text(fill: {_c("indigo-light", c)}, size: {layout.body_size + 1}pt, weight: "bold")
  it
  par()[#h(0em)]
}}

// ═══ Code block styling ═══
#show raw.where(block: true): rect(
  fill: {_c("code-bg", c)},
  stroke: 0.5pt + rgb("#ddd8c8"),
  inset: 8pt,
  radius: 2pt,
  width: 100%,
)
#show raw.where(block: true): set text(
  font: "JetBrains Mono",
  size: {layout.code_size}pt,
)

// ═══ Inline code ═══
#show raw.where(block: false): set text(
  font: "JetBrains Mono",
  fill: {_c("amber", c)},
)

// ═══ Custom blocks ═══
#let tip(body) = rect(
  fill: {_c("tip-bg", c)},
  stroke: 0.5pt + {_c("tip-border", c)},
  inset: 8pt,
  radius: 4pt,
  width: 100%,
)[#body]

#let term(title) = rect(
  fill: {_c("tip-bg", c)},
  stroke: (left: 3pt + {_c("indigo-light", c)}),
  inset: 8pt,
  width: 100%,
)[*#title*]

// ═══ Cover page ═══
{cover}

// ═══ Table of Contents ═══
#page(numbering: none)[
  #align(center)[
    #v(25%)
    #text(size: 20pt, font: "Noto Serif SC", fill: {_c("indigo", c)})[
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


def compile_pdf(content: str, output_path: str, font_paths: list[str]) -> None:
    """Compile Typst markup to PDF."""
    try:
        typst.compile(
            content.encode("utf-8"),
            output=output_path,
            font_paths=font_paths,
        )
    except typst.TypstError as e:
        print(f"Typst compilation error:\n{e}", file=sys.stderr)
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# Section 6: CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="Booksmith Typst PDF generator")
    parser.add_argument("project_dir", help="Book project directory")
    parser.add_argument("--output", default=None, help="Output PDF filename")
    parser.add_argument("--save-typ", default=None, help="Save .typ source for debugging")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    project_json = project_dir / "project.json"
    if not project_json.exists():
        print(f"Error: {project_json} not found", file=sys.stderr)
        sys.exit(1)

    config = json.loads(project_json.read_text(encoding="utf-8"))

    # Parse layout.md
    layout = parse_layout(_LAYOUT_PATH)
    print(f"Layout: body={layout.body_size}pt, margins={layout.margins_mm}mm")

    # Read manuscript files
    manuscript_dir = project_dir / "manuscript"
    if not manuscript_dir.exists():
        print(f"Error: {manuscript_dir} not found", file=sys.stderr)
        sys.exit(1)

    def sort_key(p: Path) -> tuple:
        return (0, p.stem) if not p.stem.startswith("appendix") else (1, p.stem)

    files = sorted(manuscript_dir.glob("*.md"), key=sort_key)
    files = [f for f in files if f.stem != "glossary"]
    if not files:
        print(f"Error: no .md files in {manuscript_dir}", file=sys.stderr)
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
        Path(args.save_typ).write_text(full_typst, encoding="utf-8")
        print(f"Saved .typ source -> {args.save_typ}")
    compile_pdf(full_typst, str(pdf_path), font_paths)

    size = pdf_path.stat().st_size
    print(f"Done: {pdf_path.name} ({size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
