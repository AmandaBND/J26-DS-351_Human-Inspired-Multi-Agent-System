"""Working-hours calendar shared by the raw-data generator and the preprocessing pipeline.

Prototype assumptions (configurable, NOT verified Metropolitan policy):
  Mon-Fri 08:30-17:00, Sat 08:30-13:00, Sunday and fixed-date public holidays closed.
Only fixed-date holidays are listed (Poya days and other moving holidays are omitted).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

OPEN = time(8, 30)
WEEKDAY_CLOSE = time(17, 0)
SAT_CLOSE = time(13, 0)
WEEKDAY_MINUTES = 510   # 8.5 h
SAT_MINUTES = 270       # 4.5 h

# (month, day, name)
FIXED_HOLIDAYS = [(2, 4, "Independence Day"), (4, 13, "Day before Sinhala & Tamil New Year"),
                  (4, 14, "Sinhala & Tamil New Year"), (5, 1, "May Day"), (12, 25, "Christmas Day")]
HOLIDAYS: set[date] = {date(y, m, d) for y in range(2022, 2028) for m, d, _ in FIXED_HOLIDAYS}


def day_window(d: date) -> tuple[datetime, datetime] | None:
    """Opening/closing datetimes for a date, or None if closed."""
    if d in HOLIDAYS or d.weekday() == 6:
        return None
    close = SAT_CLOSE if d.weekday() == 5 else WEEKDAY_CLOSE
    return datetime.combine(d, OPEN), datetime.combine(d, close)


def is_working_day(d: date) -> bool:
    return day_window(d) is not None


def in_working_hours(dt: datetime) -> bool:
    w = day_window(dt.date())
    return bool(w and w[0] <= dt < w[1])


def next_working_start(dt: datetime) -> datetime:
    """dt itself if inside working hours, otherwise the start of the next working period."""
    d = dt.date()
    while True:
        w = day_window(d)
        if w:
            s, e = w
            if d == dt.date():
                if dt <= s:
                    return s
                if dt < e:
                    return dt
            else:
                return s
        d += timedelta(days=1)


def add_working_minutes(dt: datetime, minutes: float) -> datetime:
    cur = next_working_start(dt)
    remaining = float(minutes)
    while True:
        end = day_window(cur.date())[1]
        avail = (end - cur).total_seconds() / 60
        if remaining <= avail:
            return cur + timedelta(minutes=remaining)
        remaining -= avail
        cur = next_working_start(datetime.combine(cur.date() + timedelta(days=1), time(0, 0)))


def working_minutes_between(a: datetime, b: datetime) -> float:
    """Signed working minutes from a to b (after-hours time is not counted)."""
    if b < a:
        return -working_minutes_between(b, a)
    total = 0.0
    d = a.date()
    while d <= b.date():
        w = day_window(d)
        if w:
            s, e = max(w[0], a), min(w[1], b)
            if e > s:
                total += (e - s).total_seconds() / 60
        d += timedelta(days=1)
    return total


def working_days_between(a: datetime, b: datetime) -> float:
    """Working days (8.5 h each) between two timestamps."""
    return working_minutes_between(a, b) / WEEKDAY_MINUTES
