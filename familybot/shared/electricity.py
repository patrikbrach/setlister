"""Electricity spot price client using energidataservice.dk (free, no API key)."""

import datetime
import requests
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")
PRICES_URL = "https://api.energidataservice.dk/dataset/Elspotprices"
FX_URL = "https://open.er-api.com/v6/latest/EUR"


def _get_eur_sek() -> float:
    """Fetch current EUR/SEK exchange rate. Returns fallback 11.5 on failure."""
    try:
        r = requests.get(FX_URL, timeout=5)
        r.raise_for_status()
        return r.json()["rates"]["SEK"]
    except Exception:
        return 11.5  # fallback approximation


def fetch_prices(date: datetime.date, zone: str = "SE4") -> list[dict]:
    """Fetch hourly spot prices for a given date. Returns list of {hour, ore_per_kwh}."""
    # Query a 26-hour window to ensure we cover the full day regardless of UTC offset
    start = datetime.datetime(date.year, date.month, date.day, 0, 0,
                              tzinfo=TZ).astimezone(datetime.timezone.utc)
    end = start + datetime.timedelta(hours=26)

    try:
        params = {
            "start": start.strftime("%Y-%m-%dT%H:%M"),
            "end": end.strftime("%Y-%m-%dT%H:%M"),
            "filter": f'{{"PriceArea":"{zone}"}}',
            "sort": "HourUTC asc",
            "limit": 30,
        }
        r = requests.get(PRICES_URL, params=params, timeout=10)
        r.raise_for_status()
        records = r.json().get("records", [])
    except Exception as e:
        print(f"Elpris API error: {e}")
        return []

    eur_sek = _get_eur_sek()
    result = []
    for rec in records:
        hour_dk = rec.get("HourDK", "")
        if not hour_dk.startswith(date.isoformat()):
            continue
        eur_mwh = rec.get("SpotPriceEUR", 0)
        ore_kwh = round(eur_mwh / 1000 * eur_sek * 100)
        hour = int(hour_dk[11:13])
        result.append({"hour": hour, "ore": ore_kwh})

    return sorted(result, key=lambda x: x["hour"])


def get_price_summary(zone: str = "SE4") -> dict:
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    now_hour = datetime.datetime.now(tz=TZ).hour

    def summarise(prices: list[dict], current_hour: int | None = None) -> dict | None:
        if not prices:
            return None
        ore_list = [p["ore"] for p in prices]
        avg = round(sum(ore_list) / len(ore_list))
        sorted_ore = sorted(ore_list)
        n = max(1, len(sorted_ore) // 3)
        low_thresh = sorted_ore[n - 1]
        high_thresh = sorted_ore[-n]
        cheap = [p["hour"] for p in prices if p["ore"] <= low_thresh]
        expensive = [p["hour"] for p in prices if p["ore"] >= high_thresh]
        out = {
            "avg": avg,
            "min": min(ore_list),
            "max": max(ore_list),
            "cheap_hours": cheap,
            "expensive_hours": expensive,
        }
        if current_hour is not None:
            match = [p for p in prices if p["hour"] == current_hour]
            if match:
                out["now"] = match[0]["ore"]
        return out

    return {
        "today": summarise(fetch_prices(today, zone), now_hour),
        "tomorrow": summarise(fetch_prices(tomorrow, zone)),
    }


def _fmt_hours(hours: list[int]) -> str:
    if not hours:
        return "–"
    groups, start, end = [], hours[0], hours[0]
    for h in hours[1:]:
        if h == end + 1:
            end = h
        else:
            groups.append(f"{start:02d}-{end+1:02d}")
            start = end = h
    groups.append(f"{start:02d}-{end+1:02d}")
    return ", ".join(groups)


def format_price_telegram(zone: str = "SE4") -> str:
    summary = get_price_summary(zone)
    today = summary.get("today")

    if not today:
        return "⚡ *ELPRIS*\nKunde inte hämta elpris just nu."

    now_str = f" | Nu: *{today['now']}*" if "now" in today else ""
    lines = [
        "⚡ *ELPRIS* (öre/kWh spotpris)",
        f"Idag: snitt {today['avg']}, min {today['min']}, max {today['max']}{now_str}",
        f"  🟢 Billig: {_fmt_hours(today['cheap_hours'])}",
        f"  🔴 Dyr:    {_fmt_hours(today['expensive_hours'])}",
    ]

    tomorrow = summary.get("tomorrow")
    if tomorrow:
        lines += [
            f"Imorgon: snitt {tomorrow['avg']}, min {tomorrow['min']}, max {tomorrow['max']}",
            f"  🟢 Billig: {_fmt_hours(tomorrow['cheap_hours'])}",
            f"  🔴 Dyr:    {_fmt_hours(tomorrow['expensive_hours'])}",
        ]

    return "\n".join(lines)
