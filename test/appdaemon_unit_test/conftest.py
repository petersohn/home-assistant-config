from __future__ import annotations
import os
import shutil
from datetime import datetime, timedelta, time, date
from typing import Any
import pytest
from helpers.config import create_app_manager
from helpers.timing import Timing
from apps.hass import AppManager, Hass
from apps.mutex_graph import find_cycle, append_graph


class Harness:
    def __init__(
        self,
        start_date: date,
        start_time: time,
        interval: timedelta,
        log_path: str,
        global_mutex_graph: dict,
    ):
        start_datetime = datetime.combine(start_date, start_time)
        self._manager = create_app_manager(start_datetime, log_path)
        self._interval = interval
        self._global_mutex_graph = global_mutex_graph
        self.locker = self.create_app("locker", "Locker", "locker", enable_logging=True)
        self.test_app = self.create_app("test_app", "TestApp", "test_app")

    @property
    def datetime(self) -> datetime:
        return self._manager.datetime()

    @property
    def interval(self) -> timedelta:
        return self._interval

    @property
    def app_manager(self) -> AppManager:
        return self._manager

    def step(self):
        self._manager.step(self._interval)

    def advance_time(self, amount: timedelta):
        self._manager.advance_time(amount, self._interval)

    def advance_time_to(self, target_time: time):
        target = self.date_from_time(target_time, future=True)
        self.advance_time_to_datetime(target)

    def advance_time_to_datetime(self, target: datetime):
        self._manager.advance_time_to(target, self._interval)

    def get_state(self, entity_id: str, attribute: str | None = None, type: str | None = None):
        return self.test_app.get_state_as(entity_id, attribute=attribute, type=type)

    def set_state(self, entity_id: str, value, **attributes):
        self._call_and_check(self.test_app.set_state, entity_id, value, attributes)

    def turn_on(self, entity_id: str):
        self.set_state(entity_id, "on")

    def turn_off(self, entity_id: str):
        self.set_state(entity_id, "off")

    def create_app(self, module: str, class_name: str, name: str, **kwargs) -> Hass:
        return self._call_and_check(self._manager.create_app, module, class_name, name, **kwargs)

    def get_app(self, name: str) -> Hass | None:
        return self._manager.get_app(name)

    def schedule_call_in(self, delay: timedelta, func_name: str, *args, **kwargs):
        self._call_and_check(self.test_app.schedule_call_in, delay, func_name, *args, **kwargs)

    def schedule_call_at(self, target_time: time, func_name: str, *args, **kwargs):
        target = self.date_from_time(target_time, future=True)
        self._call_and_check(self.test_app.schedule_call_at, target, func_name, *args, **kwargs)

    def schedule_call_at_datetime(self, target: datetime, func_name: str, *args, **kwargs):
        self._call_and_check(self.test_app.schedule_call_at, target, func_name, *args, **kwargs)

    def call_on_app(self, app, method: str, *args, **kwargs):
        return self._call_and_check(self.test_app.call_on_app, app, method, *args, **kwargs)

    def date_from_time(self, time_of_day: time | timedelta, future: bool) -> datetime:
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
        deadline_datetime: datetime | None = None,
        old: str | None = None,
        new: str | None = None,
    ):
        actual_deadline = deadline_datetime
        if timeout is not None:
            actual_deadline = self.datetime + timeout
        elif deadline is not None:
            actual_deadline = self.date_from_time(deadline, future=True)
        self._manager.wait_for_state_change(entity, actual_deadline, self._interval, old=old, new=new)

    def _call_and_check(self, func, *args, **kwargs):
        result = func(*args, **kwargs)
        self._manager.call_pending_callbacks()
        assert not self._manager.has_error()
        return result

    def cleanup(self):
        mutex_graph = self.locker.get_global_graph()
        append_graph(self._global_mutex_graph, mutex_graph)
        assert not find_cycle(self._global_mutex_graph)
        self._manager.remove_all_apps()
        assert not self._manager.has_error()


@pytest.fixture(scope="session")
def base_output_directory():
    return os.path.join(os.path.dirname(__file__), "output")


@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory):
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)


@pytest.fixture(scope="module", autouse=True)
def global_mutex_graph():
    graph: dict = {}
    yield graph
    assert not find_cycle(graph)


@pytest.fixture
def harness(request, base_output_directory, global_mutex_graph):
    params = getattr(request, "param", {})
    start_date = params.get("start_date", date(2018, 1, 1))
    module_default_start_time = getattr(request.module, "_default_start_time", time(1, 0, 0))
    start_time = params.get("start_time", module_default_start_time)
    interval = params.get("interval", timedelta(seconds=10))
    safe_name = request.node.name.replace("[", "_").replace("]", "")
    log_dir = os.path.join(base_output_directory, "logs", request.module.__name__)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{safe_name}.log")
    h = Harness(start_date, start_time, interval, log_path, global_mutex_graph)
    yield h
    h.cleanup()


@pytest.fixture
def timing(harness):
    return Timing(harness)