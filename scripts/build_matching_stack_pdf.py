from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: reportlab. Install it before rebuilding the PDF docs."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"

BG = HexColor("#121212")
SURFACE = HexColor("#1E1E1E")
SURFACE_SOFT = HexColor("#181818")
EMBER = HexColor("#C86844")
PISTACHIO = HexColor("#9BBC5C")
TEXT = HexColor("#ECE6DF")
MUTED = HexColor("#A79B91")
RULE = HexColor("#3A2A24")
CODE_COLOR = "#9BBC5C"


@dataclass(frozen=True)
class DocumentSpec:
    language: str
    source: Path
    output: Path
    header: str


SPECS = {
    "en": DocumentSpec(
        language="en",
        source=DOCS_DIR / "MATCHING_STACK.md",
        output=DOCS_DIR / "MATCHING_STACK.pdf",
        header="ANDY'S LINEMATCHER",
    ),
    "pl": DocumentSpec(
        language="pl",
        source=DOCS_DIR / "MATCHING_STACK_PL.md",
        output=DOCS_DIR / "MATCHING_STACK_PL.pdf",
        header="ANDY'S LINEMATCHER",
    ),
}


BANNER_LINES = [
    "   █████╗ ███╗   ██╗██████╗ ██╗   ██╗",
    "  ██╔══██╗████╗  ██║██╔══██╗╚██╗ ██╔╝",
    "  ███████║██╔██╗ ██║██║  ██║ ╚████╔╝",
    "  ██╔══██║██║╚██╗██║██║  ██║  ╚██╔╝",
    "  ██║  ██║██║ ╚████║██████╔╝   ██║",
    "  ╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝    ╚═╝",
    "",
    "  ██╗     ██╗███╗   ██╗███████╗",
    "  ██║     ██║████╗  ██║██╔════╝",
    "  ██║     ██║██╔██╗ ██║█████╗",
    "  ██║     ██║██║╚██╗██║██╔══╝",
    "  ███████╗██║██║ ╚████║███████╗",
    "  ╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝",
    "",
    "  ███╗   ███╗ █████╗ ████████╗ ██████╗██╗  ██╗███████╗██████╗",
    "  ████╗ ████║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██╔════╝██╔══██╗",
    "  ██╔████╔██║███████║   ██║   ██║     ███████║█████╗  ██████╔╝",
    "  ██║╚██╔╝██║██╔══██║   ██║   ██║     ██╔══██║██╔══╝  ██╔══██╗",
    "  ██║ ╚═╝ ██║██║  ██║   ██║   ╚██████╗██║  ██║███████╗██║  ██║",
    "  ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
]


def register_fonts() -> dict[str, str]:
    families = {
        "sans": {
            "normal": Path(r"C:\Windows\Fonts\segoeui.ttf"),
            "bold": Path(r"C:\Windows\Fonts\segoeuib.ttf"),
            "italic": Path(r"C:\Windows\Fonts\segoeuii.ttf"),
            "boldItalic": Path(r"C:\Windows\Fonts\segoeuiz.ttf"),
        },
        "mono": {
            "normal": Path(r"C:\Windows\Fonts\consola.ttf"),
            "bold": Path(r"C:\Windows\Fonts\consolab.ttf"),
            "italic": Path(r"C:\Windows\Fonts\consolai.ttf"),
            "boldItalic": Path(r"C:\Windows\Fonts\consolaz.ttf"),
        },
    }

    registered = {}
    for family_name, variants in families.items():
        if not all(path.exists() for path in variants.values()):
            continue

        prefix = "SegoeUI" if family_name == "sans" else "Consolas"
        normal_name = prefix
        bold_name = f"{prefix}-Bold"
        italic_name = f"{prefix}-Italic"
        bold_italic_name = f"{prefix}-BoldItalic"

        pdfmetrics.registerFont(TTFont(normal_name, str(variants["normal"])))
        pdfmetrics.registerFont(TTFont(bold_name, str(variants["bold"])))
        pdfmetrics.registerFont(TTFont(italic_name, str(variants["italic"])))
        pdfmetrics.registerFont(TTFont(bold_italic_name, str(variants["boldItalic"])))
        pdfmetrics.registerFontFamily(
            normal_name,
            normal=normal_name,
            bold=bold_name,
            italic=italic_name,
            boldItalic=bold_italic_name,
        )
        registered[family_name] = normal_name

    if "sans" not in registered:
        registered["sans"] = "Helvetica"
    if "mono" not in registered:
        registered["mono"] = "Courier"
    return registered


def build_styles(fonts: dict[str, str]) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}

    styles["title"] = ParagraphStyle(
        "Title",
        parent=base["Heading1"],
        fontName=fonts["sans"],
        fontSize=23.5,
        leading=28,
        textColor=EMBER,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    styles["lead"] = ParagraphStyle(
        "Lead",
        parent=base["BodyText"],
        fontName=fonts["sans"],
        fontSize=11.05,
        leading=16.5,
        textColor=TEXT,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    styles["h2"] = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontName=f"{fonts['sans']}-Bold" if fonts["sans"] != "Helvetica" else "Helvetica-Bold",
        fontSize=15.5,
        leading=20,
        textColor=TEXT,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=2,
    )
    styles["h3"] = ParagraphStyle(
        "H3",
        parent=base["Heading3"],
        fontName=f"{fonts['sans']}-Bold" if fonts["sans"] != "Helvetica" else "Helvetica-Bold",
        fontSize=10.1,
        leading=13.4,
        textColor=PISTACHIO,
        alignment=TA_LEFT,
        spaceBefore=7,
        spaceAfter=3,
    )
    styles["body"] = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName=fonts["sans"],
        fontSize=10.4,
        leading=15.1,
        textColor=TEXT,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet",
        parent=styles["body"],
        leftIndent=14,
        firstLineIndent=0,
        bulletIndent=0,
        spaceAfter=4,
    )
    styles["code"] = ParagraphStyle(
        "Code",
        parent=styles["body"],
        fontName=fonts["mono"],
        fontSize=9,
        leading=13.1,
        textColor=PISTACHIO,
        backColor=SURFACE,
        spaceAfter=0,
    )
    styles["ascii"] = ParagraphStyle(
        "Ascii",
        parent=base["BodyText"],
        fontName=fonts["mono"],
        fontSize=8.35,
        leading=9.2,
        textColor=EMBER,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    styles["header"] = ParagraphStyle(
        "Header",
        parent=base["BodyText"],
        fontName=fonts["mono"],
        fontSize=8.2,
        leading=10,
        textColor=MUTED,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    return styles


def render_inline(text: str, mono_font: str) -> str:
    code_parts = text.split("`")
    rendered: list[str] = []
    for code_index, code_part in enumerate(code_parts):
        bold_parts = code_part.split("**") if code_index % 2 == 0 else [code_part]
        if code_index % 2 == 1:
            rendered.append(
                f"<font name='{mono_font}' color='{CODE_COLOR}'>{html.escape(code_part)}</font>"
            )
            continue

        for bold_index, bold_part in enumerate(bold_parts):
            escaped = html.escape(bold_part)
            if bold_index % 2 == 1:
                rendered.append(f"<b>{escaped}</b>")
            else:
                rendered.append(escaped)
    return "".join(rendered)


def build_panel(paragraph: Paragraph, content_width: float) -> Table:
    panel = Table([[paragraph]], colWidths=[content_width])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE),
                ("LINEBEFORE", (0, 0), (0, -1), 3, EMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return panel


def build_code_block(
    text: str,
    styles: dict[str, ParagraphStyle],
    content_width: float,
) -> Table:
    code = Preformatted(text, styles["code"])
    panel = Table([[code]], colWidths=[content_width])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return panel


def build_ascii_banner(
    styles: dict[str, ParagraphStyle],
    content_width: float,
) -> Table:
    banner = Preformatted("\n".join(BANNER_LINES), styles["ascii"])
    panel = Table([[banner]], colWidths=[content_width])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BG),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE),
                ("LINEBELOW", (0, 0), (-1, -1), 2.1, EMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return panel


def md_to_story(
    md_text: str,
    styles: dict[str, ParagraphStyle],
    content_width: float,
) -> list[object]:
    story: list[object] = []
    in_code = False
    code_lines: list[str] = []
    title_seen = False
    lead_consumed = False
    h2_seen = False

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            story.append(build_code_block("\n".join(code_lines), styles, content_width))
            story.append(Spacer(1, 8))
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
            title_seen = True
            story.append(Spacer(1, 5 * mm))
            story.append(build_ascii_banner(styles, content_width))
            story.append(Spacer(1, 6))
            story.append(Paragraph(line[2:], styles["title"]))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=RULE,
                    spaceBefore=2,
                    spaceAfter=10,
                )
            )
            continue

        if line.startswith("## "):
            flush_code()
            h2_seen = True
            story.append(Spacer(1, 6))
            story.append(
                Paragraph(
                    render_inline(line[3:], styles["code"].fontName),
                    styles["h2"],
                )
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.6,
                    color=RULE,
                    spaceBefore=2,
                    spaceAfter=8,
                )
            )
            continue

        if line.startswith("### "):
            flush_code()
            story.append(
                Paragraph(
                    render_inline(line[4:], styles["code"].fontName),
                    styles["h3"],
                )
            )
            continue

        if line.startswith("- "):
            flush_code()
            story.append(
                Paragraph(
                    f"&bull; {render_inline(line[2:], styles['code'].fontName)}",
                    styles["bullet"],
                )
            )
            continue

        if re.match(r"^\d+\.\s+", line):
            flush_code()
            story.append(
                Paragraph(
                    render_inline(line, styles["code"].fontName),
                    styles["bullet"],
                )
            )
            continue

        paragraph = Paragraph(render_inline(line, styles["code"].fontName), styles["body"])
        if title_seen and not lead_consumed and not h2_seen:
            story.append(
                build_panel(
                    Paragraph(
                        render_inline(line, styles["code"].fontName),
                        styles["lead"],
                    ),
                    content_width,
                )
            )
            story.append(Spacer(1, 9))
            lead_consumed = True
            continue

        story.append(paragraph)

    flush_code()
    return story


def draw_page(spec: DocumentSpec, fonts: dict[str, str]):
    def renderer(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        canvas.setStrokeColor(EMBER)
        canvas.setLineWidth(1)
        canvas.line(18 * mm, height - 18 * mm, width - 18 * mm, height - 18 * mm)
        canvas.setFont(fonts["mono"], 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 14 * mm, spec.header)
        canvas.drawRightString(width - 18 * mm, 12 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    return renderer


def build_pdf(spec: DocumentSpec, fonts: dict[str, str]) -> Path:
    if not spec.source.exists():
        raise FileNotFoundError(f"Source markdown not found: {spec.source}")

    styles = build_styles(fonts)
    md_text = spec.source.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(spec.output),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
        title=spec.source.stem,
        author="Codex",
    )
    story = md_to_story(md_text, styles, doc.width)
    renderer = draw_page(spec, fonts)
    doc.build(story, onFirstPage=renderer, onLaterPages=renderer)
    return spec.output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Andy's LineMatcher matching stack PDFs."
    )
    parser.add_argument(
        "--lang",
        choices=["all", "en", "pl"],
        default="all",
        help="Which document set to build. Default: all.",
    )
    return parser.parse_args()


def selected_specs(lang: str) -> list[DocumentSpec]:
    if lang == "all":
        return [SPECS["en"], SPECS["pl"]]
    return [SPECS[lang]]


def main() -> int:
    args = parse_args()
    fonts = register_fonts()
    outputs: list[Path] = []

    for spec in selected_specs(args.lang):
        outputs.append(build_pdf(spec, fonts))

    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
