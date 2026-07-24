from __future__ import annotations
import time
import requests  # type: ignore[import-untyped]
from typing import Any
from helpers.app_daemon import create_appdaemon_apps_config
from helpers.mutex_graph import append_graph, find_cycle


class AppDaemonClient:
    def __init__(self, host: str, appdaemon_dir: str) -> None:
        self._session = requests.Session()
        self._host = host
        self._dir = appdaemon_dir
        self._loaded_apps: list[str] = []

    def call_function(self, function: str, *args: Any, **kwargs: Any) -> Any:
        result_type = kwargs.pop("result_type", None)
        arg_types = kwargs.pop("arg_types", [])
        kwarg_types = kwargs.pop("kwarg_types", {})
        content = {
            "function": function,
            "result_type": result_type,
            "arg_types": arg_types,
            "kwarg_types": kwarg_types,
            "args": list(args),
            "kwargs": kwargs,
        }
        r = self._session.post(f"http://{self._host}/api/appdaemon/TestApp", json=content)
        r.raise_for_status()
        return r.json()

    def get_state(self, entity_id: str, **kwargs: Any) -> Any:
        return self.call_function("get_state", entity_id, **kwargs)

    def set_state(self, entity_id: str, value: Any, **attributes: Any) -> None:
        self.call_function("set_state", entity_id, state=value, attributes=attributes)

    def turn_on(self, entity_id: str) -> None:
        self.call_function("turn_on", entity_id)

    def turn_off(self, entity_id: str) -> None:
        self.call_function("turn_off", entity_id)

    def select_option(self, entity_id: str, value: str) -> None:
        self.call_function("select_option", entity_id, value)

    def set_value(self, entity_id: str, value: Any) -> None:
        self.call_function("set_value", entity_id, value)

    def call_service(self, service: str, **kwargs: Any) -> None:
        self.call_function("call_service", service, **kwargs)

    def call_on_app(self, app_name: str, function: str, *args: Any, **kwargs: Any) -> Any:
        return self.call_function("call_on_app", app_name, function, *args, **kwargs)

    def log(self, message: str) -> None:
        self.call_function("log", message)

    def wait_for_state(self, entity_id: str, expected: Any, timeout: int = 10) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.get_state(entity_id) == expected:
                return
            time.sleep(0.1)
        assert self.get_state(entity_id) == expected

    def load_apps(self, *configs: str) -> None:
        self._loaded_apps = create_appdaemon_apps_config(self._dir, "TestApp", *configs)
        self._wait_until_loaded(*self._loaded_apps, timeout=30)

    def unload_apps(self) -> None:
        if not self._loaded_apps:
            return
        create_appdaemon_apps_config(self._dir, "TestApp")
        self._wait_until_unloaded(*self._loaded_apps, timeout=30)
        self._loaded_apps = []

    def initialize_states(self, **states: Any) -> None:
        for entity, state in states.items():
            self.call_function("set_state", entity, state=state, attributes={})

    def check_mutex_graph(self, global_mutex_graph: dict[str, Any]) -> None:
        graph = self.call_on_app("locker", "get_global_graph")
        append_graph(global_mutex_graph, graph)
        assert not find_cycle(global_mutex_graph)

    def _wait_until_loaded(self, *apps: str, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.call_function("is_all_apps_loaded", list(apps)):
                return
            time.sleep(0.1)
        assert self.call_function("is_all_apps_loaded", list(apps))

    def _wait_until_unloaded(self, *apps: str, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.call_function("is_all_apps_unloaded", list(apps)):
                return
            time.sleep(0.1)
        assert self.call_function("is_all_apps_unloaded", list(apps))