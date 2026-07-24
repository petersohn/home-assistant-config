from datetime import datetime, time, timedelta
from dateutil import parser as date_parser


def to_time(input: str) -> time:
    parsed = date_parser.parse(input)
    return parsed.time()


def find_time(start_date: str, new_time: str) -> datetime:
    start_datetime = date_parser.parse(start_date)
    target_time = to_time(new_time)
    result = start_datetime.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=target_time.second,
        microsecond=target_time.microsecond,
    )
    if target_time < start_datetime.time():
        result += timedelta(days=1)
    return result


def add_times(*times: timedelta) -> timedelta:
    return sum(times, timedelta())