from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, date, time
from inspect import Traceback
from typing import Any, Callable, Literal, NamedTuple
from traceback import format_exception
import os


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
        ("kwargs", dict[str, Any]),
    ],
)

ServiceKey = NamedTuple("ServiceKey", [("service", str), ("entity_id", str)])
ServiceCallback = Callable[[dict[str, Any]], None]
ServiceData = NamedTuple(
    "ServiceData", [("app", str), ("callback", ServiceCallback)]
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
    def __init__(self, begin_time: datetime, log_filename: str):
        self.__apps: dict[str, Hass] = {}
        self.__app_order: list[str] = []
        self.__states: dict[str, State] = {}
        self.__state_callbacks: dict[int, StateCallbackRecord] = {}
        self.__state_callback_id = 0
        self.__datetime = begin_time
        self.__scheduled_tasks: dict[int, ScheduledTask] = {}
        self.__scheduled_task_order: list[int] = []
        self.__has_error = False
        self.__log_filename = log_filename
        self.__services: dict[ServiceKey, ServiceData] = {}

        if os.path.exists(log_filename):
            os.remove(log_filename)
        else:
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)

    def create_app(
        self,
        library_name: str,
        class_name: str,
        app_name: str,
        **kwargs: Any,
    ) -> Hass:
        library = __import__(library_name)
        class_ = getattr(library, class_name)
        obj = class_()
        self.add_app(app_name, obj, kwargs)
        return obj

    def add_app(self, name: str, app: Hass, args: dict[str, Any]) -> None:
        if name in self.__apps:
            raise RuntimeError("App already exists: {}".format(name))
        app.init_app(self, name, args)
        self.__apps[name] = app
        self.__app_order.append(name)

    def remove_app(self, name: str) -> None:
        self.__debug("Remove app: {}".format(name))
        app = self.__apps[name]
        del self.__apps[name]
        self.__app_order = list(filter(lambda a: a != name, self.__app_order))

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

        for key in [
            key for key, value in self.__services.items() if value.app == name
        ]:
            self.unregister_service(key)

        with ErrorHandler(self, name):
            app.do_terminate()

    def remove_all_apps(self) -> None:
        while len(self.__app_order) != 0:
            self.remove_app(self.__app_order[-1])
        assert len(self.__apps) == 0

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
            return data.to_map()
        return data.attributes.get(attribute)

    def set_state(
        self,
        app: str,
        name: str,
        state: str | None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        data = self.__states.setdefault(name, State())
        old = data.to_map()
        data.state = None if state is None else str(state)

        if attributes is not None:
            data.attributes.update(attributes)

        new = data.to_map()
        self.__debug("Set state {} by {}: {}".format(name, app, new))

        for id, callback in self.__state_callbacks.items():
            if callback.entity != name:
                continue

            def call_callback(
                f: StateCallback,
                name: str,
                attribute: str | None,
                old: str | None,
                new: str | None,
            ):
                f(name, attribute, old, new, {})

            def schedule_call(
                f: StateCallback,
                attribute: str | None,
                old: str | None,
                new: str | None,
            ):
                self.__debug(
                    "Schedule state change callback {} for {}".format(id, app)
                )
                _ = self.schedule_task(
                    ScheduledTask(
                        app=app,
                        time=self.__datetime,
                        callback=lambda _: call_callback(
                            f, name, attribute, old, new
                        ),
                        repeat=None,
                        kwargs={},
                    )
                )

            if callback.attribute is None:
                old_state = old["state"]
                if (
                    data.state != old_state
                    and (callback.old is None or old_state == callback.old)
                    and (callback.new is None or data.state == callback.new)
                ):
                    schedule_call(
                        callback.callback, None, old_state, data.state
                    )
            elif callback.attribute == "all":
                if old != new:
                    schedule_call(
                        callback.callback, callback.attribute, old, new
                    )
            else:
                old_attr = old["attributes"].get(callback.attribute)
                new_attr = data.attributes.get(callback.attribute)
                if (
                    old_attr != new_attr
                    and (callback.old is None or old_attr == callback.old)
                    and (callback.new is None or new_attr == callback.new)
                ):
                    schedule_call(
                        callback.callback,
                        callback.attribute,
                        old_attr,
                        new_attr,
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
        self.__debug(
            "Listen state {} by {}: {}".format(
                callback.entity, callback.app, id
            )
        )
        self.__state_callbacks[id] = callback
        return id

    def cancel_listen_state(self, id: int) -> None:
        if id in self.__state_callbacks:
            del self.__state_callbacks[id]

    def __calculate_scheduled_task_order(self):
        self.__scheduled_task_order = list(self.__scheduled_tasks.keys())
        self.__scheduled_task_order.sort(
            key=lambda i: self.__scheduled_tasks[i].time, reverse=True
        )

    def __schedule_task(self, id: int, task: ScheduledTask) -> None:
        self.__debug(
            "schedule task {} at {}".format(id, task.time.strftime("%H:%M:%S"))
        )
        self.__scheduled_tasks[id] = task
        self.__calculate_scheduled_task_order()

    def schedule_task(self, task: ScheduledTask) -> int:
        id = self.__get_id()
        self.__schedule_task(id, task)
        return id

    def cancel_timer(self, id: int) -> None:
        self.__debug("Cancel timer {}".format(id))
        if id in self.__scheduled_tasks:
            del self.__scheduled_tasks[id]
        else:
            self.__debug("No such timer.")
        self.__calculate_scheduled_task_order()

    def datetime(self) -> datetime:
        return self.__datetime

    def has_error(self) -> bool:
        return self.__has_error

    def log(self, app: str, msg: str, level: LogLevel) -> None:
        line = "{} [{}] {}: {}".format(
            self.__datetime.strftime("%Y-%m-%d %H:%M:%S"), level, app, msg
        )
        print(line)
        with open(self.__log_filename, "a") as f:
            print(line, file=f)
        if level == "CRITICAL" or level == "ERROR":
            self.__has_error = True

    def __debug(self, msg: str) -> None:
        self.log("AppManager", msg, "DEBUG")

    def step(self, delta: timedelta) -> None:
        self.__datetime += delta
        self.call_pending_callbacks()

    def call_pending_callbacks(self):
        while len(self.__scheduled_task_order) != 0:
            id = self.__scheduled_task_order[-1]
            task = self.__scheduled_tasks[id]
            if task.time > self.__datetime:
                break

            self.__debug(
                "Execute scheduled task {} for {}".format(id, task.app)
            )

            if task.repeat is not None:
                self.__schedule_task(
                    id,
                    ScheduledTask(
                        app=task.app,
                        time=task.time + task.repeat,
                        callback=task.callback,
                        repeat=task.repeat,
                        kwargs=task.kwargs,
                    ),
                )
            else:
                del self.__scheduled_tasks[id]
                self.__calculate_scheduled_task_order()

            with ErrorHandler(self, task.app):
                task.callback(task.kwargs)

    def advance_time_to(self, target: datetime, delta: timedelta) -> None:
        while self.__datetime < target:
            self.step(delta)

    def advance_time(self, amount: timedelta, delta: timedelta) -> None:
        self.advance_time_to(self.__datetime + amount, delta)

    def wait_for_state_change(
        self,
        entity: str,
        deadline: datetime | None,
        delta: timedelta,
        old: str | None = None,
        new: str | None = None,
    ) -> None:
        current_state = self.get_state(entity)
        self.__debug("Wait for state change current={}".format(current_state))

        step_count = 0
        while not deadline or self.__datetime < deadline:
            self.step(delta)

            state = self.get_state(entity)
            if state != current_state:
                self.__debug(
                    "{}: {} -> {}".format(entity, current_state, state)
                )
            if (
                state != current_state
                and (old is None or current_state == old)
                and (new is None or state == new)
            ):
                break

            current_state = state
            step_count += 1
            if step_count >= 10000:
                raise RuntimeError("State did not change in time")

    def register_service(
        self, app: str, key: ServiceKey, callback: ServiceCallback
    ) -> None:
        if key in self.__services:
            raise RuntimeError("Service already registered: {}".format(key))
        self.__services[key] = ServiceData(app=app, callback=callback)

    def unregister_service(self, key: ServiceKey) -> None:
        if key not in self.__services:
            raise RuntimeError("Service not registered: {}".format(key))
        del self.__services[key]

    def call_service(
        self, _app: str, key: ServiceKey, data: dict[str, Any]
    ) -> None:
        service = self.__services[key]
        service.callback(data)


class Hass:
    def __init__(self):
        self.__manager: AppManager | None = None
        self.__name = ""
        self.args: dict[str, Any] = {}

    def do_initialize(self):
        pass

    def do_terminate(self):
        pass

    def init_app(
        self, manager: AppManager, name: str, args: dict[str, Any]
    ) -> None:
        self.__manager = manager
        self.__name = name
        self.args = args
        self.do_initialize()

    def get_app(self, name: str) -> Hass | None:
        assert self.__manager is not None
        return self.__manager.get_app(name)

    def datetime(self) -> datetime:
        assert self.__manager is not None
        return self.__manager.datetime()

    def date(self) -> date:
        return self.datetime().date()

    def time(self) -> time:
        return self.datetime().time()

    def get_state(
        self, entity_id: str, attribute: str | None = None
    ) -> str | dict[str, str] | None:
        assert self.__manager is not None
        return self.__manager.get_state(entity_id, attribute)

    def set_state(
        self,
        entity_id: str,
        state: str | None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        assert self.__manager is not None
        self.__manager.set_state(self.__name, entity_id, state, attributes)

    def select_option(self, entity_id: str, option: str) -> None:
        assert self.__manager is not None
        self.__manager.set_state(self.__name, entity_id, option)

    def turn_on(self, entity_id: str) -> None:
        assert self.__manager is not None
        self.__manager.set_state(self.__name, entity_id, "on")

    def turn_off(self, entity_id: str) -> None:
        assert self.__manager is not None
        self.__manager.set_state(self.__name, entity_id, "off")

    def listen_state(
        self,
        callback: StateCallback,
        entity_id: str,
        attribute: str | None = None,
        old: str | None = None,
        new: str | None = None,
    ) -> int:
        assert self.__manager is not None
        return self.__manager.listen_state(
            StateCallbackRecord(
                app=self.__name,
                callback=callback,
                entity=entity_id,
                attribute=attribute,
                old=old,
                new=new,
            )
        )

    def cancel_listen_state(self, id: int) -> None:
        assert self.__manager is not None
        self.__manager.cancel_listen_state(id)

    def run_in(
        self, callback: SchedulerChallback, delay: int, **kwargs: Any
    ) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=self.datetime() + timedelta(seconds=delay),
                callback=callback,
                repeat=None,
                kwargs=kwargs,
            )
        )

    def run_at(
        self, callback: SchedulerChallback, when: datetime, **kwargs: Any
    ) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=when,
                callback=callback,
                repeat=None,
                kwargs=kwargs,
            )
        )

    def run_every(
        self,
        callback: SchedulerChallback,
        when: datetime,
        repeat: int,
        **kwargs: Any,
    ) -> int:
        assert self.__manager is not None
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=when,
                callback=callback,
                repeat=timedelta(seconds=repeat),
                kwargs=kwargs,
            )
        )

    def run_daily(
        self, callback: SchedulerChallback, when: time, **kwargs: Any
    ) -> int:
        assert self.__manager is not None
        next = datetime.combine(self.date(), when)
        if next < self.datetime():
            next += timedelta(days=1)
        return self.__manager.schedule_task(
            ScheduledTask(
                app=self.__name,
                time=next,
                callback=callback,
                repeat=timedelta(days=1),
                kwargs=kwargs,
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

    def load_history(self, _entity_id: str, _max_interval: timedelta) -> Any:
        return {}

    def load_states(self, entity_id: str) -> dict[str, Any]:
        state = self.get_state(entity_id, attribute="all")
        if state is None:
            raise RuntimeError("Entity not found: {}".format(entity_id))
        assert type(state) is dict

        now = self.datetime().strftime("%Y-%m-%dT%H:%M:%S")
        state["entity_id"] = entity_id
        state["last_changed"] = now
        state["last_reported"] = now
        state["last_updated"] = now
        return state

    def _register_service(
        self, service: str, entity_id: str, callback: ServiceCallback
    ) -> None:
        assert self.__manager is not None
        self.__manager.register_service(
            self.__name,
            ServiceKey(service=service, entity_id=entity_id),
            callback,
        )

    def call_service(self, service: str, entity_id: str, **kwargs: Any) -> None:
        assert self.__manager is not None
        self.__manager.call_service(
            self.__name,
            ServiceKey(service=service, entity_id=entity_id),
            kwargs,
        )
