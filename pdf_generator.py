import io
from fpdf import FPDF


def generate_setlist_pdf(result: dict) -> bytes:
    """Generate a PDF for a single found setlist. Returns PDF bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Header ─────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, result.get("artist", ""), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    meta = f"{result.get('date', '')}  •  {result.get('venue', '')}"
    pdf.cell(0, 8, meta, new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.5)
    pdf.ln(2)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── Song list ───────────────────────────────────────────
    songs = result.get("songs", [])
    encore_breaks = set(result.get("encore_breaks", []))
    pdf.set_text_color(0, 0, 0)

    for j, song in enumerate(songs):
        if j in encore_breaks:
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(150, 100, 0)
            pdf.cell(0, 6, "— Encore —", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        pdf.set_font("Helvetica", "", 11)
        num = f"{song['order']}."
        name = song["name"]
        info = f"  ({song['info']})" if song.get("info") else ""

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(10, 7, num)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 7, name, new_x="LMARGIN", new_y="NEXT")

        if info:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(10, 5, "")
            pdf.cell(0, 5, info.strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

    # ── Footer ──────────────────────────────────────────────
    url = result.get("setlist_url", "")
    if url:
        pdf.ln(6)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 100, 200)
        pdf.cell(0, 6, url)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def safe_filename(artist: str, date: str) -> str:
    """Generate a safe filename from artist and date."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in f"{artist} {date}")
    return safe.strip().replace(" ", "_") + ".pdf"
