from __future__ import annotations

import argparse
import html
import json
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
    from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
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
STATS_PATH = DOCS_DIR / "MATCHING_REAL_DATA.json"

BG = HexColor("#121212")
SURFACE = HexColor("#1E1E1E")
SURFACE_SOFT = HexColor("#181818")
EMBER = HexColor("#C86844")
PISTACHIO = HexColor("#9BBC5C")
TEXT = HexColor("#ECE6DF")
MUTED = HexColor("#A79B91")
RULE = HexColor("#3A2A24")
CODE_COLOR = "#9BBC5C"
CHART_BLUE = HexColor("#5AA7FF")
CHART_GOLD = HexColor("#E1B04D")
CHART_RED = HexColor("#D26A4D")
CHART_GREEN = HexColor("#9BBC5C")
CHART_YELLOW = HexColor("#E0C15A")


@dataclass(frozen=True)
class DocumentSpec:
    language: str
    source: Path
    output: Path
    header: str


@dataclass(frozen=True)
class StatsBundle:
    source_workbook: str
    thresholds: dict[str, float]
    examples: list[dict[str, object]]
    decision_points: list[dict[str, object]]


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


def load_stats_bundle() -> StatsBundle | None:
    if not STATS_PATH.exists():
        return None

    raw = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    return StatsBundle(
        source_workbook=str(raw.get("source_workbook") or ""),
        thresholds={
            "auto": float(raw.get("thresholds", {}).get("auto", 90.0)),
            "review": float(raw.get("thresholds", {}).get("review", 75.0)),
            "margin": float(raw.get("thresholds", {}).get("margin", 3.0)),
        },
        examples=list(raw.get("examples") or []),
        decision_points=list(raw.get("decision_points") or []),
    )


def truncate_label(value: str, limit: int = 26) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def compact_label_text(value: str, limit: int = 38) -> str:
    if len(value) <= limit:
        return value
    head = max(8, (limit - 3) // 2)
    tail = max(6, limit - 3 - head)
    return value[:head] + "..." + value[-tail:]


def chart_panel(drawing: Drawing, content_width: float) -> Table:
    panel = Table([[drawing]], colWidths=[content_width])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.8, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return panel


def build_fuzzy_chart(bundle: StatsBundle, fonts: dict[str, str], content_width: float) -> Table | None:
    examples = bundle.examples[:6]
    if not examples:
        return None

    width = max(int(content_width - 20), 360)
    label_width = 214
    row_gap = 36
    top_margin = 86
    bottom_margin = 20
    height = top_margin + len(examples) * row_gap + bottom_margin
    drawing = Drawing(width, height)
    mono = fonts["mono"]
    sans = fonts["sans"]

    drawing.add(String(0, height - 18, "Real data / selected fuzzy matches", fontName=mono, fontSize=8, fillColor=MUTED))
    drawing.add(String(0, height - 34, f"Workbook: {bundle.source_workbook}", fontName=sans, fontSize=8.5, fillColor=MUTED))

    bar_left = label_width + 18
    bar_width = width - bar_left - 28
    scale = bar_width / 100.0
    colors = [
        ("seq", CHART_BLUE, "sequence"),
        ("tok", CHART_GOLD, "token_sort"),
        ("sub", CHART_RED, "subset"),
        ("fin", CHART_GREEN, "final"),
    ]

    legend_x = bar_left
    for index, (short_label, color, _) in enumerate(colors):
        legend_left = legend_x + index * 54
        drawing.add(Rect(legend_left, height - 50, 10, 10, fillColor=color, strokeColor=color))
        drawing.add(String(legend_left + 14, height - 48, short_label, fontName=mono, fontSize=7.3, fillColor=TEXT))

    for tick in range(0, 101, 20):
        x = bar_left + tick * scale
        drawing.add(Line(x, 14, x, height - top_margin + 18, strokeColor=RULE, strokeWidth=0.5))
        drawing.add(String(x - 6, 3, str(tick), fontName=mono, fontSize=7, fillColor=MUTED))

    for row_index, example in enumerate(examples):
        base_y = height - top_margin - row_index * row_gap
        label = compact_label_text(str(example.get("label") or ""), 38)
        drawing.add(Rect(0, base_y - 8, label_width - 10, 18, fillColor=BG, strokeColor=None))
        drawing.add(String(0, base_y + 1, label, fontName=sans, fontSize=7.7, fillColor=TEXT))
        values = {
            "sequence": float(example.get("sequence") or 0.0),
            "token_sort": float(example.get("token_sort") or 0.0),
            "subset": float(example.get("subset") or 0.0),
            "final": float(example.get("final") or 0.0),
        }
        for offset, (_, color, key) in enumerate(colors):
            y = base_y - 4 - offset * 6
            drawing.add(Rect(bar_left, y, values[key] * scale, 4.2, fillColor=color, strokeColor=color))
        drawing.add(String(bar_left + bar_width + 8, base_y - 12, f"{values['final']:.1f}", fontName=mono, fontSize=7.3, fillColor=TEXT))
        drawing.add(Line(0, base_y - 16, width, base_y - 16, strokeColor=SURFACE, strokeWidth=0.5))

    return chart_panel(drawing, content_width)


def build_decision_chart(bundle: StatsBundle, fonts: dict[str, str], content_width: float) -> Table | None:
    all_points = bundle.decision_points
    if not all_points:
        return None

    ranked = sorted(
        all_points,
        key=lambda point: (
            float(point.get("margin") or 0.0),
            -float(point.get("score") or 0.0),
        ),
    )
    points = ranked[:5]
    strongest = max(
        all_points,
        key=lambda point: (
            float(point.get("margin") or 0.0),
            float(point.get("score") or 0.0),
        ),
    )
    if strongest not in points:
        points.append(strongest)

    width = max(int(content_width - 20), 360)
    label_width = 270
    row_gap = 42
    top_margin = 88
    bottom_margin = 24
    height = top_margin + len(points) * row_gap + bottom_margin
    drawing = Drawing(width, height)
    mono = fonts["mono"]
    sans = fonts["sans"]

    chart_left = label_width + 18
    chart_bottom = 20
    chart_width = width - chart_left - 64
    chart_height = len(points) * row_gap + 4

    drawing.add(String(0, height - 18, "Real data / top score vs second score", fontName=mono, fontSize=8, fillColor=MUTED))
    drawing.add(String(0, height - 34, f"Workbook: {bundle.source_workbook}", fontName=sans, fontSize=8.5, fillColor=MUTED))

    for tick in range(0, 101, 20):
        x = chart_left + chart_width * (tick / 100.0)
        drawing.add(Line(x, chart_bottom, x, chart_bottom + chart_height, strokeColor=RULE, strokeWidth=0.5))
        drawing.add(String(x - 6, 4, str(tick), fontName=mono, fontSize=7, fillColor=MUTED))

    review_x = chart_left + chart_width * (bundle.thresholds["review"] / 100.0)
    auto_x = chart_left + chart_width * (bundle.thresholds["auto"] / 100.0)
    drawing.add(Line(review_x, chart_bottom, review_x, chart_bottom + chart_height, strokeColor=CHART_YELLOW, strokeWidth=0.8))
    drawing.add(Line(auto_x, chart_bottom, auto_x, chart_bottom + chart_height, strokeColor=CHART_GREEN, strokeWidth=1.0))
    drawing.add(String(review_x - 12, height - 50, "75", fontName=mono, fontSize=7, fillColor=CHART_YELLOW))
    drawing.add(String(review_x - 18, height - 60, "review", fontName=mono, fontSize=6.8, fillColor=CHART_YELLOW))
    drawing.add(String(auto_x - 10, height - 50, "90", fontName=mono, fontSize=7, fillColor=CHART_GREEN))
    drawing.add(String(auto_x - 12, height - 60, "auto", fontName=mono, fontSize=6.8, fillColor=CHART_GREEN))

    status_colors = {
        "auto_matched": CHART_GREEN,
        "review_needed": CHART_YELLOW,
        "unmatched": CHART_RED,
        "manual_matched": CHART_BLUE,
    }
    legend_items = [("second", CHART_BLUE), ("top", CHART_GREEN), ("margin", MUTED)]
    for index, (label, color) in enumerate(legend_items):
        legend_left = index * 76
        drawing.add(Circle(legend_left + 4, height - 46, 4, fillColor=color, strokeColor=color))
        drawing.add(String(legend_left + 12, height - 49, label, fontName=mono, fontSize=7.2, fillColor=TEXT))

    for row_index, point in enumerate(points):
        row_y = height - top_margin - row_index * row_gap
        source_label = compact_label_text(
            str(point.get("source") or point.get("label") or ""),
            34,
        )
        top_label = compact_label_text(str(point.get("top_candidate") or "/"), 34)
        second_label = compact_label_text(str(point.get("second_candidate") or "/"), 34)
        score = float(point.get("score") or 0.0)
        second_score = float(point.get("second_score") or 0.0)
        margin = float(point.get("margin") or 0.0)
        top_x = chart_left + chart_width * (score / 100.0)
        second_x = chart_left + chart_width * (second_score / 100.0)
        top_color = status_colors.get(str(point.get("status") or ""), CHART_BLUE)

        drawing.add(Rect(0, row_y - 18, label_width - 10, 30, fillColor=BG, strokeColor=None))
        drawing.add(String(0, row_y + 8, source_label, fontName=sans, fontSize=7.5, fillColor=TEXT))
        drawing.add(String(0, row_y - 2, f"top: {top_label}", fontName=mono, fontSize=6.8, fillColor=top_color))
        drawing.add(String(0, row_y - 12, f"second: {second_label}", fontName=mono, fontSize=6.6, fillColor=CHART_BLUE))
        drawing.add(Line(second_x, row_y, top_x, row_y, strokeColor=MUTED, strokeWidth=1.0))
        drawing.add(Circle(second_x, row_y, 3.1, fillColor=CHART_BLUE, strokeColor=CHART_BLUE))
        drawing.add(Circle(top_x, row_y, 3.4, fillColor=top_color, strokeColor=top_color))
        drawing.add(String(chart_left + chart_width + 8, row_y - 3, f"m={margin:.1f}", fontName=mono, fontSize=7.0, fillColor=TEXT))
        drawing.add(Line(0, row_y - 21, width, row_y - 21, strokeColor=SURFACE, strokeWidth=0.5))

    drawing.add(String(chart_left + chart_width / 2 - 14, 4, "score", fontName=mono, fontSize=7.5, fillColor=MUTED))
    return chart_panel(drawing, content_width)


def md_to_story(
    md_text: str,
    styles: dict[str, ParagraphStyle],
    content_width: float,
    fonts: dict[str, str],
    stats_bundle: StatsBundle | None,
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
            heading = line[3:].strip()
            story.append(Spacer(1, 6))
            story.append(
                Paragraph(
                    render_inline(heading, styles["code"].fontName),
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
            if stats_bundle and heading in {"Wynik końcowy fuzzy", "Final fuzzy score"}:
                chart = build_fuzzy_chart(stats_bundle, fonts, content_width)
                if chart:
                    story.append(chart)
                    story.append(Spacer(1, 8))
            if stats_bundle and heading in {"Reguła decyzji", "Decision rules"}:
                chart = build_decision_chart(stats_bundle, fonts, content_width)
                if chart:
                    story.append(chart)
                    story.append(Spacer(1, 8))
            continue

        if line.startswith("### "):
            flush_code()
            heading = line[4:].strip()
            story.append(
                Paragraph(
                    render_inline(heading, styles["code"].fontName),
                    styles["h3"],
                )
            )
            if stats_bundle and heading in {"Wynik końcowy fuzzy", "Final fuzzy score"}:
                chart = build_fuzzy_chart(stats_bundle, fonts, content_width)
                if chart:
                    story.append(chart)
                    story.append(Spacer(1, 8))
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
    stats_bundle = load_stats_bundle()
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
    story = md_to_story(md_text, styles, doc.width, fonts, stats_bundle)
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
