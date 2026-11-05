"""Tehran time helpers. Iran has no DST since 2022, so a fixed +03:30 offset is exact."""
from datetime import datetime, timedelta, timezone

TEHRAN = timezone(timedelta(hours=3, minutes=30))

# Python weekday(): Monday=0 ... Sunday=6. Iranian trading week: Sat-Wed.
TRADING_WEEKDAYS = {5, 6, 0, 1, 2}
WINDOW_START = (8, 30)
WINDOW_END = (19, 0)


def tehran_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(TEHRAN)
    return now.astimezone(TEHRAN)


def is_active_window(now: datetime | None = None) -> bool:
    """True during the part of the week when trading data can change.

    Hours differ by instrument (stocks ~09:00-12:30, some funds until ~18:30),
    so the window is deliberately wide. It only controls how fast we poll.
    """
    t = tehran_now(now)
    if t.weekday() not in TRADING_WEEKDAYS:
        return False
    return WINDOW_START <= (t.hour, t.minute) < WINDOW_END
