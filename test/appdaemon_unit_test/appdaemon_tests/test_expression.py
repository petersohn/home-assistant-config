from __future__ import annotations
from datetime import time, timedelta
import pytest

input1 = "sensor.test_input1"
input2 = "sensor.test_input2"
input3 = "sensor.test_input3"
output = "sensor.test_output"


def _initialize(harness, expression, args=None, **initial_values):
    for entity, value in initial_values.items():
        harness.set_state(entity, value)
    kwargs = {"expr": expression}
    if args:
        kwargs.update(args)
    harness.create_app("expression", "Expression", "expression", target=output, **kwargs)


def _initialize_with_args(harness, expression, **initial_values):
    args_dict = {"list": ["first", "second", "third"], "dict": {"a": "foo", "b": "bar", "c": "baz"}}
    _initialize(harness, expression, args=args_dict, **initial_values)


def _test_states(harness, sensor1, sensor2, type_, expected):
    harness.set_state(input1, sensor1)
    harness.set_state(input2, sensor2)
    assert harness.get_state(output, type=type_) == expected


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    (0, 0, "int", 0),
    (0, 13, "int", 13),
    (63, -8, "int", 55),
    (-7, 5, "int", -2),
])
def test_numeric_sensors(harness, sensor1, sensor2, type_, expected):
    _initialize(harness, f'v.{input1} + v["{input2}"]', **{input1: "0", input2: "0"})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    ("foo", "bar", "str", "foobar"),
    ("", "foo", "str", "foo"),
    ("bar", "", "str", "bar"),
    ("", "", "str", ""),
])
def test_alphanumeric_sensors(harness, sensor1, sensor2, type_, expected):
    _initialize(harness, f"v.{input1} + v.{input2}", **{input1: "", input2: ""})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("sensor1, sensor2, type_, expected", [
    (0, 1, "str", "off"),
    (1, 0, "str", "on"),
    (0, 0, "str", "off"),
    (5, 10, "str", "off"),
    (10, 5, "str", "on"),
])
def test_numeric_binary_sensors(harness, sensor1, sensor2, type_, expected):
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
def test_alphanumeric_binary_sensors(harness, sensor1, sensor2, type_, expected):
    _initialize(harness, f'v.{input1} > v["{input2}"]', **{input1: "", input2: ""})
    _test_states(harness, sensor1, sensor2, type_, expected)


@pytest.mark.parametrize("attr1, attr2, type_, expected", [
    (0, 0, "int", 0),
    (0, 13, "int", 13),
    (63, -8, "int", 55),
    (-7, 5, "int", -2),
    ("foo", "bar", "str", "foobar"),
])
def test_attributes(harness, attr1, attr2, type_, expected):
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
def test_ok(harness, sensor1, sensor2, type_, expected):
    _initialize(harness, f"ok.{input1}", **{input1: "unknown"})
    _test_states(harness, sensor1, sensor2, type_, expected)


def _times_should_match(harness, result, td):
    expected = harness.date_from_time(td, future=False)
    assert result == expected.strftime("%Y-%m-%d %H:%M:%S")


@pytest.mark.parametrize("harness", [{"start_time": time(0, 0, 0)}], indirect=True)
def test_get_now(harness):
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
def test_args(harness, sensor1, sensor2, expected):
    _initialize_with_args(
        harness,
        "args['list'][int(v['sensor.test_input1'])] + args['dict'][v['sensor.test_input2']]",
        **{input1: "0", input2: "a"},
    )
    _test_states(harness, sensor1, sensor2, "str", expected)


def test_changes(harness):
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


def test_nums(harness):
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