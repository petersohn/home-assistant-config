from __future__ import annotations
from collections import namedtuple
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, NamedTuple, Callable


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
        ("callback", StateCallback),
        ("entity", str),
        ("attribute", str | None),
        ("old", str | None),
        ("new", str | None),
    ],
)

SchedulerChallback = Callable[[dict[str, Any]], None]

ScheduledTask = NamedTuple(
    "ScheduledTask", [("time", datetime), ("callback", SchedulerChallback)]
)


class AppManager:
    def __init__(self, begin_time: datetime):
        self.__apps: dict[str, Hass] = {}
        self.__states: dict[str, State] = {}
        self.__state_callbacks: dict[int, StateCallbackRecord] = {}
        self.__state_callback_id = 0
         self.__time = begin_time
         self.__scheduled_tasks: list[ScheduledTask] = []

    def add_app(self, name: str, app: Hass, args: dict[str, Any]) -> None:
        app.init_app(self, args)
        self.__apps[name] = app

    def get_app(self, name: str) -> Hass:
        return self.__apps[name]

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
        self, name: str, state: str | None, attributes: dict[str, str] | None = None
    ):
        data = self.__states.setdefault(name, State())
        old = data.to_map()
        data.state = None if state is None else str(state)

        if attributes is not None:
            data.attributes.update(attributes)

        for callback in self.__state_callbacks.values():
            if callback.entity != name:
                continue
            if callback.attribute is None:
                old_state = old["state"]
                if callback.old is not None and old_state != callback.old:
                    continue
                if callback.new is not None and data.state != callback.new:
                    continue
                callback.callback(name, None, old_state, data.state, {})
            elif callback.attribute == "all":
                callback.callback(name, callback.attribute, old, data.to_map(), {})
            else:
                old_attr = old["attributes"].get(callback.attribute)
                new_attr = data.attributes.get(callback.attribute)
                if callback.old is not None and old_attr != callback.old:
                    continue
                if callback.new is not None and new_attr != callback.new:
                    continue
                callback.callback(name, callback.attribute, old_attr, new_attr, {})

    def listen_state(
        self,
        callback: StateCallback,
        entity: str,
        attribute: str | None = None,
        old: str | None = None,
        new: str | None = None,
    ):
        id = self.__state_callback_id
        self.__state_callback_id += 1
        self.__state_callbacks[id] = StateCallbackRecord(
            callback, entity, attribute, new, old
        )

    def cancel_listen_state(self, id: int):
        del self.__state_callbacks[id]


class Hass:
    def __init__(self):
        self.__manager: AppManager | None = None
        self.args: dict[str, Any] = {}

    def init_app(self, manager: AppManager, args: dict[str, Any]):
        self.__manager = manager
        self.args = args

    def get_app(self, name: str):
        assert self.__manager is not None
        return self.__manager.get_app(name)

    def get_state(self, name: str):
        assert self.__manager is not None
        return self.__manager.get_state(name)

    def set_state(
        self, name: str, state: str | None, attributes: dict[str, str] | None = None
    ):
        assert self.__manager is not None
        self.__manager.set_state(name, state, attributes)

    def listen_state(
        self,
        callback: StateCallback,
        entity: str,
        attribute: str | None = None,
        old: str | None = None,
        new: str | None = None,
    ):
        assert self.__manager is not None
        self.__manager.listen_state(callback, entity, attribute, old, new)

    def cancel_listen_state(self, id: int):
        assert self.__manager is not None
        self.__manager.cancel_listen_state(id)
