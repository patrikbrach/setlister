"""Telegram handler for /tåg command."""

import os
import sys
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes
from trafikverket import get_disruptions, format_disruptions_telegram


async def cmd_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tåg — visar aktuella tågstörningar"""
    api_key = os.environ["TRAFIKVERKET_API_KEY"]
    disruptions = get_disruptions(api_key)
    text = format_disruptions_telegram(disruptions)
    await update.message.reply_text(text, parse_mode="Markdown")
