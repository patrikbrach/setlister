import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Unicode font setup ────────────────────────────────────
# Try common TTF locations (Streamlit Cloud / Ubuntu / Mac / Windows)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]

_UNICODE_FONT = "Helvetica"  # fallback to built-in

for _path in _FONT_CANDIDATES:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont("UniFont", _path))
            _UNICODE_FONT = "UniFont"
        except Exception:
            pass
        break


def _safe(text: str) -> str:
    """If we couldn't load a Unicode font, strip non-Latin-1 chars."""
    if _UNICODE_FONT != "Helvetica":
        return text
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _style(name, font=None, size=11, leading=16, bold=False, color=colors.black, space_before=0, space_after=2):
    f = font or _UNICODE_FONT
    return ParagraphStyle(
        name,
        fontName=f,
        fontSize=size,
        leading=leading,
        textColor=color,
        spaceBefore=space_before,
        spaceAfter=space_after,
    )


def generate_setlist_pdf(result: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    gray = colors.HexColor("#666666")
    light_gray = colors.HexColor("#cccccc")
    amber = colors.HexColor("#b07800")
    link_color = colors.HexColor("#4444cc")

    s_artist = _style("artist", size=22, leading=26, bold=True)
    s_meta = _style("meta", size=11, leading=14, color=gray, space_after=4)
    s_num = _style("num", size=10, leading=14, color=gray)
    s_song = _style("song", size=11, leading=15)
    s_info = _style("info", size=9, leading=12, color=gray)
    s_encore = _style("encore", size=9, leading=12, color=amber, space_before=6, space_after=6)
    s_url = _style("url", size=8, leading=11, color=link_color, space_before=6)

    story = []

    story.append(Paragraph(_safe(result.get("artist", "")), s_artist))

    meta = f"{result.get('date', '')}  -  {result.get('venue', '')}"
    story.append(Paragraph(_safe(meta), s_meta))
    story.append(HRFlowable(width="100%", thickness=0.5, color=light_gray, spaceAfter=8))

    songs = result.get("songs", [])
    encore_breaks = set(result.get("encore_breaks", []))

    for j, song in enumerate(songs):
        if j in encore_breaks:
            story.append(Paragraph("— Encore —", s_encore))

        # Number + name on same line using a table-like trick with tabs
        song_line = f'<font color="#aaaaaa">{song["order"]}.</font>  {_safe(song["name"])}'
        story.append(Paragraph(song_line, s_song))

        if song.get("info"):
            story.append(Paragraph(f'({_safe(song["info"])})', s_info))

    url = result.get("setlist_url", "")
    if url:
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=light_gray))
        story.append(Paragraph(_safe(url), s_url))

    doc.build(story)
    return buf.getvalue()


def safe_filename(artist: str, date: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in f"{artist} {date}")
    return safe.strip().replace(" ", "_") + ".pdf"
