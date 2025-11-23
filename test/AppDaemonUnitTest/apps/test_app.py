import hass
from datetime import datetime, timedelta
from typing import Any, Callable


def call_func(func: Callable[..., None], *args: Any, **kwargs: Any):
    print("call")
    func(*args, **kwargs)


class TestApp(hass.Hass):
    def schedule_call_in(
        self, delay: timedelta, func: str, *args: Any, **kwargs: Any
    ) -> None:
        f = getattr(self, func)
        _ = self.run_in(
            lambda _: call_func(f, *args, **kwargs), int(delay.total_seconds())
        )

    def schedule_call_at(
        self, when: datetime, func: str, *args: Any, **kwargs: Any
    ) -> None:
        f = getattr(self, func)
        _ = self.run_at(lambda _: call_func(f, *args, **kwargs), when)
