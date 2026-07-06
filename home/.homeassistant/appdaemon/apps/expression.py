from __future__ import annotations
import datetime
import hass
import traceback
from hass import EntityValue
from typing import Any, Callable


ExpressionResult = str | float | int | bool | None
Callback = Callable[[ExpressionResult], None]


class Evaluator:
    def __init__(
        self, func: Callable[[str], Any], prefix: str = ""
    ) -> None:
        self.__prefix = prefix
        self.__func = func

    def __getattr__(self, value: str) -> Any:
        return self.__func(self.__prefix + value)

    def __getitem__(self, value: str) -> Any:
        return self.__func(self.__prefix + str(value))


def filter_nums(*args: Any) -> Any:
    return filter(lambda x: type(x) == float, args)


class ExpressionEvaluator:
    def __init__(
        self,
        app: hass.Hass,
        expr: str,
        callback: Callback | None = None,
        extra_values: dict[str, Any] | None = None,
    ) -> None:
        import locker
        locker_app = app.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("ExpressionEvaluator")

        self.app = app
        self.expr = expr
        self.callback: Callback | None = callback
        self.entities: set[str] = set()
        self.attributes: set[tuple[str, str]] = set()
        self.app_callbacks: dict[str, int] = {}
        self.evaluators: dict[str, Any] = self._create_evaluators()
        if extra_values:
            self.evaluators.update(extra_values)
        self.timer: str | None = None
        self.get()

    def cleanup(self) -> None:
        for name, id in self.app_callbacks.items():
            try:
                self.app.get_app(name).remove_callback(id)  # type: ignore[attr-defined]
            except Exception:
                self.app.error(traceback.format_exc())

    def _create_evaluators(self) -> dict[str, Any]:
        return {
            "a": Evaluator(self._get_attribute_base),
            "e": Evaluator(self._get_enabled),
            "c": Evaluator(self._get_last_changed),
            "u": Evaluator(self._get_last_updated),
            "v": Evaluator(self._get_value),
            "ok": Evaluator(self._get_ok),
            "now": self._get_now,
            "strptime": datetime.datetime.strptime,
            "dt": datetime.timedelta,
            "t": datetime.datetime,
            "nums": filter_nums,
            "args": self.app.args,
        }

    def _get_now(self) -> datetime.datetime:
        now = self.app.datetime()
        if self.callback is not None and self.timer is None:
            self.timer = self.app.run_every(
                self.fire_callback, now + datetime.timedelta(seconds=1), 1
            )
        return now

    def _get_attribute_base(self, entity: str) -> Evaluator:
        if "." not in entity:
            return Evaluator(self._get_attribute_base, entity + ".")
        return Evaluator(self._get_attribute_callback(entity))

    def _get_attribute_callback(self, entity: str) -> Callable[[str], Any]:
        return lambda attribute: self._get_attribute(entity, attribute)

    def _get_attribute(self, entity: str, attribute: str) -> Any:
        key = (entity, attribute)
        if self.callback is not None and key not in self.attributes:
            self.app.listen_state(
                self._on_entity_change, entity_id=entity, attribute=attribute
            )
            self.attributes.add(key)

        value = self.app.get_state(entity, attribute=attribute)
        if value is None:
            return ""
        assert isinstance(value, (str, int, float, bool)), (
            "Expected scalar from get_state({!r}, attribute={!r}), got {}".format(
                entity, attribute, type(value).__name__
            )
        )
        try:
            return float(value)
        except ValueError:
            return value

    def _get_value(self, entity: str) -> str | float | bool | Evaluator:
        if "." not in entity:
            return Evaluator(self._get_value, entity + ".")

        if self.callback is not None and entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity_id=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        if value is None or value == "unknown" or value == "unavailable":
            return ""
        if value == "on":
            return True
        if value == "off":
            return False
        assert isinstance(value, (str, int, float, bool)), (
            "Expected scalar from get_state({!r}), got {}".format(
                entity, type(value).__name__
            )
        )
        try:
            return float(value)
        except ValueError:
            assert isinstance(value, str), (
                "Expected str from get_state({!r}), got {}".format(
                    entity, type(value).__name__
                )
            )
            return value

    def _get_ok(self, entity: str) -> Any:
        if "." not in entity:
            return Evaluator(self._get_ok, entity + ".")

        if self.callback is not None and entity not in self.entities:
            self.app.listen_state(self._on_entity_change, entity_id=entity)
            self.entities.add(entity)
        value = self.app.get_state(entity)
        return (
            value is not None
            and value != ""
            and value != "unknown"
            and value != "unavailable"
        )

    def _get_app(self, name: str) -> Any:
        try:
            app = self.app.get_app(name)
            if self.callback is not None and name not in self.app_callbacks:
                id = app.add_callback(lambda: self._on_app_change())  # type: ignore[attr-defined]
                self.app_callbacks[name] = id
            return app
        except Exception:
            self.app.error(f"Can't get app {name}")
            raise

    def _get_enabled(self, name: str) -> bool:
        return self._get_app(name).is_enabled()

    def _get_last_changed(self, name: str) -> Any:
        return self._get_app(name).last_changed()

    def _get_last_updated(self, name: str) -> Any:
        return self._get_app(name).last_updated()

    def _on_app_change(self) -> None:
        self.app.log("on_app_change")
        self.app.run_in(self.fire_callback, 0)

    def _on_entity_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        self.app.log("state change({}): {} -> {}".format(entity, old, new))
        if new != old:
            self.fire_callback({})

    def _get(self) -> ExpressionResult:
        try:
            result = eval(self.expr, self.evaluators)
            assert result is None or isinstance(result, (str, float, int, bool)), (
                "Expression returned unexpected type {}: {!r}".format(
                    type(result).__name__, result
                )
            )
        except Exception:
            self.app.error(traceback.format_exc())
            self.app.run_in(lambda _: self.get(), 60)
            return None
        return result

    def get(self) -> ExpressionResult:
        with self.mutex.lock("get"):
            return self._get()

    def fire_callback(self, kwargs: dict[str, Any]) -> None:
        if self.callback is None:
            return
        with self.mutex.lock("fire_callback"):
            value = self._get()
            self.callback(value)


class Expression(hass.Hass):
    def initialize(self) -> None:
        self.target: str = self.args["target"]
        self.attributes: dict[str, Any] = self.args.get("attributes", {})
        self.evaluator = ExpressionEvaluator(
            self, self.args["expr"], self._set
        )
        self._set(self.evaluator.get())

    def terminate(self) -> None:
        self.evaluator.cleanup()

    def _set(self, value: ExpressionResult) -> None:
        if type(value) is bool:
            value = "on" if value else "off"
        self.set_state(self.target, state=value, attributes=self.attributes)
