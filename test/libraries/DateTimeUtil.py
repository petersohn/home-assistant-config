import datetime

from robot.libraries import DateTime


def to_time(time):
    total_seconds = DateTime.convert_time(time, result_format='number')
    seconds, fraction = divmod(total_seconds, 1)
    minutes, second = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return datetime.time(
        hour=int(hour),
        minute=int(minute),
        second=int(second),
        microsecond=int(fraction * 1000000))


def find_time(start_date, new_time):
    start_datetime = DateTime.convert_date(
        start_date, result_format='datetime')
    time = to_time(new_time)
    result = start_datetime.replace(
        hour=time.hour, minute=time.minute, second=time.second,
        microsecond=time.microsecond)
    if time < start_datetime.time():
        result += datetime.timedelta(days=1)
    return result
