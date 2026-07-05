from __future__ import annotations
import datetime
import hass
from typing import Any, Callable


class Enabler(hass.Hass):
    def initialize(self) -> None:
        self.callbacks: dict[int, Callable[[], None]] = {}
        self.delay: datetime.timedelta | None = None
        if "delay" in self.args:
            self.delay = datetime.timedelta(**self.args["delay"])
        self.callback_id = 0
        self.state: bool | None = None
        self.change_state: bool | None = None
        self.change_timer: hass.TimerHandle | None = None
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.state_mutex = locker_app.get_mutex("Enabler.State")
        self.callbacks_mutex = locker_app.get_mutex("Enabler.Callbacks")

    def _init_enabler(self, state: bool | None) -> None:
        self.state = state
        self.log("Init: {}".format(self.state))

    def terminate(self) -> None:
        if self.change_timer is not None:
            self.cancel_timer(self.change_timer)  # type: ignore[arg-type]

    def get_callbacks(self) -> list[Callable[[], None]]:
        with self.callbacks_mutex.lock("get_callbacks"):
            return list(self.callbacks.values())

    def call_callbacks(self, callbacks: list[Callable[[], None]]) -> None:
        for callback in callbacks:
            callback()

    # This must not be called from within a callback!
    def change(self, state: bool) -> None:
        if self.delay is None:
            callbacks = self.get_callbacks()
            with self.state_mutex.lock("change"):
                self._do_change(state)
            self.call_callbacks(callbacks)
            return

        with self.state_mutex.lock("change"):
            self.log("change={} delay={}".format(state, self.delay))
            if self.change_timer is not None:
                if self.change_state == state:
                    self.log("no change")
                    return
                self.cancel_timer(self.change_timer)  # type: ignore[arg-type]
                self.change_timer = None
            self.change_state = state
            self.change_timer = self.run_in(
                self.on_timeout, self.delay.total_seconds()
            )

    def _do_change(self, state: bool | None) -> None:
        if self.state != state:
            self.log("state change {} -> {}".format(self.state, state))
            self.state = state

    def on_timeout(self, kwargs: dict[str, Any]) -> None:
        callbacks = self.get_callbacks()
        with self.state_mutex.lock("on_timeout"):
            self.log(
                "timeout state={} callbacks={}".format(
                    self.change_state, len(callbacks)
                )
            )
            self._do_change(self.change_state)
            self.change_state = None
            self.change_timer = None
        self.call_callbacks(callbacks)

    def add_callback(self, func: Callable[[], None]) -> int:
        with self.callbacks_mutex.lock("add_callback"):
            id = self.callback_id
            self.callbacks[id] = func
            self.callback_id += 1
            self.log("add_callback={}".format(id))
            return id

    def remove_callback(self, id: int) -> None:
        with self.callbacks_mutex.lock("remove_callback"):
            self.log("remove_callback={}".format(id))
            del self.callbacks[id]

    def is_enabled(self) -> bool:
        with self.state_mutex.lock("is_enabled"):
            return self.state is True


class ScriptEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        self._init_enabler(self.args.get("initial", True))

    def enable(self) -> None:
        self.change(True)

    def disable(self) -> None:
        self.change(False)


class EntityEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        self._entity: str = self.args["entity"]
        self.listen_state(self._on_change, entity_id=self._entity)
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("EntityEnabler")
        self._init_enabler(self._get())

    def _on_change(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("_on_change"):
            value = self._get()
            self.log(
                "state change {}: {} -> {} value={}".format(
                    entity, old, new, value
                )
            )
            self.change(value)

    def _get(self) -> bool:
        return False


class ValueEnabler(EntityEnabler):
    def initialize(self) -> None:
        self.values: list[str] | None = self.args.get("values")
        if not self.values:
            self.values = [self.args["value"]]
        super().initialize()

    def _get(self) -> bool:
        assert self.values is not None
        return self.get_state(self._entity) in self.values


def is_between(
    value: Any, min_value: float | None, max_value: float | None
) -> bool:
    if min_value is not None and float(value) < min_value:
        return False
    if max_value is not None and float(value) > max_value:
        return False
    return True


class RangeEnabler(EntityEnabler):
    def initialize(self) -> None:
        self.__min: float | None = self.args.get("min")
        self.__max: float | None = self.args.get("max")
        super().initialize()

    def _get(self) -> bool:
        value = self.get_state(self._entity)
        return is_between(value, self.__min, self.__max)


class DateEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        self.begin: datetime.date = datetime.datetime.strptime(
            self.args["begin"], "%m-%d"
        ).date()
        self.end: datetime.date = datetime.datetime.strptime(
            self.args["end"], "%m-%d"
        ).date()
        self._init_enabler(self._get())
        self.run_daily(
            lambda _: self.change(self._get()), datetime.time(0, 0, 1)
        )

    def _get(self) -> bool:
        now = self.date()
        begin = datetime.date(now.year, self.begin.month, self.begin.day)
        end = datetime.date(now.year, self.end.month, self.end.day)
        if begin <= end:
            return begin <= now <= end
        else:  # begin > end
            return now >= begin or now <= end


class HistoryEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        self._init_enabler(None)
        self.min: float | None = self.args.get("min")
        self.max: float | None = self.args.get("max")
        import history
        self.aggregator = history.Aggregator(self, self.on_value)

    def on_value(self, value: float) -> None:
        enabled = is_between(value, self.min, self.max)
        self.change(enabled)


class MultiEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        self.enablers: list[Enabler] = []
        for name in self.args.get("enablers") or []:
            app = self.get_app(name)
            assert isinstance(app, Enabler)
            self.enablers.append(app)
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("MultiEnabler")
        self._init_enabler(self.__get())
        self.ids: list[int] = []
        for enabler in self.enablers:
            self.ids.append(
                enabler.add_callback(lambda: self._on_change())
            )

    def terminate(self) -> None:
        for enabler, id in zip(self.enablers, self.ids):
            enabler.remove_callback(id)

    def _on_change(self) -> None:
        self.run_in(self.get, 0)

    def get(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("get"):
            self.change(self.__get())

    def __get(self) -> bool:
        return all([enabler.is_enabled() for enabler in self.enablers])


class ExpressionEnabler(Enabler):
    def initialize(self) -> None:
        super().initialize()
        import expression
        self.evaluator = expression.ExpressionEvaluator(
            self, self.args["expr"], self.change
        )
        self._init_enabler(self.evaluator.get())

    def terminate(self) -> None:
        self.evaluator.cleanup()
