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


def create_app_manager(start_datetime: datetime) -> hass.AppManager:
    return hass.AppManager(start_datetime)


def add_app(
    manager: hass.AppManager,
    library_name: str,
    class_name: str,
    app_name: str,
    **kwargs: Any,
) -> hass.Hass:
    library = __import__("apps." + library_name)
    class_ = getattr(library, class_name)
    obj = class_()
    manager.add_app(app_name, obj, kwargs)
    return obj
