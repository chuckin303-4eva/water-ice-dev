from datetime import UTC, datetime

from app.services import calendar_link_service


def test_google_calendar_link_contains_expected_fields() -> None:
    start = datetime(2026, 8, 5, 15, 0, 0, tzinfo=UTC)
    link = calendar_link_service.google_calendar_link(
        "Follow up: 123 Main St", start, "Call notes here", "123 Main St, Denver, CO"
    )
    assert link.startswith("https://calendar.google.com/calendar/render?")
    assert "action=TEMPLATE" in link
    assert "20260805T150000Z%2F20260805T153000Z" in link  # 30 min default duration
    assert "text=Follow+up" in link or "text=Follow%20up" in link


def test_outlook_calendar_link_contains_expected_fields() -> None:
    start = datetime(2026, 8, 5, 15, 0, 0, tzinfo=UTC)
    link = calendar_link_service.outlook_calendar_link(
        "Follow up: 123 Main St", start, "Call notes here", "123 Main St, Denver, CO"
    )
    assert link.startswith("https://outlook.live.com/calendar/0/deeplink/compose?")
    assert "rru=addevent" in link
    assert "startdt=2026-08-05T15%3A00%3A00%2B00%3A00" in link
