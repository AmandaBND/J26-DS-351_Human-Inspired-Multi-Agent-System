from datetime import datetime as D

from src.services.working_time import (add_working_minutes, in_working_hours, next_working_start,
                                       working_minutes_between)


def test_friday_evening_rolls_to_saturday():
    assert add_working_minutes(D(2026, 3, 13, 16, 30), 60) == D(2026, 3, 14, 9, 0)


def test_saturday_close_rolls_to_monday():
    assert add_working_minutes(D(2026, 3, 14, 12, 30), 60) == D(2026, 3, 16, 9, 0)


def test_holiday_skipped():
    assert next_working_start(D(2026, 4, 13, 10, 0)) == D(2026, 4, 15, 8, 30)


def test_working_minutes_between():
    assert working_minutes_between(D(2026, 3, 13, 16, 0), D(2026, 3, 16, 9, 0)) == 360
    assert working_minutes_between(D(2026, 3, 16, 9, 0), D(2026, 3, 13, 16, 0)) == -360


def test_after_hours():
    assert not in_working_hours(D(2026, 3, 15, 10, 0))   # Sunday
