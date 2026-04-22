#!/usr/bin/env python3
"""
booksmith-rl.py — Booksmith PDF 生成器（ReportLab 版，fallback）

从 layout.md 读取排版参数，将 manuscript/*.md 转为带书签/目录的 PDF。
仅依赖 reportlab，不依赖 any2pdf 或任何外部浏览器。

用法：
  python3 booksmith-pdf.py ~/Books/project-dir [--output ebook.pdf]
"""

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Imports & Constants
# ═══════════════════════════════════════════════════════════════════════

import argparse
import json
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

_SKILL_DIR = Path(__file__).resolve().parent.parent
_LAYOUT_PATH = _SKILL_DIR / "layout.md"
_PLAT = platform.system()


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Font Management
# ═══════════════════════════════════════════════════════════════════════

_FONT_CANDIDATES = {
    "Sans": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ],
    "SansBold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ],
    "CJK": [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ],
    "CJKBold": [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ],
    "Mono": [
        ("/System/Library/Fonts/Menlo.ttc", 0),
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    ],
    "MonoBold": [
        ("/System/Library/Fonts/Menlo.ttc", 1),
        "C:/Windows/Fonts/consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ],
}

_CJK_RANGES = [
    (0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF),
    (0x3000, 0x303F), (0xFF00, 0xFFEF), (0x2E80, 0x2EFF),
    (0x2F00, 0x2FDF), (0xFE30, 0xFE4F), (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F), (0x2B740, 0x2B81F),
]


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def _find_font(candidates: list) -> str | tuple | None:
    for c in candidates:
        path = c[0] if isinstance(c, tuple) else c
        if os.path.exists(path):
            return c
    return None


def register_fonts() -> None:
    missing: list[str] = []
    for name, candidates in _FONT_CANDIDATES.items():
        spec = _find_font(candidates)
        if spec is None:
            missing.append(name)
            continue
        try:
            if isinstance(spec, tuple):
                pdfmetrics.registerFont(TTFont(name, spec[0], subfontIndex=spec[1]))
            else:
                pdfmetrics.registerFont(TTFont(name, spec))
        except Exception as e:
            missing.append(name)
            print(f"Warning: Font {name} — {e}", file=sys.stderr)
    if missing:
        print(
            f"Warning: Missing fonts: {', '.join(missing)}. "
            "PDF may have \u25a1 characters.",
            file=sys.stderr,
        )
        if _PLAT == "Linux":
            print(
                "  Fix: sudo apt install fonts-noto fonts-noto-cjk fonts-dejavu-core",
                file=sys.stderr,
            )
        elif _PLAT == "Windows":
            print(
                "  Fix: Install Noto fonts from https://fonts.google.com/noto",
                file=sys.stderr,
            )
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold")


def _font_wrap(text: str) -> str:
    """Wrap CJK runs in <font name='CJK'> tags for ReportLab Paragraph."""
    out: list[str] = []
    buf: list[str] = []
    in_cjk = False
    for ch in text:
        c = _is_cjk(ch)
        if c != in_cjk and buf:
            seg = "".join(buf)
            out.append(f"<font name='CJK'>{seg}</font>" if in_cjk else seg)
            buf = []
        buf.append(ch)
        in_cjk = c
    if buf:
        seg = "".join(buf)
        out.append(f"<font name='CJK'>{seg}</font>" if in_cjk else seg)
    return "".join(out)


def _draw_mixed(
    c, x: float, y: float, text: str, size: float,
    anchor: str = "left", max_w: float = 0,
) -> float:
    """Draw mixed CJK/Latin text on canvas. Returns bottom y."""
    if max_w > 0:
        return _draw_mixed_wrap(c, x, y, text, size, anchor, max_w)
    segs: list[tuple[str, str]] = []
    buf: list[str] = []
    in_cjk = False
    for ch in text:
        cj = _is_cjk(ch)
        if cj != in_cjk and buf:
            segs.append(("CJK" if in_cjk else "Sans", "".join(buf)))
            buf = []
        buf.append(ch)
        in_cjk = cj
    if buf:
        segs.append(("CJK" if in_cjk else "Sans", "".join(buf)))
    total_w = sum(c.stringWidth(t, f, size) for f, t in segs)
    if anchor == "right":
        x -= total_w
    elif anchor == "center":
        x -= total_w / 2
    for font, txt in segs:
        c.setFont(font, size)
        c.drawString(x, y, txt)
        x += c.stringWidth(txt, font, size)
    return y


def _measure_mixed(c, text: str, size: float) -> float:
    w = 0.0
    buf: list[str] = []
    in_cjk = False
    for ch in text:
        cj = _is_cjk(ch)
        if cj != in_cjk and buf:
            w += c.stringWidth("".join(buf), "CJK" if in_cjk else "Sans", size)
            buf = []
        buf.append(ch)
        in_cjk = cj
    if buf:
        w += c.stringWidth("".join(buf), "CJK" if in_cjk else "Sans", size)
    return w


def _draw_mixed_wrap(
    c, x: float, y: float, text: str, size: float,
    anchor: str, max_w: float,
) -> float:
    words = text.split(" ")
    while size > 16:
        longest = max(_measure_mixed(c, w, size) for w in words)
        if longest <= max_w:
            break
        size -= 1
    lines: list[str] = []
    cur: list[str] = []
    cur_w = 0.0
    space_w = c.stringWidth(" ", "Sans", size)
    for word in words:
        ww = _measure_mixed(c, word, size)
        test_w = cur_w + (space_w if cur else 0) + ww
        if cur and test_w > max_w:
            lines.append(" ".join(cur))
            cur = [word]
            cur_w = ww
        else:
            cur.append(word)
            cur_w = test_w
    if cur:
        lines.append(" ".join(cur))
    line_h = size * 1.3
    for i, line in enumerate(lines):
        _draw_mixed(c, x, y - i * line_h, line, size, anchor)
    return y - (len(lines) - 1) * line_h


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_code(text: str) -> str:
    out: list[str] = []
    for line in text.split("\n"):
        e = esc(line)
        stripped = e.lstrip(" ")
        indent = len(e) - len(stripped)
        out.append("&nbsp;" * indent + stripped)
    return "<br/>".join(out)


def md_inline(text: str, accent_hex: str = "#D97706") -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`(.+?)`",
        rf"<font name='Mono' size='8' color='{accent_hex}'>\1</font>",
        text,
    )
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"<u>\1</u>", text)
    return _font_wrap(text)


def md_inline_body(text: str, accent_hex: str = "#D97706") -> str:
    """Simplified inline parser for body text — skips font-wrap for split compatibility."""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`(.+?)`",
        rf"<font name='Mono' size='8' color='{accent_hex}'>\1</font>",
        text,
    )
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"<u>\1</u>", text)
    return text


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Layout Parser
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
        return LayoutConfig(colors=_hex_dict(_DEFAULT_COLORS))

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
    colors = _hex_dict(_DEFAULT_COLORS)
    css_blocks = re.findall(r"```css\n(.*?)```", text, re.DOTALL)
    for block in css_blocks:
        for m in re.finditer(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block):
            key, val = m.group(1), m.group(2)
            colors[key] = HexColor(val)
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


def _hex_dict(d: dict) -> dict:
    return {k: HexColor(v) if isinstance(v, str) else v for k, v in d.items()}


def _color_hex(color) -> str:
    """Convert HexColor to hex string for HTML attributes."""
    if isinstance(color, str):
        return color
    r, g, b = int(color.red * 255), int(color.green * 255), int(color.blue * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Markdown Parser
# ═══════════════════════════════════════════════════════════════════════

_anchor_counter = [0]


def _next_anchor() -> str:
    _anchor_counter[0] += 1
    return f"anchor_{_anchor_counter[0]}"


class ChapterMark(Flowable):
    """Zero-dimension flowable that creates a PDF bookmark and records page number."""
    width = 0
    height = 0

    def __init__(self, title: str, level: int = 0):
        Flowable.__init__(self)
        self.title = title
        self.level = level
        self.key = _next_anchor()
        self.page_num = 0  # filled by afterFlowable

    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(
            self.title, self.key, level=self.level, closed=(self.level == 0)
        )


class HRule(Flowable):
    """Horizontal rule flowable."""

    def __init__(self, width: float, thick: float = 0.5, color=None):
        Flowable.__init__(self)
        self.width = width
        self.thick = thick
        self.color = color or HexColor("#DDD8C8")
        self.height = thick + 4

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thick)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


def _extract_title(raw: str) -> str:
    """Extract clean chapter title from booksmith heading formats."""
    t = raw.strip()
    t = re.sub(r"^Chapter\s+\d+\s*[—–-]\s*", "", t)
    t = re.sub(r"^§\s*\d+\.?\d*\s*", "", t)
    t = t.strip('"').strip("'")
    return t.strip()


def parse_manuscript(
    md_text: str, styles: dict, accent_hex: str
) -> tuple[list, list]:
    """Parse booksmith Markdown into ReportLab story + TOC entries."""
    lines = md_text.split("\n")
    story: list = []
    toc: list = []
    i = 0
    in_code = False
    code_buf: list[str] = []
    body_w = styles.get("_body_w", 450)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        i += 1

        # --- Code block ---
        if stripped.startswith("```"):
            if in_code:
                code_text = "\n".join(code_buf)
                story.append(Paragraph(esc_code(code_text), styles["code"]))
                story.append(Spacer(1, 6))
                code_buf = []
                in_code = False
            else:
                in_code = True
                code_buf = []
            continue

        if in_code:
            code_buf.append(line)
            continue

        # Skip empty lines
        if not stripped:
            continue

        # --- H1: Chapter heading ---
        if stripped.startswith("# ") and not stripped.startswith("## "):
            raw_title = stripped[2:].strip()
            if raw_title.startswith("manuscript/") or re.match(
                r"^(ch|appendix)\d+[\s./\-]", raw_title, re.I
            ):
                continue
            title = _extract_title(raw_title)
            if not title:
                continue

            mark = ChapterMark(title, level=0)
            story.append(PageBreak())
            story.append(mark)
            story.append(Spacer(1, 8))
            story.append(Paragraph(md_inline(title, accent_hex), styles["chapter"]))
            story.append(Spacer(1, 12))
            toc.append((title, mark.key, 0))
            continue

        # --- H2: Section heading ---
        if stripped.startswith("## ") and not stripped.startswith("### "):
            title = stripped[3:].strip()
            mark = ChapterMark(title, level=1)
            story.append(Spacer(1, 10))
            story.append(mark)
            story.append(Paragraph(md_inline(title, accent_hex), styles["h2"]))
            story.append(Spacer(1, 6))
            toc.append((title, mark.key, 1))
            continue

        # --- H3: Sub-section heading ---
        if stripped.startswith("### "):
            title = stripped[4:].strip()
            story.append(Spacer(1, 6))
            story.append(Paragraph(md_inline(title, accent_hex), styles["h3"]))
            story.append(Spacer(1, 4))
            continue

        # --- Table ---
        if stripped.startswith("|"):
            table_lines = [stripped]
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            t = _parse_table(table_lines, styles, accent_hex, body_w)
            if t:
                story.append(Spacer(1, 6))
                story.append(t)
                story.append(Spacer(1, 6))
            continue

        # --- Horizontal rule ---
        if re.match(r"^-{3,}$", stripped):
            story.append(Spacer(1, 6))
            story.append(HRule(body_w))
            story.append(Spacer(1, 6))
            continue

        # --- Blockquote ---
        if stripped.startswith("> "):
            content = re.sub(r"^>\s*", "", stripped)
            story.append(
                Paragraph(md_inline_body(content, accent_hex), styles["body_indent"])
            )
            continue

        # --- Bullet list ---
        if re.match(r"^[-*]\s", stripped):
            content = re.sub(r"^[-*]\s+", "", stripped)
            story.append(
                Paragraph(
                    f"\u2022  {md_inline_body(content, accent_hex)}", styles["bullet"]
                )
            )
            continue

        # --- Numbered list ---
        if re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            num = re.match(r"^(\d+)", stripped).group(1)
            story.append(
                Paragraph(
                    f"{num}.  {md_inline_body(content, accent_hex)}", styles["bullet"]
                )
            )
            continue

        # --- .tip block ---
        if re.match(r"^\.tip\b", stripped, re.I):
            content = re.sub(r"^\.tip\b\s*", "", stripped)
            content = re.sub(r"[{}]", "", content).strip()
            if content:
                story.append(
                    Paragraph(md_inline_body(content, accent_hex), styles["body_indent"])
                )
            continue

        # --- .term block ---
        if re.match(r"^\.term\b", stripped, re.I):
            content = re.sub(r"^\.term\b\s*", "", stripped)
            content = re.sub(r"[{}]", "", content).strip()
            if content:
                story.append(
                    Paragraph(
                        f"<b>{md_inline_body(content, accent_hex)}</b>", styles["body"]
                    )
                )
            continue

        # --- Plain paragraph ---
        para_lines = [stripped]
        while i < len(lines):
            next_line = lines[i].strip()
            if (
                not next_line
                or next_line.startswith("#")
                or next_line.startswith("|")
                or next_line.startswith("```")
                or next_line.startswith("> ")
                or re.match(r"^[-*]\s", next_line)
                or re.match(r"^\d+\.\s", next_line)
                or re.match(r"^-{3,}$", next_line)
                or re.match(r"^\.(tip|term)\b", next_line, re.I)
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

        story.append(Paragraph(md_inline_body(merged, accent_hex), styles["body"]))

    return story, toc


def _parse_table(
    lines: list[str], styles: dict, accent_hex: str, body_w: float
) -> Table | None:
    """Parse markdown table into ReportLab Table."""
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip().strip("|")
        rows.append([c.strip() for c in line.split("|")])

    if len(rows) < 2:
        return None

    header = rows[0]
    data = [r for r in rows[1:] if not all(set(c.strip()) <= set("-: ") for c in r)]
    if not data:
        return None

    nc = len(header)
    accent_color = styles.get("_accent", HexColor("#312E81"))

    td = [[Paragraph(md_inline(h, accent_hex), styles["th"]) for h in header]]
    for r in data:
        while len(r) < nc:
            r.append("")
        td.append(
            [Paragraph(md_inline(c, accent_hex), styles["tc"]) for c in r[:nc]]
        )

    avail = body_w - 4 * mm
    max_lens = [
        max(len(r[ci]) if ci < len(r) else 0 for r in [header] + data)
        for ci in range(nc)
    ]
    max_lens = [max(m, 2) for m in max_lens]
    total = sum(max_lens)
    cw = [avail * m / total for m in max_lens]
    min_w = 18 * mm
    for ci in range(nc):
        if cw[ci] < min_w:
            deficit = min_w - cw[ci]
            cw[ci] = min_w
            widest = sorted(range(nc), key=lambda x: -cw[x])
            for oi in widest:
                if oi != ci:
                    cw[oi] -= deficit
                    break

    t = Table(td, colWidths=cw, repeatRows=1, splitByRow=1, splitInRow=1)
    border_color = HexColor("#DDD8C8")
    alt_bg = HexColor("#F9F8F5")
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), accent_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, alt_bg]),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    return t


# ═══════════════════════════════════════════════════════════════════════
# Section 5: PDF Builder
# ═══════════════════════════════════════════════════════════════════════


class BooksmithPDF:
    """Build PDF from parsed manuscript using layout.md styling."""

    def __init__(self, config: dict, layout: LayoutConfig):
        self.cfg = config
        self.layout = layout
        self.page_w, self.page_h = A4
        top, right, bottom, left = layout.margins_mm
        self.lm = left * mm
        self.rm = right * mm
        self.tm = top * mm
        self.bm = bottom * mm
        self.body_w = self.page_w - self.lm - self.rm
        self.body_h = self.page_h - self.tm - self.bm
        self.accent_hex = _color_hex(layout.colors.get("amber", HexColor("#D97706")))
        self.ST = self._build_styles()

    def _build_styles(self) -> dict:
        L = self.layout
        colors = L.colors
        body_sz = L.body_size
        body_lead = body_sz * L.body_leading_factor

        s: dict[str, ParagraphStyle] = {}

        s["chapter"] = ParagraphStyle(
            "Chapter",
            fontName="CJK",
            fontSize=L.chapter_size,
            leading=L.chapter_size * 1.45,
            textColor=colors.get("indigo", HexColor("#312E81")),
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
        )

        s["h2"] = ParagraphStyle(
            "H2",
            fontName="CJK",
            fontSize=L.section_size,
            leading=L.section_size * 1.4,
            textColor=colors.get("indigo", HexColor("#4338CA")),
            alignment=TA_LEFT,
            spaceBefore=10,
            spaceAfter=4,
        )

        s["h3"] = ParagraphStyle(
            "H3",
            fontName="CJK",
            fontSize=L.section_size - 2,
            leading=(L.section_size - 2) * 1.4,
            textColor=colors.get("indigo-light", HexColor("#4338CA")),
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=4,
        )

        s["body"] = ParagraphStyle(
            "Body",
            fontName="CJK",
            fontSize=body_sz,
            leading=body_lead,
            textColor=colors.get("text", HexColor("#2D2D2D")),
            alignment=TA_JUSTIFY,
            spaceBefore=2,
            spaceAfter=6,
            wordWrap="CJK",
        )

        s["body_indent"] = ParagraphStyle(
            "BodyIndent",
            parent=s["body"],
            leftIndent=14,
            rightIndent=14,
            textColor=colors.get("gray", HexColor("#6B7280")),
        )

        s["bullet"] = ParagraphStyle(
            "Bullet",
            fontName="CJK",
            fontSize=body_sz,
            leading=body_lead,
            textColor=colors.get("text", HexColor("#2D2D2D")),
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
            leftIndent=18,
            bulletIndent=6,
            wordWrap="CJK",
        )

        s["code"] = ParagraphStyle(
            "Code",
            fontName="Mono",
            fontSize=L.code_size,
            leading=L.code_leading,
            textColor=HexColor("#3D3D3A"),
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=4,
            leftIndent=8,
            rightIndent=8,
            backColor=colors.get("code-bg", HexColor("#F5F5F5")),
            borderColor=HexColor("#DDD8C8"),
            borderWidth=0.5,
            borderPadding=6,
        )

        s["toc_chapter"] = ParagraphStyle(
            "TOC1",
            fontName="CJK",
            fontSize=11,
            leading=20,
            textColor=colors.get("text", HexColor("#2D2D2D")),
            leftIndent=0,
            spaceBefore=8,
            spaceAfter=4,
        )

        s["toc_section"] = ParagraphStyle(
            "TOC2",
            fontName="CJK",
            fontSize=9.5,
            leading=16,
            textColor=colors.get("gray", HexColor("#6B7280")),
            leftIndent=16,
            spaceBefore=1,
            spaceAfter=1,
        )

        s["th"] = ParagraphStyle(
            "TH",
            fontName="CJK",
            fontSize=8.5,
            leading=12,
            textColor=white,
            alignment=TA_LEFT,
        )

        s["tc"] = ParagraphStyle(
            "TC",
            fontName="CJK",
            fontSize=8,
            leading=11,
            textColor=colors.get("text", HexColor("#2D2D2D")),
            alignment=TA_LEFT,
        )

        # Hidden metadata for parse_manuscript
        s["_body_w"] = self.body_w
        s["_accent"] = colors.get("indigo", HexColor("#312E81"))

        return s

    def _cover_page(self, c, doc) -> None:
        c.saveState()

        # Background
        c.setFillColor(white)
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)

        indigo = self.layout.colors.get("indigo", HexColor("#312E81"))
        amber = self.layout.colors.get("amber", HexColor("#D97706"))
        gray = self.layout.colors.get("gray", HexColor("#6B7280"))

        cx = self.page_w / 2

        # Top decorative bar
        bar_y = self.page_h * 0.82
        bar_w = 40 * mm
        c.setFillColor(indigo)
        c.rect(cx - bar_w / 2, bar_y, bar_w, 3, fill=1, stroke=0)

        # Small amber diamond accent
        diamond_y = bar_y - 14
        c.setFillColor(amber)
        c.saveState()
        c.translate(cx, diamond_y)
        c.rotate(45)
        c.rect(-4, -4, 8, 8, fill=1, stroke=0)
        c.restoreState()

        # Title
        title = self.cfg.get("title", "Untitled")
        title_size = self.layout.cover_title_size
        c.setFillColor(indigo)
        title_y = self.page_h * 0.52
        btm = _draw_mixed(
            c, cx, title_y, title, title_size,
            anchor="center", max_w=self.page_w - 60 * mm,
        )

        # Subtitle
        sub = self.cfg.get("subtitle", "")
        if sub:
            c.setFillColor(gray)
            _draw_mixed(c, cx, btm - 24, sub, 13, anchor="center")

        # Author
        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(gray)
            _draw_mixed(c, cx, btm - 48, author, 11, anchor="center")

        # Bottom decorative line
        line_y = 42 * mm
        c.setStrokeColor(indigo)
        c.setLineWidth(0.5)
        c.line(cx - 30 * mm, line_y, cx + 30 * mm, line_y)

        # Date
        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(gray)
        _draw_mixed(c, cx, line_y - 18, dt, 9, anchor="center")

        c.restoreState()

    def _toc_page(self, c, doc) -> None:
        pg = c.getPageNumber()
        c.setFillColor(white)
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)
        c.setFillColor(self.layout.colors.get("gray", HexColor("#6B7280")))
        c.setFont("CJK", 9)
        c.drawCentredString(self.page_w / 2, 14 * mm, str(pg))

    def _normal_page(self, c, doc) -> None:
        pg = c.getPageNumber()
        c.setFillColor(white)
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)
        c.setFillColor(self.layout.colors.get("gray", HexColor("#6B7280")))
        c.setFont("CJK", 9)
        c.drawCentredString(self.page_w / 2, 14 * mm, str(pg))

    def _build_toc(self, toc_entries: list, page_map: dict | None = None) -> list:
        """Build TOC flowables with level differentiation and page numbers."""
        story: list = []
        indigo = self.layout.colors.get("indigo", HexColor("#312E81"))
        gray = self.layout.colors.get("gray", HexColor("#6B7280"))

        title_style = ParagraphStyle(
            "TOCTitle",
            fontName="CJK",
            fontSize=20,
            leading=28,
            textColor=indigo,
            alignment=TA_CENTER,
            spaceBefore=self.body_h * 0.25,
            spaceAfter=6,
        )
        story.append(Paragraph(_font_wrap("目 录"), title_style))
        story.append(HRule(self.body_w * 0.25, thick=0.8, color=indigo))
        story.append(Spacer(1, 18))

        for title, key, level in toc_entries:
            if level == 0:
                color = indigo
                style = self.ST["toc_chapter"]
            else:
                color = gray
                style = self.ST["toc_section"]

            text_color = _color_hex(color)
            pg = page_map.get(key, "") if page_map else ""
            pg_text = f"  ···· {pg}" if pg else ""
            markup = (
                f'<a href="#{key}" color="{text_color}">'
                f'{_font_wrap(title)}{pg_text}</a>'
            )
            story.append(Paragraph(markup, style))

        return story

    def build(
        self,
        content: list,
        toc_entries: list,
        output_path: str,
    ) -> None:
        """Assemble and write PDF. Two-pass: capture page numbers, then render TOC."""
        import tempfile

        def _make_doc(path):
            cf = Frame(0, 0, self.page_w, self.page_h, id="cover_frame")
            bf = Frame(self.lm, self.bm, self.body_w, self.body_h, id="body_frame")
            d = BaseDocTemplate(
                path, pagesize=A4,
                leftMargin=self.lm, rightMargin=self.rm,
                topMargin=self.tm, bottomMargin=self.bm,
                title=self.cfg.get("title", ""),
                author=self.cfg.get("author", ""),
            )
            d.addPageTemplates([
                PageTemplate(id="cover", frames=[cf], onPage=self._cover_page),
                PageTemplate(id="toc", frames=[bf], onPage=self._toc_page),
                PageTemplate(id="normal", frames=[bf], onPage=self._normal_page),
            ])
            return d

        # Strip leading PageBreak/Spacer from body
        start = 0
        for idx, item in enumerate(content):
            if isinstance(item, (PageBreak, Spacer)):
                start = idx + 1
                continue
            break

        # Deep copy body for pass 1 so pass 2 gets fresh flowables
        import copy
        body = content[start:]
        body_pass1 = copy.deepcopy(body)

        # Pass 1: capture page numbers
        page_map: dict[str, int] = {}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            doc1 = _make_doc(tmp_path)
            doc1.afterFlowable = lambda f: (
                page_map.__setitem__(f.key, doc1.page)
                if isinstance(f, ChapterMark) else None
            )
            p1: list = [NextPageTemplate("toc"), PageBreak(), Spacer(1, 12),
                        NextPageTemplate("normal"), PageBreak()]
            p1.extend(body_pass1)
            doc1.build(p1)
        finally:
            os.unlink(tmp_path)

        # Determine TOC page count by building a trial TOC
        trial = self._build_toc(toc_entries, page_map)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path2 = tmp.name
        toc_pages = 1
        try:
            td = _make_doc(tmp_path2)
            ts: list = [NextPageTemplate("toc"), PageBreak()]
            ts.extend(trial)
            ts.append(NextPageTemplate("normal"))
            ts.append(PageBreak())
            ts.append(Spacer(1, 1))
            td.build(ts)
        except Exception:
            pass
        else:
            toc_pages = max(1, td.page - 1)  # page 1=cover, page 2..N=toc
        finally:
            os.unlink(tmp_path2)

        # Adjust page numbers for final TOC
        offset = toc_pages - 1  # pass1 had 1 TOC page
        corrected = {k: v + offset for k, v in page_map.items()}

        # Pass 2: final PDF with TOC + page numbers
        doc2 = _make_doc(output_path)
        story: list = [NextPageTemplate("toc"), PageBreak()]
        story.extend(self._build_toc(toc_entries, corrected))
        story.append(NextPageTemplate("normal"))
        story.append(PageBreak())
        story.extend(body)
        doc2.build(story)


# ═══════════════════════════════════════════════════════════════════════
# Section 6: CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="Booksmith PDF generator")
    parser.add_argument("project_dir", help="Book project directory")
    parser.add_argument("--output", default=None, help="Output PDF filename")
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

    # Register fonts
    register_fonts()

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

    # Build PDF
    pdf_config = {
        "title": config.get("title", "Untitled"),
        "subtitle": config.get("subtitle", ""),
        "author": config.get("author", ""),
        "date": str(date.today()),
    }

    builder = BooksmithPDF(pdf_config, layout)

    all_story: list = []
    all_toc: list = []
    for f in files:
        md = f.read_text(encoding="utf-8")
        story, toc = parse_manuscript(md, builder.ST, builder.accent_hex)
        all_story.extend(story)
        all_toc.extend(toc)

    output_name = args.output or config.get("delivered_pdf", "ebook.pdf")
    if not output_name.endswith(".pdf"):
        output_name += ".pdf"
    pdf_path = project_dir / output_name

    print(f"Generating PDF -> {pdf_path}")
    builder.build(all_story, all_toc, str(pdf_path))

    size = pdf_path.stat().st_size
    print(f"Done: {pdf_path.name} ({size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
