"""Telegram handler for /väder command."""

import os
import sys
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes
from weather import get_weather_text


async def cmd_vader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/väder [stad] — visar aktuellt väder"""
    api_key = os.environ["OPENWEATHERMAP_API_KEY"]
    city = " ".join(context.args) if context.args else "Malmö"
    text = get_weather_text(city, api_key)
    await update.message.reply_text(f"🌤️ {text}")
