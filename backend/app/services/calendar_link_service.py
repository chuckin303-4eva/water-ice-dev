"""Generates "add to calendar" deep links for Google Calendar and Outlook.
No OAuth, no API calls -- these are just URLs with query parameters that
pre-fill a new-event form in the browser. This works today even with no
frontend: the URL itself is the whole deliverable, clickable from
anywhere (an email, a script, or a real UI button later).
"""

from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

DEFAULT_DURATION = timedelta(minutes=30)


def google_calendar_link(title: str, start: datetime, details: str, location: str) -> str:
    end = start + DEFAULT_DURATION
    date_format = "%Y%m%dT%H%M%SZ"
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{start.strftime(date_format)}/{end.strftime(date_format)}",
        "details": details,
        "location": location,
    }
    return f"https://calendar.google.com/calendar/render?{urlencode(params, quote_via=quote)}"


def outlook_calendar_link(title: str, start: datetime, details: str, location: str) -> str:
    end = start + DEFAULT_DURATION
    params = {
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "subject": title,
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
        "body": details,
        "location": location,
    }
    return f"https://outlook.live.com/calendar/0/deeplink/compose?{urlencode(params, quote_via=quote)}"
