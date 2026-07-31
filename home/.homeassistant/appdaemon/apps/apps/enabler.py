from __future__ import annotations
import datetime
import hass
from hass_common import EntityValue
from typing import Any, Callable, override, TYPE_CHECKING, cast

if TYPE_CHECKING:
    import locker


class Enabler(hass.Hass):
    callbacks: dict[int, Callable[[], None]] = {}
    delay: datetime.timedelta | None = None
    callback_id: int = 0
    state: bool | None = None
    change_state: bool | None = None
    change_timer: str | None = None
    state_mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))
    callbacks_mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    def initialize(self) -> None:
        self.callbacks = {}
        self.delay = None
        if "delay" in self.args:
            self.delay = datetime.timedelta(**self.args["delay"])
        self.callback_id = 0
        self.state = None
        self.change_state = None
        self.change_timer = None
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.state_mutex = locker_app.get_mutex("Enabler.State")
        self.callbacks_mutex = locker_app.get_mutex("Enabler.Callbacks")

    def _init_enabler(self, state: bool | None) -> None:
        self.state = state
        self.log(f"Init: {self.state}")

    def terminate(self) -> None:
        if self.change_timer is not None:
            self.cancel_timer(self.change_timer)

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
            self.log(f"change={state} delay={self.delay}")
            if self.change_timer is not None:
                if self.change_state == state:
                    self.log("no change")
                    return
                self.cancel_timer(self.change_timer)
                self.change_timer = None
            self.change_state = state
            self.change_timer = self.run_in(
                self.on_timeout, self.delay.total_seconds()
            )

    def _do_change(self, state: bool | None) -> None:
        if self.state != state:
            self.log(f"state change {self.state} -> {state}")
            self.state = state

    def on_timeout(self, kwargs: dict[str, Any]) -> None:
        callbacks = self.get_callbacks()
        with self.state_mutex.lock("on_timeout"):
            self.log(
                f"timeout state={self.change_state} callbacks={len(callbacks)}"
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
            self.log(f"add_callback={id}")
            return id

    def remove_callback(self, id: int) -> None:
        with self.callbacks_mutex.lock("remove_callback"):
            self.log(f"remove_callback={id}")
            del self.callbacks[id]

    def is_enabled(self) -> bool:
        with self.state_mutex.lock("is_enabled"):
            return self.state is True


class ScriptEnabler(Enabler):
    @override
    def initialize(self) -> None:
        super().initialize()
        self._init_enabler(self.args.get("initial", True))

    def enable(self) -> None:
        self.change(True)

    def disable(self) -> None:
        self.change(False)


class EntityEnabler(Enabler):
    _entity: str = ""
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    @override
    def initialize(self) -> None:
        super().initialize()
        self._entity = self.args["entity"]
        self.listen_state(
            self._on_change, entity_id=self._entity
        )
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("EntityEnabler")
        self._init_enabler(self._get())

    def _on_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("_on_change"):
            value = self._get()
            self.log(
                f"state change {entity}: {old} -> {new} value={value}"
            )
            self.change(value)

    def _get(self) -> bool:
        return False


class ValueEnabler(EntityEnabler):
    values: list[str] | None = None

    @override
    def initialize(self) -> None:
        self.values = self.args.get("values")
        if not self.values:
            self.values = [self.args["value"]]
        super().initialize()

    @override
    def _get(self) -> bool:
        assert self.values is not None
        return self.get_state(self._entity) in self.values


def is_between(
    value: str | float | int, min_value: float | None, max_value: float | None
) -> bool:
    if min_value is not None and float(value) < min_value:
        return False
    if max_value is not None and float(value) > max_value:
        return False
    return True


class RangeEnabler(EntityEnabler):
    __min: float | None = None
    __max: float | None = None

    @override
    def initialize(self) -> None:
        self.__min = self.args.get("min")
        self.__max = self.args.get("max")
        super().initialize()

    @override
    def _get(self) -> bool:
        value = self.get_state(self._entity)
        assert isinstance(value, (str, type(None))), (
            f"Expected str or None from get_state({self._entity!r}), "
            f"got {type(value).__name__}"
        )
        if value is None:
            return False
        return is_between(value, self.__min, self.__max)


class DateEnabler(Enabler):
    begin: datetime.date = cast("datetime.date", cast(Any, None))
    end: datetime.date = cast("datetime.date", cast(Any, None))

    @override
    def initialize(self) -> None:
        super().initialize()
        self.begin = datetime.datetime.strptime(
            self.args["begin"], "%m-%d"
        ).date()
        self.end = datetime.datetime.strptime(
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
    min: float | None = None
    max: float | None = None
    aggregator: Any = None

    @override
    def initialize(self) -> None:
        super().initialize()
        self._init_enabler(None)
        self.min = self.args.get("min")
        self.max = self.args.get("max")
        import history
        self.aggregator = history.Aggregator(self, self.on_value)

    def on_value(self, value: float) -> None:
        enabled = is_between(value, self.min, self.max)
        self.change(enabled)


class MultiEnabler(Enabler):
    enablers: list[Enabler] = []
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))
    ids: list[int] = []

    @override
    def initialize(self) -> None:
        super().initialize()
        self.enablers = []
        enablers: list[str] = self.args.get("enablers", []) or []
        for name in enablers:
            app = self.get_app(name)
            assert isinstance(app, Enabler)
            self.enablers.append(app)
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("MultiEnabler")
        self._init_enabler(self.__get())
        self.ids = []
        for enabler in self.enablers:
            self.ids.append(
                enabler.add_callback(lambda: self._on_change())
            )

    @override
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
    evaluator: Any = None

    @override
    def initialize(self) -> None:
        super().initialize()
        import expression
        self.evaluator = expression.ExpressionEvaluator(
            self,
            self.args["expr"],
            lambda value: self.change(bool(value)),
        )
        self._init_enabler(bool(self.evaluator.get()))

    @override
    def terminate(self) -> None:
        self.evaluator.cleanup()
