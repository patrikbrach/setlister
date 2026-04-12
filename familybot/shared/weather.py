"""OpenWeatherMap API client."""

import requests
from typing import Optional

OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_weather(city: str, api_key: str) -> Optional[dict]:
    """Fetch current weather for a city. Returns raw OWM response dict or None."""
    try:
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "sv",
        }
        response = requests.get(OWM_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Weather API error for {city}: {e}")
        return None


def parse_weather(data: dict) -> dict:
    """Extract relevant fields from OWM response."""
    temp = round(data["main"]["temp"])
    description = data["weather"][0]["description"].capitalize()
    wind = round(data["wind"]["speed"])
    rain = data.get("rain", {}).get("1h", 0)
    return {
        "temp": temp,
        "description": description,
        "wind": wind,
        "rain": rain,
    }


def get_weather_text(city: str, api_key: str) -> str:
    """Return a one-line weather summary for a city, or an error string."""
    data = fetch_weather(city, api_key)
    if not data:
        return f"{city}: Kunde inte hämta väder"
    w = parse_weather(data)
    rain_text = f", regn {w['rain']} mm/h" if w["rain"] > 0 else ""
    return f"{city}: {w['temp']}°C, {w['description']}, vind {w['wind']} m/s{rain_text}"


def format_weather_telegram(cities: list[str], api_key: str) -> str:
    """Format weather for multiple cities into a Telegram block."""
    lines = ["🌤️ *VÄDER*"]
    for city in cities:
        lines.append(get_weather_text(city, api_key))
    return "\n".join(lines)
