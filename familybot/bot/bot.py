#!/usr/bin/env python3
"""Telegram family bot with shopping list, weather, traffic and news commands."""

import os
import sys
import logging

sys.path.insert(0, "/app/shared")

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

from handlers.shopping import cmd_handla, cmd_lista, cmd_klar, cmd_angra, cmd_rensa, cmd_raderalista
from handlers.weather import cmd_vader
from handlers.traffic import cmd_tag
from handlers.news import cmd_nyheter
import database as db

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

HELP_TEXT = """🤖 *Tillgängliga kommandon*

*Inköpslista*
/handla vara1, vara2 — Lägg till varor
/lista — Visa hela inköpslistan
/klar vara — Pricka av en vara
/angra vara — Ta tillbaka en avprickad vara
/rensa — Ta bort alla avprickade varor
/raderalista — Radera hela listan

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
        BotCommand("handla", "Lägg till varor på inköpslistan"),
        BotCommand("lista", "Visa inköpslistan"),
        BotCommand("klar", "Pricka av en vara"),
        BotCommand("angra", "Ta tillbaka en avprickad vara"),
        BotCommand("rensa", "Ta bort avprickade varor"),
        BotCommand("raderalista", "Radera hela inköpslistan"),
        BotCommand("vader", "Visa väder"),
        BotCommand("tag", "Visa tågstörningar"),
        BotCommand("nyheter", "Visa senaste nyheter"),
        BotCommand("hjalp", "Visa hjälp"),
    ])


def main() -> None:
    db.init_db()

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("handla", cmd_handla))
    app.add_handler(CommandHandler("lista", cmd_lista))
    app.add_handler(CommandHandler("klar", cmd_klar))
    app.add_handler(CommandHandler("angra", cmd_angra))
    app.add_handler(CommandHandler("rensa", cmd_rensa))
    app.add_handler(CommandHandler("raderalista", cmd_raderalista))
    app.add_handler(CommandHandler("vader", cmd_vader))
    app.add_handler(CommandHandler("tag", cmd_tag))
    app.add_handler(CommandHandler("nyheter", cmd_nyheter))
    app.add_handler(CommandHandler(["hjalp", "help"], cmd_help))

    logger.info("Bot startar med polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
