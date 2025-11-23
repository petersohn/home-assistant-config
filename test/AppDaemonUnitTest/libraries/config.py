from typing import Any
from apps import hass
from datetime import datetime


def extract_from_dictionary(dictionary: Any, key: Any) -> Any:
    return _extract_from_dictionary(dictionary, key)


def _extract_from_dictionary[Key, Value](
    dictionary: dict[Key, Value], key: Key
) -> Value | None:
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]

    print(dictionary)

    return result


def repeat_item[T](item: T, count: int) -> list[T]:
    return [item] * count


def create_app_manager(
    start_datetime: datetime, log_filename: str
) -> hass.AppManager:
    return hass.AppManager(start_datetime, log_filename)
