from __future__ import annotations
from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from conftest import Harness
from unit_helpers.timing import Timing

test_input = "sensor.test_input"
test_switch = "input_boolean.test_switch"
values = ["foo", "bar"]


def _create_enabled_switch(harness: Harness, name: str, enabler_name: str, target: str) -> Any:
    switch_name = f"{name}_switch"
    harness.create_app("auto_switch", "AutoSwitch", switch_name, target=target)
    targets = [switch_name]
    return harness.create_app(
        "enabled_switch", "EnabledSwitch", name,
        enabler=enabler_name, targets=targets,
    )


@pytest.mark.parametrize("initial_state_arg, expected_initial_state", [
    (None, True),
    (True, True),
    (False, False),
])
def test_script_enabler(harness: Harness, initial_state_arg: Any, expected_initial_state: bool) -> None:
    args = {}
    if initial_state_arg is not None:
        args["initial"] = initial_state_arg
    enabler: Any = harness.create_app("enabler", "ScriptEnabler", "enabler", **args)
    assert enabler.is_enabled() == expected_initial_state
    enabler.disable()
    assert enabler.is_enabled() == False
    enabler.enable()
    assert enabler.is_enabled() == True


@pytest.mark.parametrize("class_name, entity_value, expected_state, args", [
    ("ValueEnabler", "off", False, {"value": "on"}),
    ("ValueEnabler", "on", True, {"value": "on"}),
    ("ValueEnabler", "off", True, {"value": "off"}),
    ("ValueEnabler", "on", False, {"value": "off"}),
    ("ValueEnabler", "foo", True, {"values": values}),
    ("ValueEnabler", "bar", True, {"values": values}),
    ("ValueEnabler", "foobar", False, {"values": values}),
    ("ValueEnabler", 0, False, {"values": values}),
    ("ValueEnabler", 100, False, {"values": values}),
    ("RangeEnabler", -100, False, {"min": 10, "max": 20}),
    ("RangeEnabler", 0, False, {"min": 10, "max": 20}),
    ("RangeEnabler", 9, False, {"min": 10, "max": 20}),
    ("RangeEnabler", 10, True, {"min": 10, "max": 20}),
    ("RangeEnabler", 15, True, {"min": 10, "max": 20}),
    ("RangeEnabler", 20, True, {"min": 10, "max": 20}),
    ("RangeEnabler", 21, False, {"min": 10, "max": 20}),
    ("RangeEnabler", 100, False, {"min": 10, "max": 20}),
    ("RangeEnabler", -100, False, {"min": 15}),
    ("RangeEnabler", 0, False, {"min": 15}),
    ("RangeEnabler", 14, False, {"min": 15}),
    ("RangeEnabler", 15, True, {"min": 15}),
    ("RangeEnabler", 16, True, {"min": 15}),
    ("RangeEnabler", 100, True, {"min": 15}),
    ("RangeEnabler", -100, True, {"max": 15}),
    ("RangeEnabler", 0, True, {"max": 15}),
    ("RangeEnabler", 14, True, {"max": 15}),
    ("RangeEnabler", 15, True, {"max": 15}),
    ("RangeEnabler", 16, False, {"max": 15}),
    ("RangeEnabler", 100, False, {"max": 15}),
])
def test_value_enabler(harness: Harness, class_name: str, entity_value: Any, expected_state: bool, args: dict[str, Any]) -> None:
    harness.set_state(test_input, entity_value)
    enabler: Any = harness.create_app(
        "enabler", class_name, "enabler", entity=test_input, **args
    )
    assert enabler.is_enabled() == expected_state


@pytest.mark.parametrize("harness, expected_state, begin, end", [
    ({"start_date": date(2018, 1, 1), "start_time": time(10, 0, 0)}, False, "03-11", "03-11"),
    ({"start_date": date(2018, 3, 10), "start_time": time(10, 0, 0)}, False, "03-11", "03-11"),
    ({"start_date": date(2018, 3, 11), "start_time": time(10, 0, 0)}, True, "03-11", "03-11"),
    ({"start_date": date(2018, 3, 12), "start_time": time(10, 0, 0)}, False, "03-11", "03-11"),
    ({"start_date": date(2018, 12, 31), "start_time": time(10, 0, 0)}, False, "03-11", "03-11"),
    ({"start_date": date(2025, 3, 11), "start_time": time(10, 0, 0)}, True, "03-11", "03-11"),
    ({"start_date": date(2025, 3, 12), "start_time": time(10, 0, 0)}, False, "03-11", "03-11"),
    ({"start_date": date(2018, 1, 1), "start_time": time(10, 0, 0)}, False, "05-01", "10-06"),
    ({"start_date": date(2018, 4, 30), "start_time": time(10, 0, 0)}, False, "05-01", "10-06"),
    ({"start_date": date(2018, 5, 1), "start_time": time(10, 0, 0)}, True, "05-01", "10-06"),
    ({"start_date": date(2018, 5, 2), "start_time": time(10, 0, 0)}, True, "05-01", "10-06"),
    ({"start_date": date(2018, 10, 5), "start_time": time(10, 0, 0)}, True, "05-01", "10-06"),
    ({"start_date": date(2018, 10, 6), "start_time": time(10, 0, 0)}, True, "05-01", "10-06"),
    ({"start_date": date(2018, 10, 7), "start_time": time(10, 0, 0)}, False, "05-01", "10-06"),
    ({"start_date": date(2018, 12, 31), "start_time": time(10, 0, 0)}, False, "05-01", "10-06"),
    ({"start_date": date(2018, 1, 1), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 4, 29), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 4, 30), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 5, 1), "start_time": time(10, 0, 0)}, False, "06-20", "04-30"),
    ({"start_date": date(2018, 6, 19), "start_time": time(10, 0, 0)}, False, "06-20", "04-30"),
    ({"start_date": date(2018, 6, 20), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 6, 21), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 12, 31), "start_time": time(10, 0, 0)}, True, "06-20", "04-30"),
    ({"start_date": date(2018, 9, 1), "start_time": time(10, 0, 0)}, False, "09-02", "09-02"),
    ({"start_date": date(2018, 9, 2), "start_time": time(10, 0, 0)}, True, "09-02", "09-02"),
    ({"start_date": date(2018, 9, 3), "start_time": time(10, 0, 0)}, False, "09-02", "09-02"),
], indirect=["harness"])
def test_date_enabler(harness: Harness, expected_state: bool, begin: str, end: str) -> None:
    enabler: Any = harness.create_app("enabler", "DateEnabler", "enabler", begin=begin, end=end)
    assert enabler.is_enabled() == expected_state


@pytest.mark.parametrize("expected_state, vs", [
    (False, [False, False, False, False]),
    (False, [False, False, False, True]),
    (False, [False, False, True, False]),
    (False, [False, False, True, True]),
    (False, [False, True, False, False]),
    (False, [False, True, False, True]),
    (False, [False, True, True, False]),
    (True, [True, True, True, True]),
])
def test_multi_enabler(harness: Harness, expected_state: bool, vs: list[bool]) -> None:
    names = []
    for i, value in enumerate(vs):
        name = f"enabler{i}"
        harness.create_app("enabler", "ScriptEnabler", name, initial=value)
        names.append(name)
    enabler: Any = harness.create_app("enabler", "MultiEnabler", "enabler", enablers=names)
    assert enabler.is_enabled() == expected_state


@pytest.mark.parametrize("harness", [{"start_time": time(0, 0, 0)}], indirect=True)
def test_delayed_enabler(harness: Harness, timing: Timing) -> None:
    delay = {"minutes": 1}
    enabler: Any = harness.create_app(
        "enabler", "ScriptEnabler", "test_enabler", initial=False, delay=delay
    )
    _create_enabled_switch(harness, "switch", "test_enabler", test_switch)

    harness.schedule_call_at(timedelta(seconds=40), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=3), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=5, seconds=30), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=6), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=8), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=10), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=10, seconds=30), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=12), "call_on_app", enabler, "disable")

    timing.state_should_change_at(test_switch, "on", timedelta(minutes=1, seconds=40))
    timing.state_should_change_at(test_switch, "off", timedelta(minutes=4))
    timing.state_should_change_at(test_switch, "on", timedelta(minutes=9))
    timing.state_should_change_at(test_switch, "off", timedelta(minutes=13))


def test_value_enabler_changes(harness: Harness) -> None:
    harness.set_state(test_input, "")
    enabler: Any = harness.create_app(
        "enabler", "ValueEnabler", "enabler", entity=test_input, value="foo"
    )
    _create_enabled_switch(harness, "switch", "enabler", test_switch)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    harness.set_state(test_input, "foo")
    assert enabler.is_enabled() == True
    assert harness.get_state(test_switch) == "on"
    harness.set_state(test_input, "bar")
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"


def test_range_enabler_changes(harness: Harness) -> None:
    harness.set_state(test_input, 0)
    enabler: Any = harness.create_app(
        "enabler", "RangeEnabler", "enabler", entity=test_input, min=10, max=20
    )
    _create_enabled_switch(harness, "switch", "enabler", test_switch)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    harness.set_state(test_input, 15)
    assert enabler.is_enabled() == True
    assert harness.get_state(test_switch) == "on"
    harness.set_state(test_input, -15)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"


@pytest.mark.parametrize("harness", [{
    "start_date": date(2018, 2, 1),
    "start_time": time(12, 0, 0),
    "interval": timedelta(hours=1),
}], indirect=True)
def test_date_enabler_changes(harness: Harness, timing: Timing) -> None:
    enabler: Any = harness.create_app("enabler", "DateEnabler", "enabler", begin="02-03", end="02-04")
    _create_enabled_switch(harness, "switch", "enabler", test_switch)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    timing.state_should_change_at_datetime(test_switch, "on", datetime(2018, 2, 3, 1, 0, 0))
    assert enabler.is_enabled() == True
    timing.state_should_change_at_datetime(test_switch, "off", datetime(2018, 2, 5, 1, 0, 0))
    assert enabler.is_enabled() == False


@pytest.mark.parametrize("harness", [{
    "start_time": time(23, 59, 30),
    "interval": timedelta(seconds=1),
}], indirect=True)
def test_date_enabler_exact_change_time(harness: Harness, timing: Timing) -> None:
    enabler: Any = harness.create_app("enabler", "DateEnabler", "enabler", begin="01-02", end="01-02")
    _create_enabled_switch(harness, "switch", "enabler", test_switch)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    timing.state_should_change_at(test_switch, "on", time(0, 0, 1))
    assert enabler.is_enabled() == True


def test_multi_enabler_changes(harness: Harness) -> None:
    enabler1: Any = harness.create_app("enabler", "ScriptEnabler", "enabler1", initial=False)
    enabler2: Any = harness.create_app("enabler", "ScriptEnabler", "enabler2", initial=False)
    enabler: Any = harness.create_app(
        "enabler", "MultiEnabler", "enabler", enablers=["enabler1", "enabler2"]
    )
    _create_enabled_switch(harness, "switch", "enabler", test_switch)
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    harness.call_on_app(enabler1, "enable")
    assert enabler.is_enabled() == False
    assert harness.get_state(test_switch) == "off"
    harness.call_on_app(enabler2, "enable")
    assert enabler.is_enabled() == True
    assert harness.get_state(test_switch) == "on"