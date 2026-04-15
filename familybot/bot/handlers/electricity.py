"""Telegram handler for /elpris command."""

import sys
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes
from electricity import format_price_telegram


async def cmd_elpris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/elpris — visar dagens och morgondagens elpriser"""
    text = format_price_telegram()
    await update.message.reply_text(text, parse_mode="Markdown")
