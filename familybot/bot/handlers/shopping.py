"""Telegram handlers for shopping list commands."""

import sys, os
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes

import database as db


def _display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


async def cmd_handla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/handla vara1, vara2, ..."""
    if not context.args:
        await update.message.reply_text("Användning: /handla vara1, vara2, ...")
        return

    raw = " ".join(context.args)
    items = [i.strip() for i in raw.split(",") if i.strip()]
    if not items:
        await update.message.reply_text("Inga varor hittades. Separera med komma.")
        return

    who = _display_name(update.effective_user)
    for item in items:
        db.add_item(item, who)

    added = "\n".join(f"  • {i}" for i in items)
    await update.message.reply_text(f"Lade till:\n{added}")


async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/lista — visa hela inköpslistan"""
    rows = db.get_all_items()
    if not rows:
        await update.message.reply_text("Inköpslistan är tom!")
        return

    active = [r for r in rows if not r["completed"]]
    done = [r for r in rows if r["completed"]]

    lines = ["🛒 *Inköpslista*"]
    if active:
        lines.append("\n*Att köpa:*")
        for r in active:
            date_str = str(r["added_at"])[:10]
            lines.append(f"  ⬜ {r['item']} _(tillagd {date_str} av {r['added_by']})_")
    if done:
        lines.append("\n*Klara:*")
        for r in done:
            date_str = str(r["completed_at"])[:10] if r["completed_at"] else "?"
            lines.append(f"  ✅ ~{r['item']}~ _(klar {date_str} av {r['completed_by']})_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_klar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/klar vara — pricka av en vara"""
    if not context.args:
        await update.message.reply_text("Användning: /klar vara")
        return
    item = " ".join(context.args)
    who = _display_name(update.effective_user)
    if db.complete_item(item, who):
        await update.message.reply_text(f"✅ *{item}* markerad som klar!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Hittade inte '{item}' i aktiva varor.")


async def cmd_angra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ångra vara — ta tillbaka en avprickad vara"""
    if not context.args:
        await update.message.reply_text("Användning: /ångra vara")
        return
    item = " ".join(context.args)
    if db.undo_item(item):
        await update.message.reply_text(f"↩️ *{item}* återlagd i listan.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Hittade inte '{item}' bland avprickade varor.")


async def cmd_rensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rensa — ta bort alla avprickade varor"""
    count = db.delete_completed()
    if count:
        await update.message.reply_text(f"🗑️ Tog bort {count} avprickad(e) vara(or).")
    else:
        await update.message.reply_text("Inga avprickade varor att rensa.")


async def cmd_raderalista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/raderalista — raderar hela inköpslistan"""
    count = db.delete_all()
    if count:
        await update.message.reply_text(f"🗑️ Hela listan raderad ({count} varor borttagna).")
    else:
        await update.message.reply_text("Listan var redan tom.")
