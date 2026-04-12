"""Telegram handler for /nyheter command."""

import sys
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes
from news import format_news_telegram


async def cmd_nyheter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/nyheter — visar top 3 senaste nyheter"""
    text = format_news_telegram(max_items=3)
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
