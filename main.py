import asyncio
import io
import json
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

from excel_reader import parse_excel
from setlist_client import fetch_setlist
from pdf_generator import generate_setlist_pdf, safe_filename

API_KEY = os.environ.get("SETLIST_API_KEY", "")

_rows: dict[int, dict] = {}
_results: dict[int, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Setlister", lifespan=lifespan)

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")

    contents = await file.read()
    try:
        rows = parse_excel(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    _rows.clear()
    _results.clear()
    for row in rows:
        _rows[row["id"]] = row

    return {"rows": rows, "total": len(rows)}


@app.get("/fetch/{row_id}")
async def fetch_row(row_id: int):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="SETLIST_API_KEY not configured.")
    if row_id not in _rows:
        raise HTTPException(status_code=404, detail="Unknown row id.")

    row = _rows[row_id]
    async with httpx.AsyncClient() as client:
        result = await fetch_setlist(
            client=client,
            api_key=API_KEY,
            row_id=row_id,
            artist=row["artist"],
            date=row["date"],
            venue=row.get("venue"),
        )

    _results[row_id] = result
    return result


@app.get("/pdf/{row_id}")
async def download_pdf(row_id: int):
    result = _results.get(row_id)
    if not result or result.get("status") != "found":
        raise HTTPException(status_code=404, detail="No setlist result found for this row.")

    pdf_bytes = generate_setlist_pdf(result)
    filename = safe_filename(result["artist"], result["date"])

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export")
async def export(results: str = Query(...)):
    import openpyxl
    from openpyxl import Workbook

    try:
        data = json.loads(results)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in results parameter.")

    wb = Workbook()
    ws = wb.active
    ws.title = "Setlists"
    ws.append(["Artist", "Date", "Venue", "Songs", "Setlist.fm URL"])

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
