import io
import time

import streamlit as st
import openpyxl

from excel_reader import parse_excel
from setlist_client import fetch_setlist_sync
from spotify_client import SpotifyClient
from pdf_generator import generate_setlist_pdf, generate_single_pdf, safe_filename

st.set_page_config(page_title="Setlist Lookup", page_icon="🎵", layout="centered")
st.title("🎵 Setlist Lookup")

# ── Credentials ────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1.5, 1.5])
with col1:
    api_key = st.text_input("setlist.fm API-nyckel", type="password", placeholder="API-nyckel")
with col2:
    spotify_id = st.text_input("Spotify Client ID", placeholder="Client ID")
with col3:
    spotify_secret = st.text_input("Spotify Client Secret", type="password", placeholder="Client Secret")

use_spotify = bool(spotify_id and spotify_secret)

# ── File upload ────────────────────────────────────────────
uploaded = st.file_uploader("Ladda upp Excel-fil (.xlsx)", type=["xlsx"])

run = st.button("Hämta setlister", disabled=not (api_key and uploaded))

if not run:
    st.stop()

# ── Validate Spotify credentials ───────────────────────────
spotify: SpotifyClient | None = None
if use_spotify:
    try:
        spotify = SpotifyClient(spotify_id, spotify_secret)
        spotify.validate()
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Kunde inte ansluta till Spotify: {e}")
        st.stop()

# ── Parse Excel ────────────────────────────────────────────
try:
    rows = parse_excel(uploaded.read())
except ValueError as e:
    st.error(str(e))
    st.stop()

isrc_label = " · hämtar ISRC via Spotify" if use_spotify else ""
st.write(f"Hittade **{len(rows)}** rader. Hämtar setlister{isrc_label}…")

progress = st.progress(0)
status = st.empty()

results = []
isrc_found_count = 0
placeholders = [st.empty() for _ in rows]

# ── Fetch loop ─────────────────────────────────────────────
for i, row in enumerate(rows):
    status.text(f"{i} / {len(rows)} klara" + (f"  ·  {isrc_found_count} låtar med ISRC" if use_spotify else ""))

    result = fetch_setlist_sync(
        api_key=api_key,
        row_id=row["id"],
        artist=row["artist"],
        date=row["date"],
        venue=row.get("venue"),
    )

    # Enrich songs with ISRC
    if result["status"] == "found" and spotify:
        for song in result.get("songs", []):
            isrc = spotify.get_isrc(result["artist"], song["name"])
            song["isrc"] = isrc
            song["isrc_status"] = "found" if isrc else "not_found"
            if isrc:
                isrc_found_count += 1
        result["isrc_enriched"] = True

    results.append(result)

    # ── Render card ────────────────────────────────────────
    with placeholders[i].container():
        if result["status"] == "found":
            songs = result.get("songs", [])
            encore_breaks = set(result.get("encore_breaks", []))
            label = f"✅ {result['artist']} – {result['date']} – {result.get('venue', '')}"

            with st.expander(label):
                if songs:
                    # Build table rows
                    header = "| # | Låt |" + (" ISRC |" if use_spotify else "")
                    sep = "|---|---|" + ("---|" if use_spotify else "")
                    lines = [header, sep]
                    for j, song in enumerate(songs):
                        if j in encore_breaks:
                            lines.append(f"| | *— Encore —* |" + (" |" if use_spotify else ""))
                        isrc_cell = f" `{song['isrc']}` |" if use_spotify else ""
                        if use_spotify and not song.get("isrc"):
                            isrc_cell = " — |"
                        lines.append(f"| {song['order']} | {song['name']} |{isrc_cell}")
                    st.markdown("\n".join(lines))
                else:
                    st.markdown("*Tom setlist*")

                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if result.get("setlist_url"):
                        st.markdown(f"[↗ Öppna på setlist.fm]({result['setlist_url']})")
                with btn_col2:
                    pdf_bytes = generate_single_pdf(result)
                    st.download_button(
                        label="⬇ PDF",
                        data=pdf_bytes,
                        file_name=safe_filename(result["artist"], result["date"]),
                        mime="application/pdf",
                        key=f"pdf_{result['id']}",
                    )

        elif result["status"] == "not_found":
            st.warning(f"❌ {result['artist']} – {result['date']} – Ingen setlist hittades")
        else:
            msg = result.get("message", "Okänt fel")
            st.error(f"⚠️ {result.get('artist', '')} – {result['date']} – {msg}")
            if "401" in msg:
                status.text("Ogiltig API-nyckel – avbryter.")
                progress.progress(1.0)
                st.stop()

    progress.progress((i + 1) / len(rows))

    if i < len(rows) - 1:
        time.sleep(0.5)

# ── Done ───────────────────────────────────────────────────
final_status = f"✅ {len(rows)} / {len(rows)} klara"
if use_spotify:
    final_status += f"  ·  {isrc_found_count} låtar med ISRC"
status.text(final_status)

# ── Export buttons ─────────────────────────────────────────
found_results = [r for r in results if r.get("status") == "found"]

exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    if found_results:
        all_pdf = generate_setlist_pdf(found_results)
        st.download_button(
            label="⬇ Exportera alla → PDF",
            data=all_pdf,
            file_name="setlists.pdf",
            mime="application/pdf",
        )

with exp_col2:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Setlists"
    ws.append(["Artist", "Datum", "Venue", "Antal låtar", "Setlist.fm URL"])
    for r in results:
        ws.append([
            r.get("artist", ""),
            r.get("date", ""),
            r.get("venue", ""),
            len(r.get("songs", [])) if r["status"] == "found" else 0,
            r.get("setlist_url", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    st.download_button(
        label="⬇ Exportera alla → Excel",
        data=buf,
        file_name="setlists.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
