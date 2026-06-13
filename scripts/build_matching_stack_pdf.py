from __future__ import annotations

import html
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: reportlab. Install it before rebuilding docs/MATCHING_STACK.pdf."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = ROOT / "docs" / "MATCHING_STACK.md"
OUTPUT_PDF = ROOT / "docs" / "MATCHING_STACK.pdf"

BG = HexColor("#121212")
SURFACE = HexColor("#1E1E1E")
EMBER = HexColor("#C86844")
PISTACHIO = HexColor("#9BBC5C")
TEXT = HexColor("#ECE6DF")
MUTED = HexColor("#A79B91")
RULE = HexColor("#3A2A24")
CODE_COLOR = "#9BBC5C"


def build_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["title"] = ParagraphStyle(
        "Title",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=EMBER,
        spaceAfter=10,
        alignment=TA_LEFT,
    )
    styles["h2"] = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=TEXT,
        spaceBefore=12,
        spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=TEXT,
        spaceAfter=6,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet",
        parent=styles["body"],
        leftIndent=12,
        firstLineIndent=0,
        bulletIndent=0,
    )
    styles["mono"] = ParagraphStyle(
        "Mono",
        parent=styles["body"],
        fontName="Courier",
        fontSize=9,
        leading=13,
        textColor=PISTACHIO,
        backColor=SURFACE,
        borderPadding=8,
        borderColor=RULE,
        borderWidth=1,
        borderRadius=0,
        spaceBefore=4,
        spaceAfter=10,
    )
    styles["label"] = ParagraphStyle(
        "Label",
        parent=styles["body"],
        fontName="Courier-Bold",
        fontSize=8.5,
        leading=12,
        textColor=MUTED,
        spaceAfter=2,
    )
    return styles


def draw_bg(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    canvas.setStrokeColor(EMBER)
    canvas.setLineWidth(1)
    canvas.line(16 * mm, height - 18 * mm, width - 16 * mm, height - 18 * mm)
    canvas.setFont("Courier", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(16 * mm, height - 14 * mm, "ANDY'S LINEMATCHER :: MATCHING STACK")
    canvas.drawRightString(width - 16 * mm, 12 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def md_to_story(md_text: str):
    styles = build_styles()
    story = []
    in_code = False
    code_lines: list[str] = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["mono"]))
            code_lines = []

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                flush_code()
            in_code = not in_code
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            story.append(Spacer(1, 4))
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["title"]))
            story.append(Paragraph("dark stack / deterministic fuzzy matching", styles["label"]))
            story.append(Spacer(1, 6))
            continue

        if line.startswith("## "):
            story.append(Spacer(1, 6))
            story.append(Paragraph(line[3:], styles["h2"]))
            continue

        if line.startswith("### "):
            story.append(Paragraph(line[4:], styles["label"]))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"&bull; {escape_inline(line[2:])}", styles["bullet"]))
            continue

        if line[0].isdigit() and ". " in line[:4]:
            story.append(Paragraph(escape_inline(line), styles["bullet"]))
            continue

        story.append(Paragraph(escape_inline(line), styles["body"]))

    flush_code()
    return story


def escape_inline(text: str) -> str:
    parts = text.split("`")
    rendered: list[str] = []
    for index, part in enumerate(parts):
        escaped = html.escape(part)
        if index % 2 == 1:
            rendered.append(
                f"<font name='Courier' color='{CODE_COLOR}'>{escaped}</font>"
            )
        else:
            rendered.append(escaped)
    return "".join(rendered)


def build_pdf() -> Path:
    md_text = SOURCE_MD.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
    )
    story = md_to_story(md_text)
    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    return OUTPUT_PDF


if __name__ == "__main__":
    output = build_pdf()
    print(output)
