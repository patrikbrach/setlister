"""OpenWeatherMap API client."""

import datetime
import requests
from typing import Optional

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def fetch_weather(city: str, api_key: str) -> Optional[dict]:
    """Fetch current weather for a city."""
    try:
        response = requests.get(
            OWM_CURRENT_URL,
            params={"q": city, "appid": api_key, "units": "metric", "lang": "sv"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Weather API error for {city}: {e}")
        return None


def fetch_forecast(city: str, api_key: str) -> Optional[list]:
    """Fetch 5-day / 3-hour forecast list for a city."""
    try:
        response = requests.get(
            OWM_FORECAST_URL,
            params={"q": city, "appid": api_key, "units": "metric", "lang": "sv"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("list", [])
    except Exception as e:
        print(f"Forecast API error for {city}: {e}")
        return None


def parse_weather(data: dict) -> dict:
    """Extract relevant fields from OWM current weather response."""
    temp = round(data["main"]["temp"])
    description = data["weather"][0]["description"].capitalize()
    wind = round(data["wind"]["speed"])
    rain = data.get("rain", {}).get("1h", 0)
    return {"temp": temp, "description": description, "wind": wind, "rain": rain}


def get_forecast_at_15(forecast_list: list) -> Optional[dict]:
    """Return the forecast entry closest to 15:00 today."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    target = f"{today} 15:00:00"
    # Find exact match first, then nearest
    for entry in forecast_list:
        if entry.get("dt_txt") == target:
            return entry
    # Fallback: closest entry with today's date after 12:00
    candidates = [e for e in forecast_list if e.get("dt_txt", "").startswith(today)]
    if not candidates:
        return None
    return min(candidates, key=lambda e: abs(
        datetime.datetime.strptime(e["dt_txt"], "%Y-%m-%d %H:%M:%S").hour - 15
    ))


def rain_risk_today(forecast_list: list) -> bool:
    """Return True if any forecast entry for the rest of today contains rain."""
    now = datetime.datetime.now()
    today = now.date().strftime("%Y-%m-%d")
    for entry in forecast_list:
        if not entry.get("dt_txt", "").startswith(today):
            continue
        entry_time = datetime.datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if entry_time < now:
            continue
        if entry.get("rain", {}).get("3h", 0) > 0:
            return True
        # Also check weather condition codes: 2xx = thunder, 3xx = drizzle, 5xx = rain, 6xx = snow
        for w in entry.get("weather", []):
            if w.get("id", 0) < 700:
                return True
    return False


def get_weather_text(city: str, api_key: str) -> str:
    """Return a multi-line weather summary for a city."""
    current_data = fetch_weather(city, api_key)
    forecast_list = fetch_forecast(city, api_key)

    if not current_data:
        return f"{city}: Kunde inte hämta väder"

    c = parse_weather(current_data)
    rain_now = f", regn {c['rain']} mm/h" if c["rain"] > 0 else ""
    lines = [f"*{city}*: {c['temp']}°C, {c['description']}, vind {c['wind']} m/s{rain_now}"]

    if forecast_list:
        entry_15 = get_forecast_at_15(forecast_list)
        if entry_15:
            t15 = round(entry_15["main"]["temp"])
            d15 = entry_15["weather"][0]["description"].capitalize()
            r15 = entry_15.get("rain", {}).get("3h", 0)
            rain_15 = f", regn {r15} mm" if r15 > 0 else ""
            lines.append(f"  15:00 → {t15}°C, {d15}{rain_15}")

        risk = rain_risk_today(forecast_list)
        lines.append(f"  Regnrisk idag: {'⚠️ Ja' if risk else '✅ Nej'}")

    return "\n".join(lines)


def format_weather_telegram(cities: list[str], api_key: str) -> str:
    """Format weather for multiple cities into a Telegram block."""
    lines = ["🌤️ *VÄDER*"]
    for city in cities:
        lines.append(get_weather_text(city, api_key))
    return "\n".join(lines)
