from appdaemon_unit_test.test_helpers import hass
from datetime import datetime


def repeat_item[T](item: T, count: int) -> list[T]:
    return [item] * count


def create_app_manager(
    start_datetime: datetime, log_filename: str
) -> hass.AppManager:
    return hass.AppManager(start_datetime, log_filename)