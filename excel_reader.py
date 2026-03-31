import pandas as pd
from datetime import datetime
from typing import Optional
import re


ARTIST_KEYWORDS = {"artist"}
DATE_KEYWORDS = {"datum", "date"}
VENUE_KEYWORDS = {"venue", "plats", "lokal"}

EXPLICIT_FORMATS = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
]


def _normalize(name: str) -> str:
    return name.strip().lower()


def _find_column(columns: list[str], keywords: set[str]) -> Optional[str]:
    for col in columns:
        if _normalize(col) in keywords:
            return col
    return None


def _parse_date(value) -> str:
    """Parse various date formats and return dd-MM-yyyy string for setlist.fm."""
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")

    s = str(value).strip()

    # Try formats where day comes first (ambiguous otherwise)
    for fmt in EXPLICIT_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue

    # Fall back to pandas which handles ISO dates, Excel serials, and
    # datetime strings like '2026-03-21 00:00:00' or '2026-03-21 00:00:00.000000'
    try:
        return pd.to_datetime(s).strftime("%d-%m-%Y")
    except Exception:
        pass

    raise ValueError(f"Unrecognized date format: {value!r}")


def parse_excel(file_bytes: bytes) -> list[dict]:
    """
    Parse an xlsx file and return a list of row dicts with keys:
    id, artist, date, venue (optional).
    Raises ValueError with a descriptive message on bad input.
    """
    import io
    df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    df.columns = [str(c) for c in df.columns]

    artist_col = _find_column(df.columns.tolist(), ARTIST_KEYWORDS)
    date_col = _find_column(df.columns.tolist(), DATE_KEYWORDS)
    venue_col = _find_column(df.columns.tolist(), VENUE_KEYWORDS)

    missing = []
    if artist_col is None:
        missing.append("Artist")
    if date_col is None:
        missing.append("Datum/Date")
    if missing:
        raise ValueError(f"Hittade inte kolumn(er): {', '.join(missing)}")

    rows = []
    for i, row in enumerate(df.itertuples(index=False), start=1):
        artist = getattr(row, artist_col.replace(" ", "_"), None)
        date_raw = getattr(row, date_col.replace(" ", "_"), None)

        # Handle pandas attribute name mangling (special chars replaced by _)
        artist = str(row[df.columns.get_loc(artist_col)]).strip()
        date_raw = str(row[df.columns.get_loc(date_col)]).strip()

        if not artist or artist.lower() == "nan":
            continue
        if not date_raw or date_raw.lower() == "nan":
            continue

        try:
            date_str = _parse_date(date_raw)
        except ValueError as e:
            raise ValueError(f"Rad {i}: {e}")

        venue = None
        if venue_col is not None:
            v = str(row[df.columns.get_loc(venue_col)]).strip()
            if v and v.lower() != "nan":
                venue = v

        rows.append({
            "id": i,
            "artist": artist,
            "date": date_str,
            "venue": venue,
        })

    if not rows:
        raise ValueError("Inga giltiga rader hittades i filen.")

    return rows
