import asyncio
import httpx

BASE_URL = "https://api.setlist.fm/rest/1.0"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def _build_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "Accept": "application/json",
    }


def _parse_setlist(data: dict, row_id: int) -> dict:
    sets = data.get("sets", {}).get("set", [])
    songs = []
    encore_breaks = []
    order = 1

    for s in sets:
        if s.get("encore"):
            encore_breaks.append(order - 1)  # index before encore starts
        for song in s.get("song", []):
            name = song.get("name", "").strip()
            if not name:
                continue
            info = song.get("info", "") or ""
            songs.append({"order": order, "name": name, "info": info})
            order += 1

    venue_data = data.get("venue", {})
    city_data = venue_data.get("city", {})
    venue_name = venue_data.get("name", "")
    city_name = city_data.get("name", "")
    venue_display = f"{venue_name}, {city_name}" if city_name else venue_name

    return {
        "id": row_id,
        "status": "found",
        "setlist_url": data.get("url", ""),
        "artist": data.get("artist", {}).get("name", ""),
        "venue": venue_display,
        "date": data.get("eventDate", ""),
        "songs": songs,
        "encore_breaks": encore_breaks,
    }


async def fetch_setlist(
    client: httpx.AsyncClient,
    api_key: str,
    row_id: int,
    artist: str,
    date: str,
    venue: str | None = None,
) -> dict:
    """
    Fetch the best matching setlist for artist + date (+ optional venue).
    Returns a result dict with status "found", "not_found", or "error".
    """
    params = {
        "artistName": artist,
        "date": date,
        "p": 1,
    }
    if venue:
        params["venueName"] = venue

    headers = _build_headers(api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(
                f"{BASE_URL}/search/setlists",
                params=params,
                headers=headers,
                timeout=15.0,
            )

            if resp.status_code == 200:
                data = resp.json()
                setlists = data.get("setlist", [])
                if not setlists:
                    return {"id": row_id, "status": "not_found", "artist": artist, "date": date, "venue": venue or ""}
                return _parse_setlist(setlists[0], row_id)

            elif resp.status_code == 404:
                return {"id": row_id, "status": "not_found", "artist": artist, "date": date, "venue": venue or ""}

            elif resp.status_code == 401:
                return {"id": row_id, "status": "error", "message": "Ogiltig API-nyckel (401)", "artist": artist, "date": date}

            elif resp.status_code == 429:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt)
                    continue
                return {"id": row_id, "status": "error", "message": "Rate limit – försök igen senare", "artist": artist, "date": date}

            else:
                return {
                    "id": row_id,
                    "status": "error",
                    "message": f"HTTP {resp.status_code}",
                    "artist": artist,
                    "date": date,
                }

        except httpx.RequestError as e:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)
                continue
            return {"id": row_id, "status": "error", "message": f"Nätverksfel: {e}", "artist": artist, "date": date}

    return {"id": row_id, "status": "error", "message": "Max antal försök uppnått", "artist": artist, "date": date}
