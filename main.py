import asyncio
import io
import json
import os
import webbrowser
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from excel_reader import parse_excel
from setlist_client import fetch_setlist

# API key pre-configured via environment variable (optional)
_BAKED_API_KEY = os.getenv("SETLIST_API_KEY", "").strip()

# In-memory row storage keyed by upload session
_rows: dict[int, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Setlist Lookup", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


@app.get("/config")
async def config():
    """Tell the frontend whether an API key is pre-configured on the server."""
    return {"api_key_baked": bool(_BAKED_API_KEY)}


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    api_key: str = Form(default=""),
):
    """Parse uploaded xlsx and return list of rows."""
    effective_key = api_key.strip() or _BAKED_API_KEY
    if not effective_key:
        raise HTTPException(status_code=400, detail="Ingen API-nyckel angiven.")

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Endast .xlsx-filer stöds.")

    contents = await file.read()
    try:
        rows = parse_excel(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Store rows globally (simple single-user local app)
    _rows.clear()
    for row in rows:
        _rows[row["id"]] = row

    return {"rows": rows, "total": len(rows)}


@app.get("/fetch/{row_id}")
async def fetch_row(
    row_id: int,
    api_key: str = Query(default=""),
):
    """Fetch setlist for a single row by id."""
    effective_key = api_key.strip() or _BAKED_API_KEY
    if not effective_key:
        raise HTTPException(status_code=400, detail="Ingen API-nyckel angiven.")

    if row_id not in _rows:
        raise HTTPException(status_code=404, detail="Okänt rad-id.")

    row = _rows[row_id]
    async with httpx.AsyncClient() as client:
        result = await fetch_setlist(
            client=client,
            api_key=effective_key,
            row_id=row_id,
            artist=row["artist"],
            date=row["date"],
            venue=row.get("venue"),
        )
    return result


@app.get("/export")
async def export(results: str = Query(...)):
    """
    Generate an xlsx from JSON-encoded results array.
    results is a JSON string: [{artist, date, venue, songs, setlist_url, status}, ...]
    """
    import openpyxl
    from openpyxl import Workbook

    try:
        data = json.loads(results)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ogiltig JSON i results-parametern.")

    wb = Workbook()
    ws = wb.active
    ws.title = "Setlists"
    ws.append(["Artist", "Datum", "Venue", "Antal låtar", "Setlist.fm URL"])

    for item in data:
        if item.get("status") == "found":
            songs = item.get("songs", [])
            ws.append([
                item.get("artist", ""),
                item.get("date", ""),
                item.get("venue", ""),
                len(songs),
                item.get("setlist_url", ""),
            ])
        else:
            ws.append([
                item.get("artist", ""),
                item.get("date", ""),
                item.get("venue", ""),
                0,
                "",
            ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=setlists.xlsx"},
    )


if __name__ == "__main__":
    webbrowser.open("http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
