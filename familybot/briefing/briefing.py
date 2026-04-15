#!/usr/bin/env python3
"""Morning briefing: fetches train info, weather and news, then sends to Telegram."""

import os
import sys
import datetime
import requests
from dotenv import load_dotenv

# Allow importing shared modules whether running locally or inside Docker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "shared"))
sys.path.insert(0, "/app/shared")

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENWEATHERMAP_API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]
TRAFIKVERKET_API_KEY = os.environ["TRAFIKVERKET_API_KEY"]
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "")
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "/app/google-credentials.json")

# Import shared modules (paths set above)
from trafikverket import get_disruptions, format_disruptions_telegram  # noqa: E402
from weather import format_weather_telegram  # noqa: E402
from electricity import format_price_telegram  # noqa: E402
from config import WEATHER_CITIES  # noqa: E402
from calendar_client import get_todays_events  # noqa: E402

SWEDISH_DAYS = [
    "Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"
]
SWEDISH_MONTHS = [
    "", "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]


def format_date() -> str:
    now = datetime.datetime.now()
    day_name = SWEDISH_DAYS[now.weekday()]
    return f"{day_name} {now.day} {SWEDISH_MONTHS[now.month]} {now.year}"


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()


def get_telegram_chat_id(token: str) -> str:
    """Return the chat_id from TELEGRAM_CHAT_ID env, or auto-detect from latest update."""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if chat_id:
        return chat_id

    # Auto-detect: get the most recent message's chat id
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    response = requests.get(url, params={"limit": 1, "offset": -1}, timeout=10)
    response.raise_for_status()
    data = response.json()
    updates = data.get("result", [])
    if not updates:
        raise RuntimeError(
            "Inget chat_id hittades. Skicka ett meddelande till boten "
            "eller sätt TELEGRAM_CHAT_ID i .env"
        )
    return str(updates[-1]["message"]["chat"]["id"])


def build_calendar_block() -> str:
    if not GOOGLE_CALENDAR_ID:
        return ""
    try:
        events = get_todays_events(GOOGLE_CALENDAR_ID, GOOGLE_CREDENTIALS_FILE)
        lines = ["📅 *IDAG*"]
        if not events:
            lines.append("Inga händelser idag")
        for ev in events:
            if ev["all_day"]:
                lines.append(f"  Heldag: {ev['title']}")
            else:
                lines.append(f"  {ev['start'].strftime('%H:%M')} {ev['title']}")
        return "\n".join(lines)
    except Exception as e:
        print(f"Kalender-fel: {e}")
        return ""


def build_message() -> str:
    date_str = format_date()
    header = f"🌅 *God morgon familjen! {date_str}*\n"

    disruptions = get_disruptions(TRAFIKVERKET_API_KEY)
    traffic_block = format_disruptions_telegram(disruptions)

    weather_block = format_weather_telegram(WEATHER_CITIES, OPENWEATHERMAP_API_KEY)

    news_block = format_news_telegram(max_items=3)

    calendar_block = build_calendar_block()

    electricity_block = format_price_telegram()

    blocks = [header, traffic_block, weather_block, electricity_block]
    if calendar_block:
        blocks.append(calendar_block)
    return "\n\n".join(blocks)


def main() -> None:
    print("Bygger morgon-briefing...")
    message = build_message()
    print("Meddelande:\n" + message)

    chat_id = get_telegram_chat_id(TELEGRAM_BOT_TOKEN)
    send_telegram(TELEGRAM_BOT_TOKEN, chat_id, message)
    print("Skickat till Telegram!")


if __name__ == "__main__":
    main()
