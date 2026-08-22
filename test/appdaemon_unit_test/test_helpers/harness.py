from __future__ import annotations
from datetime import datetime as dt_datetime, timedelta, time, date
from typing import Any, Callable, TypeVar

from appdaemon_unit_test.test_helpers.config import create_app_manager
from appdaemon_unit_test.test_helpers.hass import AppManager, Hass
from locker import Locker
from mutex_graph import find_cycle, append_graph
from appdaemon_unit_test.test_helpers.test_app import TestApp

T = TypeVar("T")


class Harness:
    locker: Locker
    test_app: TestApp
    _manager: AppManager
    _interval: timedelta
    _global_mutex_graph: dict[str, Any]

    def __init__(
        self,
        start_date: date,
        start_time: time,
        interval: timedelta,
        log_path: str,
        global_mutex_graph: dict[str, Any],
    ) -> None:
        start_datetime = dt_datetime.combine(start_date, start_time)
        self._manager = create_app_manager(start_datetime, log_path)
        self._interval = interval
        self._global_mutex_graph = global_mutex_graph
        locker = self.create_app(
            "locker", "Locker", "locker", enable_logging=True
        )
        assert isinstance(locker, Locker)
        self.locker = locker
        test_app = self.create_app("test_app", "TestApp", "test_app")
        import test_app as test_app_module  # type: ignore[import-not-found]
        assert isinstance(test_app, test_app_module.TestApp)
        self.test_app = test_app

    @property
    def datetime(self) -> dt_datetime:
        return self._manager.datetime()

    @property
    def interval(self) -> timedelta:
        return self._interval

    @property
    def app_manager(self) -> AppManager:
        return self._manager

    def step(self) -> None:
        self._manager.step(self._interval)

    def advance_time(self, amount: timedelta) -> None:
        self._manager.advance_time(amount, self._interval)

    def advance_time_to(self, target_time: time | timedelta) -> None:
        target = self.date_from_time(target_time, future=True)
        self.advance_time_to_datetime(target)

    def advance_time_to_datetime(self, target: dt_datetime) -> None:
        self._manager.advance_time_to(target, self._interval)

    def get_state(
        self,
        entity_id: str,
        attribute: str | None = None,
        type: str | None = None,
    ) -> Any:
        return self.test_app.get_state_as(entity_id, attribute=attribute, type=type)

    def set_state(self, entity_id: str, value: Any, **attributes: Any) -> None:
        self._call_and_check(self.test_app.set_state, entity_id, value, attributes)

    def turn_on(self, entity_id: str) -> None:
        self.set_state(entity_id, "on")

    def turn_off(self, entity_id: str) -> None:
        self.set_state(entity_id, "off")

    def create_app(
        self, module: str, class_name: str, name: str, **kwargs: Any
    ) -> Hass:
        return self._call_and_check(
            self._manager.create_app, module, class_name, name, **kwargs
        )

    def get_app(self, name: str) -> Hass | None:
        return self._manager.get_app(name)

    def schedule_call_in(
        self, delay: timedelta, func_name: str, *args: Any, **kwargs: Any
    ) -> None:
        self._call_and_check(
            self.test_app.schedule_call_in, delay, func_name, *args, **kwargs
        )

    def schedule_call_at(
        self, target_time: time | timedelta, func_name: str, *args: Any, **kwargs: Any
    ) -> None:
        target = self.date_from_time(target_time, future=True)
        self._call_and_check(
            self.test_app.schedule_call_at, target, func_name, *args, **kwargs
        )

    def schedule_call_at_datetime(
        self, target: dt_datetime, func_name: str, *args: Any, **kwargs: Any
    ) -> None:
        self._call_and_check(
            self.test_app.schedule_call_at, target, func_name, *args, **kwargs
        )

    def call_on_app(
        self, app: Any, method: str, *args: Any, **kwargs: Any
    ) -> Any:
        return self._call_and_check(
            self.test_app.call_on_app, app, method, *args, **kwargs
        )

    def date_from_time(
        self, time_of_day: time | timedelta, future: bool
    ) -> dt_datetime:
        if isinstance(time_of_day, time):
            td = timedelta(
                hours=time_of_day.hour,
                minutes=time_of_day.minute,
                seconds=time_of_day.second,
                microseconds=time_of_day.microsecond,
            )
        else:
            td = time_of_day
        return self.test_app.get_next_time_of_day(td, future)

    def wait_for_state_change(
        self,
        entity: str,
        timeout: timedelta | None = None,
        deadline: time | timedelta | None = None,
        deadline_datetime: dt_datetime | None = None,
        old: str | None = None,
        new: str | None = None,
    ) -> None:
        actual_deadline = deadline_datetime
        if timeout is not None:
            actual_deadline = self.datetime + timeout
        elif deadline is not None:
            actual_deadline = self.date_from_time(deadline, future=True)
        self._manager.wait_for_state_change(
            entity, actual_deadline, self._interval, old=old, new=new
        )

    def _call_and_check(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        result = func(*args, **kwargs)
        self._manager.call_pending_callbacks()
        assert not self._manager.has_error()
        return result

    def clear_errors(self) -> None:
        self._manager.clear_errors()

    def cleanup(self) -> None:
        mutex_graph = self.locker.get_global_graph()
        append_graph(self._global_mutex_graph, mutex_graph)
        assert not find_cycle(self._global_mutex_graph)
        self._manager.remove_all_apps()
        assert not self._manager.has_error()