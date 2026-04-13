"""Telegram handlers for Google Calendar commands."""

import datetime
import os
import sys
sys.path.insert(0, "/app/shared")

from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes

import calendar_client as gc

TZ = ZoneInfo("Europe/Stockholm")

SWEDISH_DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
SWEDISH_MONTHS_SHORT = [
    "", "jan", "feb", "mar", "apr", "maj", "jun",
    "jul", "aug", "sep", "okt", "nov", "dec"
]
SWEDISH_DAY_MAP = {
    "måndag": 0, "måndag": 0, "tisdag": 1, "onsdag": 2,
    "torsdag": 3, "fredag": 4, "lördag": 5, "söndag": 6,
    "mandag": 0, "lordag": 5, "sondag": 6,
}


def _cal_id() -> str:
    return os.environ["GOOGLE_CALENDAR_ID"]


def _creds() -> str:
    return os.environ.get("GOOGLE_CREDENTIALS_FILE", "/app/google-credentials.json")


def _display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


def _fmt_time(dt: datetime.datetime, all_day: bool) -> str:
    if all_day:
        return "Heldag"
    return dt.strftime("%H:%M")


def _fmt_event_line(ev: dict) -> str:
    time_str = _fmt_time(ev["start"], ev["all_day"])
    return f"  {time_str} {ev['title']}"


def _fmt_date_header(date: datetime.date) -> str:
    day_name = SWEDISH_DAYS[date.weekday()]
    month = SWEDISH_MONTHS_SHORT[date.month]
    return f"{day_name} {date.day} {month}"


def _format_day_events(events: list[dict], header: str) -> str:
    lines = [f"📅 *{header}*"]
    if not events:
        lines.append("Inga händelser!")
    else:
        for ev in events:
            lines.append(_fmt_event_line(ev))
    return "\n".join(lines)


def _parse_date(token: str) -> datetime.date | None:
    """Parse a Swedish date token into a date object."""
    token = token.lower().strip()
    today = datetime.date.today()

    if token in ("idag", "idag"):
        return today
    if token == "imorgon":
        return today + datetime.timedelta(days=1)

    # Weekday name
    if token in SWEDISH_DAY_MAP:
        target_wd = SWEDISH_DAY_MAP[token]
        days_ahead = (target_wd - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # next occurrence
        return today + datetime.timedelta(days=days_ahead)

    # ISO format: 2026-04-20
    try:
        return datetime.date.fromisoformat(token)
    except ValueError:
        pass

    return None


async def cmd_idag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/idag — visa dagens händelser"""
    try:
        events = gc.get_todays_events(_cal_id(), _creds())
        today = datetime.date.today()
        day_name = SWEDISH_DAYS[today.weekday()]
        month = SWEDISH_MONTHS_SHORT[today.month]
        header = f"IDAG — {day_name} {today.day} {month}"
        await update.message.reply_text(_format_day_events(events, header), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Kunde inte hämta kalendern: {e}")


async def cmd_imorgon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/imorgon — visa morgondagens händelser"""
    try:
        events = gc.get_tomorrows_events(_cal_id(), _creds())
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        header = f"IMORGON — {_fmt_date_header(tomorrow)}"
        await update.message.reply_text(_format_day_events(events, header), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Kunde inte hämta kalendern: {e}")


async def cmd_vecka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/vecka — visa veckans händelser"""
    try:
        events = gc.get_weeks_events(_cal_id(), _creds())
        today = datetime.date.today()
        week_num = today.isocalendar()[1]
        monday = today - datetime.timedelta(days=today.weekday())

        lines = [f"📅 *VECKA {week_num}*"]
        for i in range(7):
            day = monday + datetime.timedelta(days=i)
            day_events = [e for e in events if e["start"].date() == day]
            lines.append(f"\n*{_fmt_date_header(day)}*")
            if day_events:
                for ev in day_events:
                    lines.append(_fmt_event_line(ev))
            else:
                lines.append("  Inga händelser")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Kunde inte hämta kalendern: {e}")


async def cmd_boka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/boka <datum> <tid> <titel>"""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Användning: /boka <datum> <tid> <titel>\n"
            "Exempel: /boka imorgon 15:00 Tandläkaren\n"
            "Datum: idag, imorgon, måndag…söndag, 2026-04-20"
        )
        return

    date_str = context.args[0]
    time_str = context.args[1]
    title = " ".join(context.args[2:])

    date = _parse_date(date_str)
    if not date:
        await update.message.reply_text(f"Förstår inte datumet '{date_str}'.")
        return

    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        await update.message.reply_text(f"Förstår inte tiden '{time_str}'. Använd HH:MM.")
        return

    start_dt = datetime.datetime(date.year, date.month, date.day, hour, minute, tzinfo=TZ)
    end_dt = start_dt + datetime.timedelta(hours=1)

    try:
        who = _display_name(update.effective_user)
        event = gc.create_event(_cal_id(), _creds(), title, start_dt, end_dt,
                                description=f"Bokad av {who}")
        date_label = _fmt_date_header(date)
        await update.message.reply_text(
            f"✅ *Inbokat!*\n"
            f"📅 {date_label} {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}\n"
            f"📝 {title}\n"
            f"👤 Bokad av {who}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Kunde inte boka: {e}")


# Pending cancellation: maps chat_id → (event_id, title, date_label)
_pending_cancel: dict[int, tuple[str, str, str]] = {}


async def cmd_avboka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/avboka <titel> — sök bland dagens och morgondagens händelser"""
    if not context.args:
        await update.message.reply_text("Användning: /avboka <titel eller del av titel>")
        return

    query = " ".join(context.args).lower()

    try:
        events = gc.get_todays_events(_cal_id(), _creds()) + \
                 gc.get_tomorrows_events(_cal_id(), _creds())
    except Exception as e:
        await update.message.reply_text(f"Kunde inte hämta kalendern: {e}")
        return

    matches = [e for e in events if query in e["title"].lower()]
    if not matches:
        await update.message.reply_text(f"Hittade ingen händelse med '{query}'.")
        return

    ev = matches[0]
    date_label = _fmt_date_header(ev["start"].date())
    time_label = ev["start"].strftime("%H:%M")
    chat_id = update.effective_chat.id
    _pending_cancel[chat_id] = (ev["id"], ev["title"], f"{date_label} {time_label}")

    await update.message.reply_text(
        f"🗑️ Vill du avboka *{ev['title']}* {date_label} {time_label}?\n"
        "Svara /ja eller /nej",
        parse_mode="Markdown"
    )


async def cmd_ja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ja — bekräfta avbokning"""
    chat_id = update.effective_chat.id
    pending = _pending_cancel.pop(chat_id, None)
    if not pending:
        await update.message.reply_text("Inget att bekräfta.")
        return
    event_id, title, label = pending
    try:
        gc.delete_event(_cal_id(), _creds(), event_id)
        await update.message.reply_text(f"🗑️ *{title}* ({label}) avbokad.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Kunde inte avboka: {e}")


async def cmd_nej(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/nej — avbryt avbokning"""
    chat_id = update.effective_chat.id
    _pending_cancel.pop(chat_id, None)
    await update.message.reply_text("Avbokning avbruten.")
