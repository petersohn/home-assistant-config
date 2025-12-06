import hass
from datetime import datetime, timedelta, time
from typing import Any, Callable


def convert(value: str | dict[str, str] | None, type_: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: convert(v, type_) for k, v in value.items()}

    converters: dict[str, Callable[[str], Any]] = {
        "str": lambda val: val,
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

    def call_on_app(
        self, app: Any, method: str, *args: Any, **kwargs: Any
    ) -> None:
        getattr(app, method)(*args, **kwargs)

    def get_state_as(
        self,
        entity: str,
        attribute: str | None = None,
        type: str | None = None,
    ) -> Any:
        self.log("get_state_as {} {} {}".format(entity, attribute, type))
        value = self.get_state(entity, attribute)
        if type is None:
            return value
        return convert(value, type)

    def get_next_time_of_day(
        self, time_of_day: timedelta, future: bool
    ) -> datetime:
        value = datetime.combine(self.date(), time()) + time_of_day
        if future and value < self.datetime():
            value += timedelta(days=1)
        return value
