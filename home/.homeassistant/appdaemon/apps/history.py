from __future__ import annotations
import datetime
import hass
import re
import traceback
from collections import deque
from collections.abc import Callable
from dateutil import tz
from typing import Any, NamedTuple


class HistoryElement(NamedTuple):
    time: datetime.datetime
    value: float


def make_history_element(
    time: datetime.datetime, value: Any
) -> HistoryElement:
    try:
        if value is None or value == "off":
            real_value: float = 0.0
        elif value == "on":
            real_value = 1.0
        else:
            real_value = float(value)
    except ValueError:
        real_value = 0.0
    return HistoryElement(time, real_value)


def get_date(s: str) -> datetime.datetime:
    s = re.sub(r"([-+][0-9]{2}):([0-9]{2})$", "", s)
    try:
        time = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        time = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    return (
        time.replace(tzinfo=tz.tzutc())
        .astimezone(tz.tzlocal())
        .replace(tzinfo=None)
    )


class HistoryManagerBase(hass.Hass):
    def initialize(self) -> None:
        self.changed_callbacks: dict[int, Callable[[], None]] = {}
        self.callback_id = 0
        self.loaded = False
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("HistoryManagerBase")
        self.load_config()

    def add_callback(self, callback: Callable[[], None]) -> int:
        with self.mutex.lock("add_callback"):
            id = self.callback_id
            self.callback_id += 1
            self.changed_callbacks[id] = callback
            return id

    def remove_callback(self, id: int) -> None:
        with self.mutex.lock("add_callback"):
            del self.changed_callbacks[id]

    def changed(self) -> None:
        self.log("callbacks={}".format(len(self.changed_callbacks)))
        for callback in self.changed_callbacks.values():
            callback()

    def is_loaded(self) -> bool:
        return self.loaded

    def load_config_inner(self) -> None:
        raise NotImplementedError()

    def load_config(self, *args: Any, **kwargs: Any) -> None:
        with self.mutex.lock("load_config"):
            self.log("Loading history...")
            try:
                self.load_config_inner()
            except Exception:
                self.error("Failed to load.", level="WARNING")
                self.error(traceback.format_exc(), level="WARNING")
                self.run_in(self.load_config, 2)
                raise
            self.loaded = True


class HistoryManager(HistoryManagerBase):
    def initialize(self) -> None:
        self.max_interval: datetime.timedelta = datetime.timedelta(
            **self.args.get("max_interval", {"days": 1})
        )
        self.entity_id: str = self.args["entity"]
        self.history: deque[HistoryElement] = deque()
        super().initialize()

    def __filter(self) -> None:
        min_time = self.datetime() - self.max_interval
        while len(self.history) >= 2 and self.history[1].time < min_time:
            self.history.popleft()

    def get_recorded_history(self) -> deque[HistoryElement]:
        with self.mutex.lock("get_recorded_history"):
            self.__filter()
            return self.history

    def load_config_inner(self, *args: Any, **kwargs: Any) -> None:
        self.log("Loading history...")
        loaded_history: Any = self.load_history(
            self.entity_id, self.max_interval
        )
        now = self.datetime()
        self.history = deque(
            filter(
                lambda element: element.time <= now
                and element.value is not None,
                (
                    make_history_element(
                        get_date(change["last_changed"]), change["state"]
                    )
                    for changes in loaded_history
                    for change in changes
                ),
            )
        )
        self.log("Total loaded history size: {}".format(len(self.history)))
        self.__filter()
        self.log("Filtered history size: {}".format(len(self.history)))
        self.listen_state(self.on_changed, entity_id=self.entity_id)
        self.log("History loaded.")

    def on_changed(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_changed"):
            if new == old:
                return
            self.__filter()
            self.history.append(
                make_history_element(self.datetime(), new)
            )
            self.changed()


class ChangeTracker(HistoryManagerBase):
    def initialize(self) -> None:
        self.entity_id: str = self.args["entity"]
        self.changed_time: datetime.datetime | None = None
        self.updated_time: datetime.datetime | None = None
        super().initialize()

    def load_config_inner(self) -> None:
        self.log("Loading last change...")
        result = self.load_states(self.entity_id)
        assert isinstance(result, dict)
        self.changed_time = get_date(result["last_changed"])
        self.updated_time = get_date(result["last_updated"])
        self.listen_state(
            self.on_changed, entity_id=self.entity_id, attribute="all"
        )
        self.log("Last change loaded.")

    def last_changed(self) -> datetime.datetime | None:
        with self.mutex.lock("last_changed"):
            return self.changed_time

    def last_updated(self) -> datetime.datetime | None:
        with self.mutex.lock("last_updated"):
            return self.updated_time

    def on_changed(
        self,
        entity: str,
        attribute: str | None,
        old: dict[str, Any],
        new: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_changed"):
            self.log("changed")
            now = self.datetime()
            self.updated_time = now
            if old["state"] != new["state"]:
                self.changed_time = now
            self.changed()


class Aggregatum:
    def __init__(self, app: Any) -> None:
        self.app = app

    def add(self, element: HistoryElement) -> None:
        raise NotImplementedError

    def get(self) -> float | None:
        raise NotImplementedError


class LimitedHistoryAggregatum(Aggregatum):
    def __init__(self, app: Any, interval: datetime.timedelta) -> None:
        super().__init__(app)
        self.interval = interval
        self.history: deque[HistoryElement] = deque()

    def add(self, element: HistoryElement) -> None:
        if not self.adding(element):
            self.history.append(element)
        minimum_time = element.time - self.interval
        while (
            len(self.history) >= 2
            and self.history[1].time <= minimum_time
        ):
            removed_element = self.history.popleft()
            self.removed(removed_element)
        if self.history[0].time < minimum_time:
            old_element = self.history[0]
            self.history[0] = HistoryElement(
                minimum_time, self.history[0].value
            )
            self.trimmed(old_element)

    def adding(self, element: HistoryElement) -> bool:
        return False

    def removed(self, element: HistoryElement) -> None:
        pass

    def trimmed(self, element: HistoryElement) -> None:
        pass


class Minmax(LimitedHistoryAggregatum):
    def __init__(
        self,
        app: Any,
        interval: datetime.timedelta,
        function: Callable[..., Any],
    ) -> None:
        super().__init__(app, interval)
        self.value: float | None = None
        self.function = function

    def adding(self, element: HistoryElement) -> bool:
        if self.value is None:
            if self.history:
                self._reevaluate()
            else:
                self.value = element.value
        self.value = self.function(self.value, element.value)
        return False

    def removed(self, element: HistoryElement) -> None:
        if self.value is not None and abs(element.value - self.value) < 0.0001:
            self._reevaluate()

    def _reevaluate(self) -> None:
        self.value = self.function([e.value for e in self.history])

    def get(self) -> float:
        if self.value is None:
            raise ValueError
        return self.value


class Sum(LimitedHistoryAggregatum):
    def __init__(self, app: Any, interval: datetime.timedelta) -> None:
        super().__init__(app, interval)
        self.value = 0.0
        self.last: float | None = None

    def adding(self, element: HistoryElement) -> bool:
        if self.last is not None and element.value == self.last:
            return True
        self.value += element.value
        self.last = element.value
        return False

    def removed(self, element: HistoryElement) -> None:
        self.value -= element.value

    def get(self) -> float:
        return self.value


class IntervalAggragatum(LimitedHistoryAggregatum):
    def __init__(self, app: Any, interval: datetime.timedelta) -> None:
        super().__init__(app, interval)

    def adding(self, element: HistoryElement) -> bool:
        if self.history:
            interval = element.time - self.history[-1].time
            self.add_interval(interval, self.history[-1].value)
        return False

    def removed(self, element: HistoryElement) -> None:
        self._remove(element)

    def trimmed(self, element: HistoryElement) -> None:
        self._remove(element)

    def _remove(self, element: HistoryElement) -> None:
        interval = self.history[0].time - element.time
        self.remove_interval(interval, element.value)

    def add_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        raise NotImplementedError

    def remove_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        raise NotImplementedError


class Integral(IntervalAggragatum):
    def __init__(
        self,
        app: Any,
        interval: datetime.timedelta,
        base_interval: datetime.timedelta,
    ) -> None:
        super().__init__(app, interval)
        self.base_interval = base_interval
        self.sum = 0.0

    def get(self) -> float:
        return self.sum

    def add_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        seconds = interval / self.base_interval
        self.sum += value * seconds

    def remove_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        seconds = interval / self.base_interval
        self.sum -= value * seconds


class Mean(IntervalAggragatum):
    def __init__(self, app: Any, interval: datetime.timedelta) -> None:
        super().__init__(app, interval)
        self.sum = 0.0
        self.time = 0.0

    def get(self) -> float:
        if self.time == 0.0:
            raise ValueError
        return self.sum / self.time

    def add_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        seconds = interval.total_seconds()
        self.sum += value * seconds
        self.time += seconds

    def remove_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        seconds = interval.total_seconds()
        self.sum -= value * seconds
        self.time -= seconds


class Anglemean(IntervalAggragatum):
    def __init__(self, app: Any, interval: datetime.timedelta) -> None:
        super().__init__(app, interval)
        self.sum180 = 0.0
        self.sum360 = 0.0
        self.sum360_2 = 0.0
        self.sum180_2 = 0.0
        self.time = 0.0

    def get(self) -> float:
        if self.time == 0.0:
            raise ValueError
        varsum180 = self.sum180_2 - (self.sum180**2) / self.time
        varsum360 = self.sum360_2 - (self.sum360**2) / self.time
        if varsum180 < varsum360:
            result = self.sum180 / self.time
            if result < 0:
                result += 360
            return result
        else:
            return self.sum360 / self.time

    def add_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        value360 = value % 360
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.sum180 += value180 * seconds
        self.sum180_2 += (value180**2) * seconds
        self.sum360 += value360 * seconds
        self.sum360_2 += (value360**2) * seconds
        self.time += seconds

    def remove_interval(
        self, interval: datetime.timedelta, value: float
    ) -> None:
        value360 = value % 360
        value180 = value - 360 if value > 180 else value
        seconds = interval.total_seconds()
        self.sum180 -= value180 * seconds
        self.sum180_2 -= (value180**2) * seconds
        self.sum360 -= value360 * seconds
        self.sum360_2 -= (value360**2) * seconds
        self.time -= seconds


class DecaySum(Aggregatum):
    def __init__(
        self,
        app: Any,
        interval: datetime.timedelta,
        fraction: float,
    ) -> None:
        super().__init__(app)
        self.interval = interval.total_seconds()
        self.fraction = fraction
        self.value: float | None = None
        self.last: float | None = None
        self.time: datetime.datetime | None = None

    def add(self, element: HistoryElement) -> None:
        if self.time is None:
            self.time = element.time
            self.value = element.value
            return

        assert self.value is not None
        current: float = self.value
        diff = (element.time - self.time).total_seconds()
        current *= self.fraction ** (diff / self.interval)
        if self.last != element.value:
            current += element.value
            self.last = element.value
        self.value = current
        self.time = element.time

    def get(self) -> float | None:
        return self.value


class Aggregator:
    def __init__(self, app: Any, callback: Callable[[float], None]) -> None:
        import locker
        locker_app = app.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("Aggregator")
        self.app = app
        self.base_interval: datetime.timedelta = datetime.timedelta(
            **app.args.get("base_interval", {"minutes": 1})
        )
        self.aggregatum: Aggregatum = self.get_aggregatum(
            app.args["aggregator"]
        )
        self.callback = callback
        self.timer: hass.TimerHandle | None = None

        manager = app.get_app(app.args["manager"])
        assert isinstance(manager, HistoryManager)
        self.manager = manager
        history = self.manager.get_recorded_history()
        for element in history:
            self.aggregatum.add(element)
        if not history:
            element = make_history_element(
                self.app.datetime(),
                self.app.get_state(self.manager.entity_id),
            )
            self.aggregatum.add(element)

        app.listen_state(self.on_change, entity_id=self.manager.entity_id)
        with self.mutex.lock("init"):
            self.__start_timer()
            self.__set_state()

    def get_aggregatum(self, name: str) -> Aggregatum:
        def get_interval() -> datetime.timedelta:
            return datetime.timedelta(**self.app.args["interval"])

        aggregators: dict[str, Callable[[], Aggregatum]] = {
            "min": lambda: Minmax(self.app, get_interval(), min),
            "max": lambda: Minmax(self.app, get_interval(), max),
            "sum": lambda: Sum(self.app, get_interval()),
            "integral": lambda: Integral(
                self.app, get_interval(), self.base_interval
            ),
            "mean": lambda: Mean(self.app, get_interval()),
            "anglemean": lambda: Anglemean(self.app, get_interval()),
            "decay_sum": lambda: DecaySum(
                self.app, get_interval(), self.app.args["fraction"]
            ),
        }
        return aggregators[name]()

    def __set_state(self) -> None:
        try:
            value = self.aggregatum.get()
        except ValueError:
            return
        assert value is not None
        self.callback(value)

    def __start_timer(self) -> None:
        assert self.timer is None
        self.timer = self.app.run_every(
            self.on_interval,
            self.app.datetime() + self.base_interval,
            self.base_interval.total_seconds(),
        )

    def on_change(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_change"):
            element = make_history_element(self.app.datetime(), new)
            self.aggregatum.add(element)
            self.app.cancel_timer(self.timer)
            self.timer = None
            self.__set_state()
            self.__start_timer()

    def on_interval(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("on_interval"):
            element = make_history_element(
                self.app.datetime(),
                self.app.get_state(self.manager.entity_id),
            )
            self.aggregatum.add(element)
            self.__set_state()


class AggregatedValue(hass.Hass):
    def initialize(self) -> None:
        self.target: str = self.args["target"]
        self.attributes: dict[str, Any] = self.args.get("attributes", {})
        self.aggregator_app = Aggregator(self, self.__set_state)

    def __set_state(self, value: Any) -> None:
        self.set_state(self.target, state=value, attributes=self.attributes)
