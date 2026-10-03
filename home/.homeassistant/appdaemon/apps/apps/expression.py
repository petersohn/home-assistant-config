from __future__ import annotations
import datetime
import hass
import traceback
from callback_provider import (
    CallbackProvider,
    ChangeTrackerProvider,
    EnablerProvider,
)
from hass_common import AttributeValue, EntityValue
from typing import Any, Callable, cast, final
from collections.abc import Iterator


ExpressionResult = str | float | int | bool | None
ExpressionValue = str | float | int | dict[str, object]
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


def filter_nums(*args: object) -> Iterator[float]:
    return (x for x in args if type(x) is float)


class _StringExprNode:
    """String sub-expression, evaluated with the eval machinery."""

    def __init__(self, expr: str) -> None:
        self.expr: str = expr

    def evaluate(self, evaluator: ExpressionEvaluator) -> ExpressionResult:
        return eval(self.expr, evaluator.evaluators)


class _LiteralNode:
    def __init__(self, value: float | int | bool) -> None:
        self.value: float | int | bool = value

    def evaluate(self, evaluator: ExpressionEvaluator) -> ExpressionResult:
        return self.value


class _IfNode:
    def __init__(
        self, cond: _ExprNode, then: _ExprNode, else_: _ExprNode
    ) -> None:
        self.cond: _ExprNode = cond
        self.then: _ExprNode = then
        self.else_: _ExprNode = else_

    def evaluate(self, evaluator: ExpressionEvaluator) -> ExpressionResult:
        cond = self.cond.evaluate(evaluator)
        branch = self.then if cond else self.else_
        return branch.evaluate(evaluator)


class _SwitchNode:
    def __init__(
        self,
        switch: _ExprNode,
        cases: list[tuple[_ExprNode, _ExprNode]],
        else_: _ExprNode,
    ) -> None:
        self.switch: _ExprNode = switch
        self.cases: list[tuple[_ExprNode, _ExprNode]] = cases
        self.else_: _ExprNode = else_

    def evaluate(self, evaluator: ExpressionEvaluator) -> ExpressionResult:
        switch_value = self.switch.evaluate(evaluator)
        for case_expr, then in self.cases:
            if switch_value == case_expr.evaluate(evaluator):
                return then.evaluate(evaluator)
        return self.else_.evaluate(evaluator)


_ExprNode = _StringExprNode | _LiteralNode | _IfNode | _SwitchNode


def _compile_expr(source: object, path: str) -> _ExprNode:
    """Compile a sub-expression to a node.

    path is the location of the sub-expression in the expression dict
    (e.g. "expr.case[1].then"), used in ValueError messages.
    """
    if isinstance(source, str):
        return _StringExprNode(source)
    if isinstance(source, (bool, int, float)):
        # bool must be handled before int: it is a subclass of int, but
        # it is valid as a sub-expression (unlike at the top level).
        return _LiteralNode(source)
    if isinstance(source, dict):
        # cast: parameterized generic dict type cannot be isinstance-checked
        return _compile_dict(cast("dict[str, object]", source), path)
    raise ValueError(
        f"{path}: expected str, int, float, bool or dict, "
        + f"got {type(source).__name__}"
    )


def _compile_dict(source: dict[str, object], path: str) -> _ExprNode:
    keys: set[str] = set(source.keys())
    if keys == {"if", "then", "else"}:
        return _IfNode(
            _compile_expr(source["if"], f"{path}.if"),
            _compile_expr(source["then"], f"{path}.then"),
            _compile_expr(source["else"], f"{path}.else"),
        )
    if keys == {"switch", "case", "else"}:
        return _compile_switch(source, path)
    unknown = keys - {"if", "then", "else", "switch", "case"}
    if unknown:
        raise ValueError(
            f"{path}: unknown keys: {sorted(map(repr, unknown))}"
        )
    expected: set[str]
    if "switch" in keys:
        expected = {"switch", "case", "else"}
    elif "if" in keys or "then" in keys:
        expected = {"if", "then", "else"}
    else:
        raise ValueError(
            f"{path}: keys must be exactly {{if, then, else}} "
            + "or {{switch, case, else}}"
        )
    raise ValueError(f"{path}: missing keys: {sorted(expected - keys)}")


def _compile_switch(source: dict[str, object], path: str) -> _ExprNode:
    case_source: object = source["case"]
    if not isinstance(case_source, list):
        raise ValueError(
            f"{path}.case: expected list, "
            + f"got {type(case_source).__name__}"
        )
    if not case_source:
        raise ValueError(f"{path}.case: empty case list")
    case_items = cast("list[object]", case_source)  # same as above
    cases: list[tuple[_ExprNode, _ExprNode]] = []
    for index, item in enumerate(case_items):
        item_path = f"{path}.case[{index}]"
        if not isinstance(item, dict):
            raise ValueError(
                f"{item_path}: expected dict, "
                + f"got {type(item).__name__}"
            )
        item_dict = cast("dict[str, object]", item)  # same as above
        item_keys: set[str] = set(item_dict.keys())
        unknown = item_keys - {"if", "then"}
        if unknown:
            raise ValueError(
                f"{item_path}: unknown keys: {sorted(map(repr, unknown))}"
            )
        for key in ("if", "then"):
            if key not in item_keys:
                raise ValueError(f"{item_path}.{key}: missing key {key}")
        cases.append(
            (
                _compile_expr(item_dict["if"], f"{item_path}.if"),
                _compile_expr(item_dict["then"], f"{item_path}.then"),
            )
        )
    return _SwitchNode(
        _compile_expr(source["switch"], f"{path}.switch"),
        cases,
        _compile_expr(source["else"], f"{path}.else"),
    )


@final
class ExpressionEvaluator:
    def __init__(
        self,
        app: hass.Hass,
        expr: ExpressionValue,
        callback: Callback | None = None,
        extra_values: dict[str, Any] | None = None,
    ) -> None:
        import locker
        locker_app = app.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("ExpressionEvaluator")

        self.app = app
        self.expr: str = ""
        self.root: _ExprNode | None = None
        if isinstance(expr, str):
            self.expr = expr
        elif isinstance(expr, dict):
            self.root = _compile_expr(expr, "expr")
        elif isinstance(expr, bool):
            raise ValueError(
                "expr: bare bool is not a valid expression, "
                + "expected str, int, float or dict"
            )
        elif type(expr) in (int, float):
            self.expr = str(expr)
        else:
            raise ValueError(
                f"expr: expected str, int, float or dict, "
                + f"got {type(expr).__name__}"
            )
        self.callback: Callback | None = callback
        self.entities: set[str] = set()
        self.attributes: set[tuple[str, str]] = set()
        self.domains: set[str] = set()
        self.app_callbacks: dict[str, int] = {}
        self.evaluators: dict[str, Any] = self._create_evaluators()
        if extra_values:
            self.evaluators.update(extra_values)
        self.timer: str | None = None
        self.get()

    def cleanup(self) -> None:
        for name, id in self.app_callbacks.items():
            try:
                app = self.app.get_app(name)
                assert isinstance(app, CallbackProvider), (
                    f"App {name!r} does not support remove_callback"
                )
                app.remove_callback(id)
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
            "d": Evaluator(self._get_domain),
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
            f"Expected scalar from get_state({entity!r}, "
            f"attribute={attribute!r}), got {type(value).__name__}"
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
            f"Expected scalar from get_state({entity!r}), "
            f"got {type(value).__name__}"
        )
        try:
            return float(value)
        except ValueError:
            assert isinstance(value, str), (
                f"Expected str from get_state({entity!r}), "
                f"got {type(value).__name__}"
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

    def _get_domain(self, domain: str) -> list[str | float | bool]:
        """All state values of entities in a domain, e.g. ``d.thread``.

        Usable with attribute access (``d.thread``) or indexing
        (``d["thread"]``), like ``v``. Listens on the whole domain, so
        entities added to or removed from the domain also trigger
        re-evaluation.
        """
        if self.callback is not None and domain not in self.domains:
            self.app.listen_state(self._on_entity_change, entity_id=domain)
            self.domains.add(domain)
        states: (
            dict[str, dict[str, object] | str | float | bool] | None
        ) = self.app.get_state(domain)
        if states is None:
            return []
        return [
            self._extract_state_value(state) for state in states.values()
        ]

    def _extract_state_value(
        self, state: dict[str, object] | str | float | bool
    ) -> str | float | bool:
        """Extract the scalar state value from a get_state domain result.

        Domain queries return full state dicts, of which only the
        ``state`` key is interesting here.
        """
        value: object = (
            state.get("state") if isinstance(state, dict) else state
        )
        if value is None:
            return ""
        if isinstance(value, bool):
            return value
        assert isinstance(value, (str, int, float)), (
            f"Expected scalar from domain query, got {type(value).__name__}"
        )
        try:
            return float(value)
        except ValueError:
            return str(value)

    def _get_app(self, name: str) -> hass.Hass:
        try:
            app = self.app.get_app(name)
            assert isinstance(app, hass.Hass), (
                f"Expected {name!r} to be a Hass app, "
                f"got {type(app).__name__}"
            )
            if self.callback is not None and name not in self.app_callbacks:
                assert isinstance(app, CallbackProvider), (
                    f"App {name!r} does not support add_callback"
                )
                id = app.add_callback(lambda: self._on_app_change())
                self.app_callbacks[name] = id
            return app
        except Exception:
            self.app.error(f"Can't get app {name}")
            raise

    def _get_enabled(self, name: str) -> bool:
        app = self._get_app(name)
        assert isinstance(app, EnablerProvider), (
            f"Expected {name!r} to be an Enabler app, "
            f"got {type(app).__name__}"
        )
        return app.is_enabled()

    def _get_last_changed(self, name: str) -> Any:
        app = self._get_app(name)
        assert isinstance(app, ChangeTrackerProvider), (
            f"Expected {name!r} to be a ChangeTracker app, "
            f"got {type(app).__name__}"
        )
        return app.last_changed()

    def _get_last_updated(self, name: str) -> Any:
        app = self._get_app(name)
        assert isinstance(app, ChangeTrackerProvider), (
            f"Expected {name!r} to be a ChangeTracker app, "
            f"got {type(app).__name__}"
        )
        return app.last_updated()

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
        self.app.log(f"state change({entity}): {old} -> {new}")
        if new != old:
            self.fire_callback({})

    def _get(self) -> ExpressionResult:
        try:
            if self.root is None:
                result = eval(self.expr, self.evaluators)
            else:
                result = self.root.evaluate(self)
            assert result is None or isinstance(result, (str, float, int, bool)), (
                f"Expression returned unexpected type "
                f"{type(result).__name__}: {result!r}"
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
    target: str = ""
    attributes: dict[str, AttributeValue] = {}
    evaluator: ExpressionEvaluator = cast("ExpressionEvaluator", cast(Any, None))

    def initialize(self) -> None:
        self.target = self.args["target"]
        self.attributes = self.args.get("attributes", {})
        self.attributes.setdefault("state_class", "measurement")
        self.evaluator = ExpressionEvaluator(
            self, self.args["expr"], self._set
        )
        self._set(self.evaluator.get())

    def terminate(self) -> None:
        self.evaluator.cleanup()

    def _set(self, value: ExpressionResult) -> None:
        if value is None:
            return
        if type(value) is bool:
            value = "on" if value else "off"
        self.set_state(self.target, state=value, attributes=self.attributes)
