from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta
from inspect import Traceback
from typing import Any, Callable, Literal, NamedTuple
from traceback import format_exception


class State:
    def __init__(self):
        self.state: str | None = None
        self.attributes: dict[str, str] = {}

    def to_map(self) -> dict[str, Any]:
        return {"state": self.state, "attributes": deepcopy(self.attributes)}


StateCallback = Callable[
    [
        str,
        str | None,
        str | dict[str, Any] | None,
        str | dict[str, Any] | None,
        dict[str, Any],
    ],
    None,
]

StateCallbackRecord = NamedTuple(
    "StateCallbackRecord",
    [
        ("app", str),
        ("callback", StateCallback),
        ("entity", str),
        ("attribute", str | None),
        ("old", str | None),
        ("new", str | None),
    ],
)

SchedulerChallback = Callable[[dict[str, Any]], None]

ScheduledTask = NamedTuple(
    "ScheduledTask",
    [
        ("app", str),
        ("time", datetime),
        ("callback", SchedulerChallback),
        ("repeat", timedelta | None),
    ],
)

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ErrorHandler:
    def __init__(self, manager: AppManager, app: str):
        self.__manager = manager
        self.__app = app

    def __enter__(self):
        pass

    def __exit__(self, exc_type: type, exc_val: Any, exc_tb: Traceback) -> bool:
        if not isinstance(exc_val, Exception):
            return False

        for line in format_exception(exc_val):
            self.__manager.log(self.__app, line, "ERROR")
        return True


class AppManager:
    def __init__(self, begin_time: datetime):
        self.__apps: dict[str, Hass] = {}
        self.__states: dict[str, State] = {}
        self.__state_callbacks: dict[int, StateCallbackRecord] = {}
        self.__state_callback_id = 0
        self.__datetime = begin_time
        self.__scheduled_tasks: dict[int, ScheduledTask] = {}
        self.__scheduled_task_order: list[int] = []
        self.__has_error = False

    def add_app(self, name: str, app: Hass, args: dict[str, Any]) -> None:
        with ErrorHandler(self, name):
            app.init_app(self, name, args)
        self.__apps[name] = app

    def remove_app(self, name: str) -> None:
        app = self.__apps[name]
        del self.__apps[name]
        for id in [
            key
            for key, value in self.__state_callbacks.items()
            if value.app == name
        ]:
            self.cancel_listen_state(id)
        for id in [
            key
            for key, value in self.__scheduled_tasks.items()
            if value.app == name
        ]:
            self.cancel_timer(id)
        with ErrorHandler(self, name):
            app.terminate()

    def get_app(self, name: str) -> Hass | None:
        return self.__apps.get(name)

    def get_state(
        self, name: str, attribute: str | None = None
    ) -> str | dict[str, str] | None:
        data = self.__states.get(name)
        if data is None:
            return None
        if attribute is None:
            return data.state
        if attribute == "all":
            return deepcopy(data.attributes)
        return data.attributes.get(attribute)

    def set_state(
        self,
        name: str,
        state: str | None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        data = self.__states.setdefault(name, State())
        old = data.to_map()
        data.state = None if state is None else str(state)

        if attributes is not None:
            data.attributes.update(attributes)

        for callback in self.__state_callbacks.values():
            if callback.entity != name:
                continue
            with ErrorHandler(self, callback.app):
                if callback.attribute is None:
                    old_state = old["state"]
                    if callback.old is not None and old_state != callback.old:
                        continue
                    if callback.new is not None and data.state != callback.new:
                        continue
                    callback.callback(name, None, old_state, data.state, {})
                elif callback.attribute == "all":
                    callback.callback(
                        name, callback.attribute, old, data.to_map(), {}
                    )
                else:
                    old_attr = old["attributes"].get(callback.attribute)
                    new_attr = data.attributes.get(callback.attribute)
                    if callback.old is not None and old_attr != callback.old:
                        continue
                    if callback.new is not None and new_attr != callback.new:
                        continue
                    callback.callback(
                        name, callback.attribute, old_attr, new_attr, {}
                    )

    def __get_id(self) -> int:
        id = self.__state_callback_id
        self.__state_callback_id += 1
        return id

    def listen_state(
        self,
        callback: StateCallbackRecord,
    ) -> int:
        id = self.__get_id()
        self.__state_callbacks[id] = callback
        return id

    def cancel_listen_state(self, id: int) -> None:
        del self.__state_callbacks[id]

    def __sort_tasks(self) -> None:
        self.__scheduled_task_order.sort(
            key=lambda i: self.__scheduled_tasks[i].time, reverse=True
        )

    def schedule_task(self, task: ScheduledTask) -> int:
        id = self.__get_id()
        self.__scheduled_tasks[id] = task
        self.__sort_tasks()
        return id

    def cancel_timer(self, id: int) -> None:
        del self.__scheduled_tasks[id]
        self.__scheduled_task_order.remove(id)

    def datetime(self) -> datetime:
        return self.__datetime

    def has_error(self) -> bool:
        return self.__has_error

    def log(self, app: str, msg: str, level: LogLevel) -> None:
        print("[{}] {}: {}".format(level, app, msg))
        if level == "CRITICAL" or level == "ERROR":
            self.__has_error = True

    def step(self, delta: timedelta) -> None:
        self.__datetime += delta
        while len(self.__scheduled_task_order) != 0:
            id = self.__scheduled_task_order[-1]
            task = self.__scheduled_tasks[id]
            if task.time > self.__datetime:
                break

            with ErrorHandler(self, task.app):
                task.callback({})

            del self.__scheduled_tasks[id]
            _ = self.__scheduled_task_order.pop()
            if task.repeat is not None:
                _ = self.schedule_task(
                    ScheduledTask(
                        app=task.app,
                        time=task.time + task.repeat,
                        callback=task.callback,
                        repeat=task.repeat,
                    )
                )

    def advance_time_to(self, target: datetime, delta: timedelta) -> None:
        while self.__datetime < target:
            self.step(delta)

    def advance_time(self, amount: timedelta, delta: timedelta) -> None:
        self.advance_time_to(self.__datetime + amount, delta)


class Hass:
    def __init__(self):
        self.__manager: AppManager | None = None
        self.__name = ""
        self.args: dict[str, Any] = {}

    def initialize(self):
        pass

    def terminate(self):
        pass

    def init_app(
        self, manager: AppManager, name: str, args: dict[str, Any]
    ) -> None:
        self.__manager = manager
        self.__name = name
        self.args = args
        self.initialize()

    def get_app(self, name: str) -> Hass | None:
        assert self.__manager is not None
        return self.__manager.get_app(name)

    def datetime(self) -> datetime:
        assert self.__manager is not None
        return self.__manager.datetime()

    def get_state(self, name: str) -> str | dict[str, str] | None:
        assert self.__manager is not None
        return self.__manager.get_state(name)

    def set_state(
        self,
        name: str,
        state: str | None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        assert self.__manager is not None
        self.__manager.set_state(name, state, attributes)

    def listen_state(
        self,
        callback: StateCallback,
        entity: str,
        attribute: str | None = None,
        old: str | None = None,
        new: str | None = None,
    ) -> int:
        assert self.__manager is not None
        return self.__manager.listen_state(
            StateCallbackRecord(
                app=self.__name,
                callback=callback,
                entity=entity,
                attribute=attribute,
                old=old,
                new=new,
            )
        )

    def cancel_listen_state(self, id: int) -> None:
        assert self.__manager is not None
        self.__manager.cancel_listen_state(id)

    def run_in(self, callback: SchedulerChallback, delay: int) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=self.datetime() + timedelta(seconds=delay),
                callback=callback,
                repeat=None,
            )
        )

    def run_at(self, callback: SchedulerChallback, when: datetime) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=when,
                callback=callback,
                repeat=None,
            )
        )

    def run_every(
        self, callback: SchedulerChallback, when: datetime, repeat: int
    ) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=when,
                callback=callback,
                repeat=timedelta(seconds=repeat),
            )
        )

    def cancel_timer(self, id: int) -> None:
        assert self.__manager is not None
        self.__manager.cancel_timer(id)

    def log(self, msg: str, level: LogLevel = "INFO") -> None:
        assert self.__manager is not None
        self.__manager.log(self.__name, msg, level)

    def error(self, msg: str, level: LogLevel = "ERROR") -> None:
        assert self.__manager is not None
        self.__manager.log(self.__name, msg, level)
