"""Electricity spot price client using elprisetjust.se (free, no API key)."""

import datetime
import requests
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")
BASE_URL = "https://www.elprisetjust.se/api/v1/prices"


def fetch_prices(date: datetime.date, zone: str = "SE4") -> list[dict]:
    """Fetch hourly spot prices for a given date and price zone."""
    url = f"{BASE_URL}/{date.year}/{date.month:02d}-{date.day:02d}_{zone}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Elpris API error: {e}")
        return []


def _ore(sek_per_kwh: float) -> int:
    """Convert SEK/kWh to öre/kWh."""
    return round(sek_per_kwh * 100)


def get_price_summary(zone: str = "SE4") -> dict:
    """
    Returns a summary dict for today and tomorrow:
    {
        'today': {'avg': int, 'min': int, 'max': int, 'now': int, 'cheap_hours': [int], 'expensive_hours': [int]},
        'tomorrow': {...} or None
    }
    All prices in öre/kWh.
    """
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    now_hour = datetime.datetime.now(tz=TZ).hour

    def summarise(prices: list[dict], current_hour: int | None = None) -> dict | None:
        if not prices:
            return None
        sek_prices = [p["SEK_per_kWh"] for p in prices]
        ore_prices = [_ore(p) for p in sek_prices]
        avg = round(sum(ore_prices) / len(ore_prices))
        sorted_prices = sorted(ore_prices)
        low_threshold = sorted_prices[len(sorted_prices) // 3]
        high_threshold = sorted_prices[-(len(sorted_prices) // 3)]
        cheap = [i for i, p in enumerate(ore_prices) if p <= low_threshold]
        expensive = [i for i, p in enumerate(ore_prices) if p >= high_threshold]
        result = {
            "avg": avg,
            "min": min(ore_prices),
            "max": max(ore_prices),
            "cheap_hours": cheap,
            "expensive_hours": expensive,
        }
        if current_hour is not None and current_hour < len(ore_prices):
            result["now"] = ore_prices[current_hour]
        return result

    today_prices = fetch_prices(today, zone)
    tomorrow_prices = fetch_prices(tomorrow, zone)

    return {
        "today": summarise(today_prices, now_hour),
        "tomorrow": summarise(tomorrow_prices),
    }


def format_price_telegram(zone: str = "SE4") -> str:
    """Format electricity prices for Telegram."""
    summary = get_price_summary(zone)
    today = summary.get("today")

    if not today:
        return "⚡ *ELPRIS*\nKunde inte hämta elpris just nu."

    def fmt_hours(hours: list[int]) -> str:
        if not hours:
            return "–"
        # Group consecutive hours
        groups = []
        start = hours[0]
        end = hours[0]
        for h in hours[1:]:
            if h == end + 1:
                end = h
            else:
                groups.append(f"{start:02d}-{end+1:02d}")
                start = end = h
        groups.append(f"{start:02d}-{end+1:02d}")
        return ", ".join(groups)

    lines = ["⚡ *ELPRIS* (öre/kWh inkl. moms)"]

    now_str = f" | Nu: *{today['now']}*" if "now" in today else ""
    lines.append(f"Idag: snitt {today['avg']}, min {today['min']}, max {today['max']}{now_str}")
    lines.append(f"  🟢 Billig: {fmt_hours(today['cheap_hours'])}")
    lines.append(f"  🔴 Dyr:    {fmt_hours(today['expensive_hours'])}")

    tomorrow = summary.get("tomorrow")
    if tomorrow:
        lines.append(f"Imorgon: snitt {tomorrow['avg']}, min {tomorrow['min']}, max {tomorrow['max']}")
        lines.append(f"  🟢 Billig: {fmt_hours(tomorrow['cheap_hours'])}")
        lines.append(f"  🔴 Dyr:    {fmt_hours(tomorrow['expensive_hours'])}")

    return "\n".join(lines)
