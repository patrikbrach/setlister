#!/usr/bin/env python3
"""Telegram family bot with shopping list, weather, traffic, news and calendar commands."""

import os
import sys
import logging
import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app/shared")

from dotenv import load_dotenv
from telegram import Update, BotCommand, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

from handlers.shopping import cmd_handla, cmd_lista, cmd_klar, cmd_angra, cmd_rensa, cmd_raderalista
from handlers.todo import cmd_todo
from handlers.weather import cmd_vader
from handlers.traffic import cmd_tag
from handlers.news import cmd_nyheter
from handlers.calendar import (
    cmd_idag, cmd_imorgon, cmd_vecka, cmd_boka, cmd_avboka, cmd_ja, cmd_nej
)
import database as db

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Stockholm")

HELP_TEXT = """🤖 *Tillgängliga kommandon*

*To-do*
/todo <uppgift> — Lägg till uppgift
/todo klar <nr> — Stryk av uppgift
/todo lista — Visa listan
/todo rensa — Ta bort klara

*Inköpslista*
/handla vara1, vara2 — Lägg till varor
/lista — Visa hela inköpslistan
/klar vara — Pricka av en vara
/angra vara — Ta tillbaka en avprickad vara
/rensa — Ta bort alla avprickade varor
/raderalista — Radera hela listan

*Kalender*
/idag — Dagens händelser
/imorgon — Morgondagens händelser
/vecka — Veckans händelser
/boka datum tid titel — Boka händelse
/avboka titel — Avboka händelse

*Info*
/vader — Väder för Malmö
/vader stad — Väder för valfri stad
/tag — Tågstörningar Malmö–CPH och Malmö–Lund
/nyheter — Top 3 senaste nyheter
/hjalp — Denna hjälp
"""


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("todo", "Hantera to-do-listan"),
        BotCommand("handla", "Lägg till varor på inköpslistan"),
        BotCommand("lista", "Visa inköpslistan"),
        BotCommand("klar", "Pricka av en vara"),
        BotCommand("angra", "Ta tillbaka en avprickad vara"),
        BotCommand("rensa", "Ta bort avprickade varor"),
        BotCommand("raderalista", "Radera hela inköpslistan"),
        BotCommand("idag", "Dagens kalenderhändelser"),
        BotCommand("imorgon", "Morgondagens kalenderhändelser"),
        BotCommand("vecka", "Veckans kalenderhändelser"),
        BotCommand("boka", "Boka en händelse"),
        BotCommand("avboka", "Avboka en händelse"),
        BotCommand("vader", "Visa väder"),
        BotCommand("tag", "Visa tågstörningar"),
        BotCommand("nyheter", "Visa senaste nyheter"),
        BotCommand("hjalp", "Visa hjälp"),
    ])


# --- Reminder background job ---

_sent_reminders: set[str] = set()  # event_id + date string


async def reminder_job(context) -> None:
    """Check for events starting within 30 minutes and send reminders."""
    cal_id = os.environ.get("GOOGLE_CALENDAR_ID", "")
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "/app/google-credentials.json")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not cal_id or not chat_id:
        return

    try:
        import calendar_client as gc
        events = gc.get_todays_events(cal_id, creds_file)
        now = datetime.datetime.now(tz=TZ)
        window = now + datetime.timedelta(minutes=35)

        for ev in events:
            if ev["all_day"]:
                continue
            minutes_until = (ev["start"] - now).total_seconds() / 60
            reminder_key = f"{ev['id']}_{ev['start'].date()}"

            if 0 < minutes_until <= 35 and reminder_key not in _sent_reminders:
                _sent_reminders.add(reminder_key)
                mins = int(minutes_until)
                end_str = ev["end"].strftime("%H:%M")
                text = (
                    f"⏰ *Om {mins} min: {ev['title']}*\n"
                    f"📅 {ev['start'].strftime('%H:%M')}–{end_str}"
                )
                await context.bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="Markdown"
                )
    except Exception as e:
        logger.warning(f"Reminder job error: {e}")


def main() -> None:
    db.init_db()

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).post_init(post_init).build()

    # Todo handler
    app.add_handler(CommandHandler("todo", cmd_todo))

    # Shopping handlers
    app.add_handler(CommandHandler("handla", cmd_handla))
    app.add_handler(CommandHandler("lista", cmd_lista))
    app.add_handler(CommandHandler("klar", cmd_klar))
    app.add_handler(CommandHandler("angra", cmd_angra))
    app.add_handler(CommandHandler("rensa", cmd_rensa))
    app.add_handler(CommandHandler("raderalista", cmd_raderalista))

    # Calendar handlers
    app.add_handler(CommandHandler("idag", cmd_idag))
    app.add_handler(CommandHandler("imorgon", cmd_imorgon))
    app.add_handler(CommandHandler("vecka", cmd_vecka))
    app.add_handler(CommandHandler("boka", cmd_boka))
    app.add_handler(CommandHandler("avboka", cmd_avboka))
    app.add_handler(CommandHandler("ja", cmd_ja))
    app.add_handler(CommandHandler("nej", cmd_nej))

    # Info handlers
    app.add_handler(CommandHandler("vader", cmd_vader))
    app.add_handler(CommandHandler("tag", cmd_tag))
    app.add_handler(CommandHandler("nyheter", cmd_nyheter))
    app.add_handler(CommandHandler(["hjalp", "help"], cmd_help))

    # Reminder job every 5 minutes
    app.job_queue.run_repeating(reminder_job, interval=300, first=30)

    logger.info("Bot startar med polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
