"""Google Calendar API client using a service account."""

import datetime
import os
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TZ = ZoneInfo("Europe/Stockholm")


def _service(credentials_file: str):
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _day_bounds(date: datetime.date) -> tuple[str, str]:
    """Return RFC3339 start/end for a full calendar day in Stockholm time."""
    start = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=TZ)
    end = start + datetime.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _parse_event(event: dict) -> dict:
    """Normalise a Calendar API event into a simple dict."""
    start_raw = event["start"].get("dateTime") or event["start"].get("date")
    end_raw = event["end"].get("dateTime") or event["end"].get("date")

    # All-day events have date strings, not datetimes
    if "T" in start_raw:
        start_dt = datetime.datetime.fromisoformat(start_raw).astimezone(TZ)
        end_dt = datetime.datetime.fromisoformat(end_raw).astimezone(TZ)
        all_day = False
    else:
        start_dt = datetime.datetime.fromisoformat(start_raw).replace(tzinfo=TZ)
        end_dt = datetime.datetime.fromisoformat(end_raw).replace(tzinfo=TZ)
        all_day = True

    return {
        "id": event["id"],
        "title": event.get("summary", "(Ingen titel)"),
        "start": start_dt,
        "end": end_dt,
        "all_day": all_day,
        "description": event.get("description", ""),
    }


def _fetch_events(calendar_id: str, credentials_file: str,
                  time_min: str, time_max: str) -> list[dict]:
    svc = _service(credentials_file)
    result = svc.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        timeZone="Europe/Stockholm",
    ).execute()
    return [_parse_event(e) for e in result.get("items", [])]


def get_todays_events(calendar_id: str, credentials_file: str) -> list[dict]:
    t_min, t_max = _day_bounds(datetime.date.today())
    return _fetch_events(calendar_id, credentials_file, t_min, t_max)


def get_tomorrows_events(calendar_id: str, credentials_file: str) -> list[dict]:
    t_min, t_max = _day_bounds(datetime.date.today() + datetime.timedelta(days=1))
    return _fetch_events(calendar_id, credentials_file, t_min, t_max)


def get_weeks_events(calendar_id: str, credentials_file: str) -> list[dict]:
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)
    t_min, _ = _day_bounds(monday)
    _, t_max = _day_bounds(sunday)
    return _fetch_events(calendar_id, credentials_file, t_min, t_max)


def create_event(calendar_id: str, credentials_file: str,
                 title: str,
                 start_dt: datetime.datetime,
                 end_dt: datetime.datetime,
                 description: str = "") -> dict:
    svc = _service(credentials_file)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Stockholm"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Stockholm"},
    }
    event = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return _parse_event(event)


def delete_event(calendar_id: str, credentials_file: str, event_id: str) -> None:
    svc = _service(credentials_file)
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
