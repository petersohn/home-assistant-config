from __future__ import annotations
import sys
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, cast

import pytest

from appdaemon_unit_test.test_helpers.harness import Harness

if TYPE_CHECKING:
    from appdaemon_unit_test.test_helpers import hass as hass_module

    _Hass = hass_module.Hass
else:
    _Hass = object

input1 = "sensor.test_input1"
input2 = "sensor.test_input2"
input3 = "sensor.test_input3"
output = "sensor.test_output"
thread1 = "thread.thread-0"
thread2 = "thread.thread-1"
thread3 = "thread.thread-2"


def _initialize(
    harness: Harness, expression: str, args: object = None,
    **initial_values: object,
) -> None:
    for entity, value in initial_values.items():
        harness.set_state(entity, value)
    kwargs: dict[str, object] = {"expr": expression}
    if isinstance(args, dict):
        kwargs.update(cast(dict[str, object], args))
    harness.create_app("expression", "Expression", "expression", target=output, **kwargs)


def _initialize_with_args(harness: Harness, expression: str, **initial_values: object) -> None:
    args_dict = {"list": ["first", "second", "third"], "dict": {"a": "foo", "b": "bar", "c": "baz"}}
    _initialize(harness, expression, args=args_dict, **initial_values)


def _test_states(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    harness.set_state(input1, sensor1)
    harness.set_state(input2, sensor2)
    assert harness.get_state(output, type=type_) == expected


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    (0, 0, "int", 0),
    (0, 13, "int", 13),
    (63, -8, "int", 55),
    (-7, 5, "int", -2),
])
def test_numeric_sensors(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    _initialize(harness, f'v.{input1} + v["{input2}"]', **{input1: "0", input2: "0"})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    ("foo", "bar", "str", "foobar"),
    ("", "foo", "str", "foo"),
    ("bar", "", "str", "bar"),
    ("", "", "str", ""),
])
def test_alphanumeric_sensors(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    _initialize(harness, f"v.{input1} + v.{input2}", **{input1: "", input2: ""})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    (0, 1, "str", "off"),
    (1, 0, "str", "on"),
    (0, 0, "str", "off"),
    (5, 10, "str", "off"),
    (10, 5, "str", "on"),
])
def test_numeric_binary_sensors(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    _initialize(harness, f"v.{input1} > v.{input2}", **{input1: "0", input2: "0"})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    ("foo", "bar", "str", "on"),
    ("bar", "foo", "str", "off"),
    ("bar", "bar", "str", "off"),
    ("", "foo", "str", "off"),
    ("bar", "", "str", "on"),
    ("", "", "str", "off"),
])
def test_alphanumeric_binary_sensors(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    _initialize(harness, f'v.{input1} > v["{input2}"]', **{input1: "", input2: ""})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("attr1, attr2, type_, expected", [
    (0, 0, "int", 0),
    (0, 13, "int", 13),
    (63, -8, "int", 55),
    (-7, 5, "int", -2),
    ("foo", "bar", "str", "foobar"),
])
def test_attributes(harness: Harness, attr1: str, attr2: str, type_: str, expected: str | int) -> None:
    _initialize(harness, f'a.{input1}.attr1 + a["{input1}"]["attr2"]', **{input1: ""})
    harness.set_state(input1, 0, attr1=attr1, attr2=attr2)
    assert harness.get_state(output, type=type_) == expected


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    ("unknown", 0, "str", "off"),
    (0, 0, "str", "on"),
    ("unavailable", 0, "str", "off"),
    ("foo", 0, "str", "on"),
    (-1, 0, "str", "on"),
])
def test_ok(harness: Harness, sensor1: str | int | float, sensor2: str | int | float, type_: str, expected: str | int | float) -> None:
    _initialize(harness, f"ok.{input1}", **{input1: "unknown"})
    _test_states(harness, sensor1, sensor2, type_, expected)


def _times_should_match(harness: Harness, result: str | None, td: timedelta) -> None:
    expected: datetime = harness.date_from_time(td, future=False)
    assert result == expected.strftime("%Y-%m-%d %H:%M:%S")


@pytest.mark.parametrize("harness", [{"start_time": time(0, 0, 0)}], indirect=True)
def test_get_now(harness: Harness) -> None:
    _initialize(harness, 'now().strftime("%Y-%m-%d %H:%M:%S")')
    harness.advance_time_to(time(0, 1, 0))
    _times_should_match(harness, harness.get_state(output), timedelta(minutes=1))
    harness.advance_time_to(time(0, 1, 30))
    _times_should_match(harness, harness.get_state(output), timedelta(minutes=1, seconds=30))
    harness.advance_time_to(time(1, 12, 20))
    _times_should_match(harness, harness.get_state(output), timedelta(hours=1, minutes=12, seconds=20))


@pytest.mark.parametrize("sensor1, sensor2, expected", [
    (0, "c", "firstbaz"),
    (1, "a", "secondfoo"),
    (2, "b", "thirdbar"),
])
def test_args(harness: Harness, sensor1: str | int, sensor2: str | int, expected: str | int) -> None:
    _initialize_with_args(
        harness,
        "args['list'][int(v['sensor.test_input1'])] + args['dict'][v['sensor.test_input2']]",
        **{input1: "0", input2: "a"},
    )
    _test_states(harness, sensor1, sensor2, "str", expected)


def test_changes(harness: Harness) -> None:
    harness.set_state(input1, "0")
    harness.create_app("history", "ChangeTracker", "changes", entity=input1)
    harness.create_app(
        "expression", "Expression", "expression",
        target=output,
        expr="'{} {}'.format(c.changes.strftime('%H:%M:%S'), u.changes.strftime('%H:%M:%S'))",
    )
    harness.advance_time_to(time(0, 1, 0))
    harness.set_state(input1, 1, foo="bar")
    harness.advance_time(harness.interval)
    assert harness.get_state(output) == "00:01:00 00:01:00"
    harness.advance_time_to(time(0, 1, 30))
    harness.set_state(input1, 1, foo="baz")
    harness.advance_time(harness.interval)
    assert harness.get_state(output) == "00:01:00 00:01:30"


def test_missing_input(harness: Harness) -> None:
    harness.app_manager.create_app(
        "expression", "Expression", "expression",
        target=output,
        expr=f"0.5 * v.{input1}",
    )
    harness.clear_errors()
    assert harness.get_state(output, attribute="all") is None
    harness.set_state(input1, 5)
    assert harness.get_state(output) == "2.5"


def test_nums(harness: Harness) -> None:
    _initialize(
        harness,
        "sum(nums(v.sensor.test_input1, v.sensor.test_input2, v.sensor.test_input3))",
        **{input1: "unknown", input2: "unknown", input3: "unknown"},
    )
    assert harness.get_state(output) == "0"
    harness.set_state(input1, 12)
    harness.set_state(input2, 6.5)
    harness.set_state(input3, -2)
    assert harness.get_state(output) == "16.5"
    harness.set_state(input2, "foo")
    harness.set_state(input1, 0)
    assert harness.get_state(output) == "-2.0"


@pytest.mark.parametrize("syntax", ["d.thread", 'd["thread"]'])
def test_domain(harness: Harness, syntax: str) -> None:
    harness.set_state(thread1, "0")
    _initialize(harness, f"len({syntax})", **{thread1: "0"})
    assert harness.get_state(output, type="int") == 1
    harness.set_state(thread2, "4")
    assert harness.get_state(output, type="int") == 2
    harness.set_state(thread3, "5")
    assert harness.get_state(output, type="int") == 3


def test_domain_filters(harness: Harness) -> None:
    harness.set_state(thread1, "idle")
    harness.set_state(thread2, "callback")
    _initialize(harness, 'sum(1 for x in d.thread if x != "idle")')
    assert harness.get_state(output, type="int") == 1
    harness.set_state(thread1, "callback")
    assert harness.get_state(output, type="int") == 2
    harness.set_state(thread1, "idle")
    assert harness.get_state(output, type="int") == 1


def test_domain_empty(harness: Harness) -> None:
    _initialize(harness, "len(d.thread)")
    assert harness.get_state(output, type="int") == 0


def test_domain_new_entity_triggers(harness: Harness) -> None:
    _initialize(harness, "len(d.thread)")
    assert harness.get_state(output, type="int") == 0
    harness.set_state(thread1, "x")
    assert harness.get_state(output, type="int") == 1


def test_domain_nonexistent(harness: Harness) -> None:
    _initialize(harness, "len(d.ghost)")
    assert harness.get_state(output, type="int") == 0


def _initialize_dict(
    harness: Harness, expression: dict[str, object], **initial_values: object,
) -> None:
    for entity, value in initial_values.items():
        harness.set_state(entity, value)
    harness.create_app(
        "expression", "Expression", "expression",
        target=output, expr=expression,
    )


def _initialize_list(
    harness: Harness, expression: list[object], **initial_values: object,
) -> None:
    for entity, value in initial_values.items():
        harness.set_state(entity, value)
    harness.create_app(
        "expression", "Expression", "expression",
        target=output, expr=expression,
    )


@pytest.mark.parametrize("sensor1, sensor2, expected", [
    (10, 5, 10.0),
    (5, 10, -1.0),
    (5, 5, -1.0),
])
def test_if_then_else(
    harness: Harness, sensor1: str | int | float,
    sensor2: str | int | float, expected: str | int | float,
) -> None:
    expr: dict[str, object] = {
        "if": f"v.{input1} > v.{input2}",
        "then": f"v.{input1}",
        "else": "-1",
    }
    _initialize_dict(
        harness, expr, **{input1: "0", input2: "0"},
    )
    _test_states(harness, sensor1, sensor2, "float", expected)


def test_nested_if(harness: Harness) -> None:
    expr: dict[str, object] = {
        "if": f"v.{input1} > 0",
        "then": {
            "if": f"v.{input2} > 5",
            "then": 1,
            "else": 0,
        },
        "else": {
            "if": False,
            "then": "impossible",
            "else": -1,
        },
    }
    _initialize_dict(harness, expr, **{input1: 1, input2: 8})
    assert harness.get_state(output, type="int") == 1
    harness.set_state(input2, 3)
    assert harness.get_state(output, type="int") == 0
    harness.set_state(input1, 0)
    assert harness.get_state(output) == "-1"


@pytest.mark.parametrize("value, expected", [
    (1, "one"),
    (2, "two"),
    (7, "other"),
])
def test_switch_cases(harness: Harness, value: int, expected: str) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 1, "then": "'one'"},
            {"if": 2, "then": "'two'"},
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: value})
    assert harness.get_state(output) == expected


def test_switch_bool_equality(harness: Harness) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 1, "then": "'one'"},
            {"if": 0, "then": "'zero'"},
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: "off"})
    assert harness.get_state(output) == "zero"
    harness.set_state(input1, "on")
    assert harness.get_state(output) == "one"


def test_switch_nested_case_dict(harness: Harness) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 0, "then": "'zero'"},
            {
                "if": 1,
                "then": {
                    "if": f"v.{input2} > 5",
                    "then": "'high'",
                    "else": "'low'",
                },
            },
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: 1, input2: 8})
    assert harness.get_state(output) == "high"
    harness.set_state(input2, 3)
    assert harness.get_state(output) == "low"


@pytest.mark.parametrize("expr, expected", [(5, 5), (2.5, 2.5)])
def test_numeric_expr(
    harness: Harness, expr: float | int, expected: float | int
) -> None:
    harness.create_app(
        "expression", "Expression", "expression", target=output, expr=expr
    )
    assert harness.get_state(output, type="float") == expected
    harness.set_state(input1, 999)
    assert harness.get_state(output, type="float") == expected


def test_if_entity_tracking(harness: Harness) -> None:
    expr: dict[str, object] = {
        "if": f"v.{input1}",
        "then": "'yes'",
        "else": "'no'",
    }
    _initialize_dict(harness, expr, **{input1: "off"})
    assert harness.get_state(output) == "no"
    harness.set_state(input1, "on")
    assert harness.get_state(output) == "yes"
    harness.set_state(input1, "off")
    assert harness.get_state(output) == "no"


def test_switch_entity_tracking(harness: Harness) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 1, "then": "'one'"},
            {"if": 2, "then": "'two'"},
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: 1})
    assert harness.get_state(output) == "one"
    harness.set_state(input1, 2)
    assert harness.get_state(output) == "two"
    harness.set_state(input1, 3)
    assert harness.get_state(output) == "other"


@pytest.mark.parametrize("bad_expr", [
    {"if": "v.sensor", "then": "1"},
    {"if": "v.sensor", "then": "1", "else": "2", "foo": "3"},
    {"switch": "v.sensor", "case": [], "else": "2"},
    {"switch": "v.sensor", "case": [{"if": "1"}], "else": "2"},
    {
        "switch": "v.sensor",
        "case": [{"if": "1", "then": "2", "when": "3"}],
        "else": "4",
    },
    {"if": ["1"], "then": "2", "else": "3"},
    ["a"],
    True,
])
def test_validation_errors(harness: Harness, bad_expr: object) -> None:
    with pytest.raises(ValueError):
        harness.create_app(
            "expression", "Expression", "expression",
            target=output, expr=bad_expr,
        )


def test_switch_int_float_equality(harness: Harness) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 1.0, "then": "'one'"},
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: 1})
    assert harness.get_state(output) == "one"


def test_switch_evaluated_once(harness: Harness) -> None:
    expr: dict[str, object] = {
        "switch": f"v.{input1}",
        "case": [
            {"if": 1, "then": "'one'"},
            {"if": 2, "then": "'two'"},
            {"if": 3, "then": "'three'"},
        ],
        "else": "'other'",
    }
    _initialize_dict(harness, expr, **{input1: 3})
    assert harness.get_state(output) == "three"

    get_state_calls: list[str] = []
    hass_module = sys.modules.get("hass") or __import__("hass")
    original_get_state = hass_module.Hass.get_state

    def counting_get_state(
        self: _Hass,
        entity_id: str | None,
        attribute: str | None = None,
        namespace: str = "default",
    ) -> object:
        if entity_id is not None and entity_id == input1:
            get_state_calls.append(entity_id)
        return original_get_state(
            self, entity_id, attribute, namespace
        )

    hass_module.Hass.get_state = counting_get_state  # type: ignore[method-assign, assignment]
    try:
        harness.set_state(input1, 2)
        assert harness.get_state(output) == "two"
    finally:
        hass_module.Hass.get_state = original_get_state  # type: ignore[method-assign, assignment]
    # One re-evaluation triggered by the state change: the switch value
    # must be fetched exactly once, not once per case.
    assert get_state_calls == [input1]


def test_validation_error_path(harness: Harness) -> None:
    bad_expr: dict[str, object] = {
        "switch": "v.sensor",
        "case": [{"if": "1", "then": "2"}, {"if": "1"}],
        "else": "3",
    }
    with pytest.raises(
        ValueError, match=r"expr\.case\[1\]\.then: missing key then"
    ):
        harness.create_app(
            "expression", "Expression", "expression",
            target=output, expr=bad_expr,
        )


@pytest.mark.parametrize("sensor1, sensor2, expected", [
    (10, 5, "first"),
    (5, 10, "second"),
    (5, 5, "other"),
])
def test_if_chain(
    harness: Harness, sensor1: str | int | float,
    sensor2: str | int | float, expected: str,
) -> None:
    expr: list[object] = [
        {"if": f"v.{input1} > v.{input2}", "then": "'first'"},
        {"if": f"v.{input2} > v.{input1}", "then": "'second'"},
        {"else": "'other'"},
    ]
    _initialize_list(harness, expr, **{input1: "0", input2: "0"})
    _test_states(harness, sensor1, sensor2, "str", expected)


def test_if_chain_three_conditions(harness: Harness) -> None:
    expr: list[object] = [
        {"if": f"v.{input1} == 1", "then": "'one'"},
        {"if": f"v.{input1} == 2", "then": "'two'"},
        {"if": f"v.{input1} == 3", "then": "'three'"},
        {"else": "'other'"},
    ]
    _initialize_list(harness, expr, **{input1: 1})
    assert harness.get_state(output) == "one"
    harness.set_state(input1, 2)
    assert harness.get_state(output) == "two"
    harness.set_state(input1, 5)
    assert harness.get_state(output) == "other"


def test_if_chain_else_value_dict(harness: Harness) -> None:
    expr: list[object] = [
        {"if": f"v.{input1} > 0", "then": "'pos'"},
        {
            "else": {
                "if": f"v.{input2} > 5",
                "then": 1,
                "else": 0,
            },
        },
    ]
    _initialize_list(harness, expr, **{input1: 1, input2: 8})
    assert harness.get_state(output) == "pos"
    harness.set_state(input1, 0)
    assert harness.get_state(output, type="int") == 1
    harness.set_state(input2, 3)
    assert harness.get_state(output, type="int") == 0


def test_if_chain_entity_tracking(harness: Harness) -> None:
    expr: list[object] = [
        {"if": f"v.{input1} == 1", "then": "'first'"},
        {"if": f"v.{input2} == 2", "then": "'second'"},
        {"else": "'other'"},
    ]
    _initialize_list(harness, expr, **{input1: 0, input2: 0})
    assert harness.get_state(output) == "other"
    harness.set_state(input2, 2)
    assert harness.get_state(output) == "second"
    harness.set_state(input2, 0)
    assert harness.get_state(output) == "other"
    harness.set_state(input1, 1)
    assert harness.get_state(output) == "first"


@pytest.mark.parametrize("bad_expr", [
    [{"else": "'other'"}],
    [{"if": "v.sensor", "then": "'first'"}],
    [{"if": "v.sensor", "then": "'first'"}, {"if": "x", "then": "'last'"}],
    [{"if": "v.sensor", "then": "'first'"}, {"else": "'a'"}, {"else": "'b'"}],
    [{"if": "v.sensor", "then": "1", "foo": "2"}, {"else": "'other'"}],
    [],
    [{"if": "1", "then": "1"}, ["2"]],
])
def test_if_chain_validation_errors(harness: Harness, bad_expr: object) -> None:
    with pytest.raises(ValueError):
        harness.create_app(
            "expression", "Expression", "expression",
            target=output, expr=bad_expr,
        )


def test_if_chain_validation_error_path(harness: Harness) -> None:
    bad_expr: list[object] = [
        {"if": "1", "then": "2", "foo": "3"},
        {"else": "'other'"},
    ]
    with pytest.raises(
        ValueError, match=r"expr\[0\]: unknown keys: \[\"'foo'\"\]"
    ):
        harness.create_app(
            "expression", "Expression", "expression",
            target=output, expr=bad_expr,
        )


def test_list_sub_expression_rejected(harness: Harness) -> None:
    bad_expr: dict[str, object] = {
        "if": ["1"],
        "then": "1",
        "else": "2",
    }
    with pytest.raises(
        ValueError,
        match=r"expr\.if: expected str, int, float, bool or dict, got list",
    ):
        harness.create_app(
            "expression", "Expression", "expression",
            target=output, expr=bad_expr,
        )
