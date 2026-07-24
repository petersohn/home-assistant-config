from __future__ import annotations
from datetime import time
import pytest

# Use 00:00:00 (matching the original Robot harness).
_default_start_time = time(0, 0, 0)

target = "input_boolean.test_switch"
switch = "input_select.test_auto_switch_switch"


def _initialize(harness, type_, initial_switch_state="auto", initial_target_state="off"):
    harness.set_state(target, initial_target_state)
    harness.set_state(switch, initial_switch_state)
    args: dict = {"target": target}
    enabler = None
    if "Switched" in type_:
        args["switch"] = switch
    if "Reentrant" in type_:
        args["reentrant"] = True
    if "Enabled" in type_:
        enabler = harness.create_app("enabler", "ScriptEnabler", "switch_enabler")
        args["enabler"] = "switch_enabler"
    auto_switch = harness.create_app("auto_switch", "AutoSwitch", "test_auto_switch", **args)
    harness.step()
    return auto_switch, enabler


def _switch_on_and_off(harness, type_, initial_switch_state, initial_target_state, expected_off, expected_on):
    auto_switch, _ = _initialize(harness, type_, initial_switch_state, initial_target_state)
    assert harness.get_state(target) == expected_off
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == expected_on
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected_off
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == expected_on
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected_off


def _switch_on_and_off_with_enabler(harness, type_, initial_switch_state, initial_target_state, enabler_state, expected_off, expected_on):
    auto_switch, enabler = _initialize(harness, type_, initial_switch_state, initial_target_state)
    assert enabler is not None
    harness.call_on_app(enabler, enabler_state)
    assert harness.get_state(target) == expected_off
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == expected_on
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected_off
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == expected_on
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected_off


@pytest.mark.parametrize("type_, initial_switch_state, initial_target_state, expected_off, expected_on", [
    ("Basic", "auto", "off", "off", "on"),
    ("Basic", "auto", "on", "off", "on"),
    ("Switched", "auto", "off", "off", "on"),
    ("Switched", "auto", "on", "off", "on"),
    ("Switched", "on", "off", "on", "on"),
    ("Switched", "on", "on", "on", "on"),
    ("Switched", "off", "off", "off", "off"),
    ("Switched", "off", "on", "off", "off"),
])
def test_basic_usage(harness, type_, initial_switch_state, initial_target_state, expected_off, expected_on):
    _switch_on_and_off(harness, type_, initial_switch_state, initial_target_state, expected_off, expected_on)


@pytest.mark.parametrize("type_, initial_switch_state, initial_target_state, enabler_state, expected_off, expected_on", [
    ("Enabled", "auto", "off", "enable", "off", "on"),
    ("Enabled", "auto", "on", "enable", "off", "on"),
    ("Enabled", "auto", "off", "disable", "off", "off"),
    ("Enabled", "auto", "on", "disable", "off", "off"),
    ("EnabledSwitched", "auto", "off", "enable", "off", "on"),
    ("EnabledSwitched", "auto", "on", "enable", "off", "on"),
    ("EnabledSwitched", "on", "off", "enable", "on", "on"),
    ("EnabledSwitched", "on", "on", "enable", "on", "on"),
    ("EnabledSwitched", "off", "off", "enable", "off", "off"),
    ("EnabledSwitched", "off", "on", "enable", "off", "off"),
    ("EnabledSwitched", "auto", "off", "disable", "off", "off"),
    ("EnabledSwitched", "auto", "on", "disable", "off", "off"),
    ("EnabledSwitched", "on", "off", "disable", "on", "on"),
    ("EnabledSwitched", "on", "on", "disable", "on", "on"),
    ("EnabledSwitched", "off", "off", "disable", "off", "off"),
    ("EnabledSwitched", "off", "on", "disable", "off", "off"),
])
def test_basic_usage_with_enabler(harness, type_, initial_switch_state, initial_target_state, enabler_state, expected_off, expected_on):
    _switch_on_and_off_with_enabler(harness, type_, initial_switch_state, initial_target_state, enabler_state, expected_off, expected_on)


@pytest.mark.parametrize("initial, auto_switch_state, changed, expected", [
    ("auto", "off", "on", "on"),
    ("auto", "off", "off", "off"),
    ("on", "off", "off", "off"),
    ("on", "off", "auto", "off"),
    ("off", "off", "on", "on"),
    ("off", "off", "auto", "off"),
    ("auto", "on", "on", "on"),
    ("auto", "on", "off", "off"),
    ("on", "on", "off", "off"),
    ("on", "on", "auto", "on"),
    ("off", "on", "on", "on"),
    ("off", "on", "auto", "on"),
])
def test_switch_on_and_off_manually(harness, initial, auto_switch_state, changed, expected):
    auto_switch, _ = _initialize(harness, "Switched", initial, target)
    if auto_switch_state == "on":
        harness.call_on_app(auto_switch, "auto_turn_on")
    else:
        harness.call_on_app(auto_switch, "auto_turn_off")
    harness.set_state(switch, changed)
    assert harness.get_state(target) == expected


def test_target_state_changes(harness):
    auto_switch, _ = _initialize(harness, "Switched")
    harness.set_state(switch, "off")
    assert harness.get_state(target) == "off"
    harness.turn_on(target)
    assert harness.get_state(target) == "on"
    assert harness.get_state(switch) == "on"
    harness.turn_off(target)
    assert harness.get_state(target) == "off"
    assert harness.get_state(switch) == "off"

    harness.set_state(switch, "auto")
    harness.call_on_app(auto_switch, "auto_turn_off")
    harness.turn_on(target)
    assert harness.get_state(target) == "off"
    assert harness.get_state(switch) == "auto"
    harness.call_on_app(auto_switch, "auto_turn_on")
    harness.turn_off(target)
    assert harness.get_state(target) == "on"
    assert harness.get_state(switch) == "auto"


def test_enabled_state_changes(harness):
    auto_switch, enabler = _initialize(harness, "Enabled")
    assert enabler is not None
    harness.call_on_app(enabler, "enable")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    harness.call_on_app(enabler, "disable")
    assert harness.get_state(target) == "off"
    harness.call_on_app(enabler, "enable")
    assert harness.get_state(target) == "on"


@pytest.mark.parametrize("type_, expected", [
    ("Basic", "off"),
    ("Reentrant", "on"),
])
def test_reentrancy(harness, type_, expected):
    auto_switch, _ = _initialize(harness, type_, "auto", "off")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == "off"