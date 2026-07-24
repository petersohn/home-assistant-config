from __future__ import annotations

from datetime import datetime
from unit_helpers.date_time_util import to_time, find_time, add_times


def test_to_time() -> None:
    result = to_time("10:15:30")
    assert result.hour == 10
    assert result.minute == 15
    assert result.second == 30


def test_find_time_on_same_day() -> None:
    result = find_time("2018-01-01 12:00:00", "13:15:30")
    assert result == datetime(2018, 1, 1, 13, 15, 30)


def test_find_time_on_next_day() -> None:
    result = find_time("2018-01-01 12:00:00", "10:32:40")
    assert result == datetime(2018, 1, 2, 10, 32, 40)


def test_add_times() -> None:
    from datetime import timedelta
    result = add_times(
        timedelta(seconds=10),
        timedelta(minutes=32, seconds=5),
        timedelta(hours=2, minutes=5, seconds=24),
    )
    assert result == timedelta(hours=2, minutes=37, seconds=39)