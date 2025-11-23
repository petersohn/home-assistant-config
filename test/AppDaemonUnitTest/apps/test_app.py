import hass
from datetime import datetime, timedelta
from typing import Any, Callable


def convert(value: str | dict[str, str] | None, type_: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: convert(v, type_) for k, v in value.items()}

    converters: dict[str, Callable[[str], Any]] = {
        "int": lambda val: int(float(val)),
        "float": lambda val: float(val),
        "percent": lambda val: int(float(val) * 100.0),
    }
    return converters[type_](value)


class TestApp(hass.Hass):
    def schedule_call_in(
        self, delay: timedelta, func: str, *args: Any, **kwargs: Any
    ) -> None:
        f = getattr(self, func)
        _ = self.run_in(
            lambda _: f(*args, **kwargs), int(delay.total_seconds())
        )

    def schedule_call_at(
        self, when: datetime, func: str, *args: Any, **kwargs: Any
    ) -> None:
        f = getattr(self, func)
        _ = self.run_at(lambda _: f(*args, **kwargs), when)

    def get_state_as(
        self,
        entity: str,
        attribute: str | None = None,
        type: str | None = None,
    ) -> Any:
        value = self.get_state(entity, attribute)
        if type is None:
            return value
        return convert(value, type)
