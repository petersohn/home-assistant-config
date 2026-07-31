from __future__ import annotations
import hass
import locker
from typing import Any, cast


class HistoryWatcher(hass.Hass):
    state_history: list[tuple[str, Any]] = []
    entities: list[str] | None = None
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    def initialize(self) -> None:
        self.state_history = []
        self.entities = self.args.get("entities")
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("TestApp")
        assert self.entities is not None
        with self.mutex.lock("init"):
            for entity in self.entities:
                self.listen_state(self.on_change, entity)

    def on_change(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_change"):
            self.log(f"{entity} = {new}")
            self.state_history.append((entity, new))

    def get_state_history(self) -> list[tuple[str, Any]]:
        with self.mutex.lock("get_state_history"):
            result = self.state_history
            self.state_history = []
            return result

    def has_history(self, history: list[tuple[str, Any]]) -> bool:
        assert len(history) != 0
        with self.mutex.lock("get_history"):
            i = 0
            for item in self.state_history:
                if item == tuple(history[i]):
                    i += 1
                    if i == len(history):
                        return True
            return False
