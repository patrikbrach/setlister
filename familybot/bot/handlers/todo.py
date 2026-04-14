"""Telegram handler for /todo command."""

import sys
sys.path.insert(0, "/app")
sys.path.insert(0, "/app/shared")

from telegram import Update
from telegram.ext import ContextTypes
import database as db


def _display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


def _render_list() -> str:
    rows = db.todo_get_all()
    if not rows:
        return "📋 *To-do-listan är tom!*"

    active = [r for r in rows if not r["completed"]]
    done = [r for r in rows if r["completed"]]

    lines = ["📋 *To-do*"]
    for i, r in enumerate(active, 1):
        lines.append(f"  {i}. {r['item']}")
    for r in done:
        lines.append(f"  ✅ ~{r['item']}~")

    return "\n".join(lines)


async def cmd_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/todo — lägg till, visa eller stryk av to-do"""
    if not context.args:
        await update.message.reply_text(_render_list(), parse_mode="Markdown")
        return

    first = context.args[0].lower()

    # /todo klar <nummer>
    if first == "klar":
        if len(context.args) < 2 or not context.args[1].isdigit():
            await update.message.reply_text("Användning: /todo klar <nummer>")
            return
        num = int(context.args[1])
        who = _display_name(update.effective_user)
        item = db.todo_complete(num, who)
        if item:
            await update.message.reply_text(
                f"✅ *{item}* klar!\n\n" + _render_list(), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"Hittade ingen punkt #{num}.")
        return

    # /todo lista
    if first == "lista":
        await update.message.reply_text(_render_list(), parse_mode="Markdown")
        return

    # /todo rensa
    if first == "rensa":
        count = db.todo_delete_completed()
        await update.message.reply_text(f"🗑️ Tog bort {count} klara punkter.")
        return

    # /todo <ny uppgift>
    item = " ".join(context.args)
    who = _display_name(update.effective_user)
    db.todo_add(item, who)
    await update.message.reply_text(
        f"✅ Lade till: *{item}*\n\n" + _render_list(), parse_mode="Markdown"
    )
