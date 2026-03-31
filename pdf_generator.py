import io
import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Unicode font setup ────────────────────────────────────
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]
_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "C:/Windows/Fonts/cour.ttf",
]

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_MONO = "Courier"

for _path in _FONT_CANDIDATES:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont("UniFont", _path))
            _FONT = "UniFont"
            _FONT_BOLD = "UniFont"
        except Exception:
            pass
        break

for _path in _MONO_CANDIDATES:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont("UniMono", _path))
            _MONO = "UniMono"
        except Exception:
            pass
        break


def _safe(text: str) -> str:
    if _FONT != "Helvetica":
        return text
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _s(name, font=None, size=10, leading=14, color=colors.black, bold=False,
       space_before=0, space_after=2):
    return ParagraphStyle(
        name,
        fontName=font or (_FONT_BOLD if bold else _FONT),
        fontSize=size,
        leading=leading,
        textColor=color,
        spaceBefore=space_before,
        spaceAfter=space_after,
    )


_gray = colors.HexColor("#555555")
_light_gray = colors.HexColor("#cccccc")
_pale = colors.HexColor("#f5f5f5")
_amber = colors.HexColor("#996600")
_link = colors.HexColor("#3333bb")


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 8)
    canvas.setFillColor(_gray)
    footer = f"Sida {doc.page}  ·  Genererad {date.today().strftime('%Y-%m-%d')}"
    canvas.drawCentredString(A4[0] / 2, 12 * mm, footer)
    canvas.restoreState()


def generate_setlist_pdf(results: list[dict]) -> bytes:
    """Generate a multi-concert PDF with ISRC column. Takes a list of result dicts."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
    )

    story = []

    for idx, result in enumerate(results):
        if result.get("status") != "found":
            continue

        section = _build_concert_section(result)
        story.append(KeepTogether(section[:4]))  # keep header + first few rows together
        story.extend(section[4:])

        if idx < len(results) - 1:
            story.append(PageBreak())

    if not story:
        story.append(Paragraph("Inga hittade setlister att exportera.", _s("none")))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buf.getvalue()


def _build_concert_section(result: dict) -> list:
    section = []

    # Artist heading
    section.append(Paragraph(_safe(result.get("artist", "")), _s("artist", size=18, leading=22, bold=True, space_after=2)))

    meta = f"{result.get('date', '')}  ·  {result.get('venue', '')}"
    section.append(Paragraph(_safe(meta), _s("meta", size=10, color=_gray, space_after=3)))

    url = result.get("setlist_url", "")
    if url:
        section.append(Paragraph(f'<link href="{url}" color="#3333bb">{_safe(url)}</link>',
                                  _s("url", size=8, color=_link, space_after=6)))

    section.append(HRFlowable(width="100%", thickness=0.5, color=_light_gray, spaceAfter=4))

    # Song table
    songs = result.get("songs", [])
    encore_breaks = set(result.get("encore_breaks", []))

    table_data = [
        [
            Paragraph("#", _s("th", size=8, bold=True, color=_gray)),
            Paragraph("Låt", _s("th", size=8, bold=True, color=_gray)),
            Paragraph("ISRC", _s("th", size=8, bold=True, color=_gray, font=_MONO)),
        ]
    ]
    row_styles = []

    for j, song in enumerate(songs):
        if j in encore_breaks:
            encore_row = [
                Paragraph("", _s("enc")),
                Paragraph("— Encore —", _s("enc", size=8, color=_amber)),
                Paragraph("", _s("enc")),
            ]
            table_data.append(encore_row)
            row_styles.append(("BACKGROUND", (0, len(table_data) - 1), (-1, len(table_data) - 1), colors.HexColor("#fff8e8")))

        isrc = song.get("isrc") or "—"
        table_data.append([
            Paragraph(str(song["order"]), _s("num", size=9, color=_gray)),
            Paragraph(_safe(song["name"]), _s("sname", size=9)),
            Paragraph(isrc, _s("isrc", size=8, font=_MONO, color=_gray if isrc == "—" else colors.black)),
        ])

        if j % 2 == 0:
            row_styles.append(("BACKGROUND", (0, len(table_data) - 1), (-1, len(table_data) - 1), _pale))

    col_widths = [10 * mm, 110 * mm, 40 * mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

    base_style = [
        ("GRID", (0, 0), (-1, 0), 0.4, _light_gray),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, _light_gray),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
    ]
    tbl.setStyle(TableStyle(base_style + row_styles))
    section.append(tbl)

    return section


def generate_single_pdf(result: dict) -> bytes:
    """Generate a PDF for a single concert."""
    return generate_setlist_pdf([result])


def safe_filename(artist: str, date: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in f"{artist} {date}")
    return safe.strip().replace(" ", "_") + ".pdf"
