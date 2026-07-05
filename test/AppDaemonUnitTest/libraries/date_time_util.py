from datetime import datetime, time, timedelta
from functools import reduce
from robot.libraries import DateTime
from typing import Any


def to_time(input: str) -> time:
    raw_seconds = DateTime.convert_time(input, result_format="number")
    assert isinstance(raw_seconds, (int, float))
    total_seconds: float = raw_seconds  # type: ignore[assignment]
    seconds, fraction = divmod(int(total_seconds), 1)
    minutes, second = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return time(
        hour=int(hour),
        minute=int(minute),
        second=int(second),
        microsecond=int(fraction * 1000000),
    )


def find_time(start_date: str, new_time: str) -> datetime:
    raw_date = DateTime.convert_date(start_date, result_format="datetime")
    assert isinstance(raw_date, datetime)
    start_datetime: datetime = raw_date
    time = to_time(new_time)
    result = start_datetime.replace(
        hour=time.hour,
        minute=time.minute,
        second=time.second,
        microsecond=time.microsecond,
    )
    if time < start_datetime.time():
        result += timedelta(days=1)
    return result


def add_times(*times: str, **kwargs: Any) -> datetime:
    def add_time(lhs: str, rhs: str) -> datetime:
        result = DateTime.add_time_to_time(lhs, rhs, **kwargs)
        assert isinstance(result, datetime)
        return result

    return reduce(add_time, times)  # type: ignore[arg-type, return-value]
