from __future__ import annotations
from datetime import time, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from appdaemon_unit_test.test_helpers.harness import Harness
from auto_switch import AutoSwitch
from enabler import ScriptEnabler

if TYPE_CHECKING:
    # Static type only: the harness loads the helper as top-level module
    # "test_switch" (distinct class object from this package-qualified
    # module, same file), so isinstance cannot hold at runtime. The
    # creation sites cast instead, with a comment there.
    from appdaemon_unit_test.test_helpers.test_switch import TestSwitch

# Use 00:00:00.
_default_start_time = time(0, 0, 0)

target = "input_boolean.test_switch"
switch = "input_select.test_auto_switch_switch"


def _initialize(harness: Harness, type_: str, initial_switch_state: str = "auto", initial_target_state: str = "off") -> tuple[AutoSwitch, ScriptEnabler | None]:
    harness.set_state(target, initial_target_state)
    harness.set_state(switch, initial_switch_state)
    args: dict[str, object] = {"target": target}
    enabler = None
    if "Switched" in type_:
        args["switch"] = switch
    if "Reentrant" in type_:
        args["reentrant"] = True
    if "Enabled" in type_:
        enabler = harness.create_app("enabler", "ScriptEnabler", "switch_enabler")
        assert isinstance(enabler, ScriptEnabler)
        args["enabler"] = "switch_enabler"
    auto_switch = harness.create_app("auto_switch", "AutoSwitch", "test_auto_switch", **args)
    assert isinstance(auto_switch, AutoSwitch)
    harness.step()
    return auto_switch, enabler


def _switch_on_and_off(harness: Harness, type_: str, initial_switch_state: str, initial_target_state: str, expected_off: str, expected_on: str) -> None:
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


def _switch_on_and_off_with_enabler(harness: Harness, type_: str, initial_switch_state: str, initial_target_state: str, enabler_state: str, expected_off: str, expected_on: str) -> None:
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
def test_basic_usage(harness: Harness, type_: str, initial_switch_state: str, initial_target_state: str, expected_off: str, expected_on: str) -> None:
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
def test_basic_usage_with_enabler(harness: Harness, type_: str, initial_switch_state: str, initial_target_state: str, enabler_state: str, expected_off: str, expected_on: str) -> None:
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
def test_switch_on_and_off_manually(harness: Harness, initial: str, auto_switch_state: str, changed: str, expected: str) -> None:
    auto_switch, _ = _initialize(harness, "Switched", initial, "off")
    if auto_switch_state == "on":
        harness.call_on_app(auto_switch, "auto_turn_on")
    else:
        harness.call_on_app(auto_switch, "auto_turn_off")
    harness.set_state(switch, changed)
    assert harness.get_state(target) == expected


def test_target_state_changes(harness: Harness) -> None:
    auto_switch, _ = _initialize(harness, "Switched")
    harness.set_state(switch, "off")
    assert harness.get_state(target) == "off"
    harness.turn_on(target)
    assert harness.get_state(target) == "off"
    assert harness.get_state(switch) == "off"
    harness.set_state(switch, "on")
    assert harness.get_state(target) == "on"
    harness.turn_off(target)
    assert harness.get_state(target) == "on"
    assert harness.get_state(switch) == "on"

    harness.set_state(switch, "auto")
    harness.call_on_app(auto_switch, "auto_turn_off")
    harness.turn_on(target)
    assert harness.get_state(target) == "off"
    assert harness.get_state(switch) == "auto"
    harness.call_on_app(auto_switch, "auto_turn_on")
    harness.turn_off(target)
    assert harness.get_state(target) == "on"
    assert harness.get_state(switch) == "auto"


def test_enabled_state_changes(harness: Harness) -> None:
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
def test_reentrancy(harness: Harness, type_: str, expected: str) -> None:
    auto_switch, _ = _initialize(harness, type_, "auto", "off")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == expected
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == "off"


def test_target_unavailable(harness: Harness) -> None:
    auto_switch, _ = _initialize(harness, "Basic")
    harness.set_state(target, "unavailable")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "unavailable"
    harness.call_on_app(auto_switch, "auto_turn_off")
    assert harness.get_state(target) == "unavailable"


def test_target_unavailable_manual_mode(harness: Harness) -> None:
    _initialize(harness, "Switched")
    harness.set_state(switch, "on")
    harness.set_state(target, "unavailable")
    harness.step()
    assert harness.get_state(target) == "unavailable"


def test_target_unavailable_retry_after_recovery(harness: Harness) -> None:
    auto_switch, _ = _initialize(harness, "Basic")
    harness.set_state(target, "unavailable")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "unavailable"
    harness.set_state(target, "off")
    harness.step()
    assert harness.get_state(target) == "on"


def test_target_unavailable_recovery_to_wrong_state(harness: Harness) -> None:
    auto_switch, _ = _initialize(harness, "Basic", initial_target_state="off")
    assert harness.get_state(target) == "off"
    harness.set_state(target, "unavailable")
    harness.step()
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "unavailable"
    harness.set_state(target, "off")
    harness.step()
    assert harness.get_state(target) == "on"


def _create_test_switch(
    harness: Harness, name: str, **args: object
) -> "TestSwitch":
    return cast(
        "TestSwitch",
        harness.create_app("test_switch", "TestSwitch", name, **args),
    )


def _initialize_with_stuck_target(
    harness: Harness,
    type_: str,
    initial_target_state: str = "off",
    initial_switch_state: str = "auto",
) -> tuple[AutoSwitch, "TestSwitch"]:
    test_switch = _create_test_switch(
        harness,
        "test_switch",
        entity=target,
        stuck=True,
        state=initial_target_state,
    )
    auto_switch, _ = _initialize(
        harness, type_, initial_switch_state, initial_target_state
    )
    return auto_switch, test_switch


def _turn_on_count(harness: Harness) -> int:
    return len(
        harness.service_calls(
            service="homeassistant/turn_on", entity_id=target
        )
    )


def _command_count(harness: Harness, state: str) -> int:
    return len(
        harness.service_calls(
            service=f"homeassistant/turn_{state}", entity_id=target
        )
    )


def test_target_change_new_none_ignored(harness: Harness) -> None:
    auto_switch, device = _initialize_with_stuck_target(harness, "Basic")
    assert harness.get_state(target) == "off"
    harness.call_on_app(auto_switch, "auto_turn_on")
    base_count = _turn_on_count(harness)
    assert base_count == 1

    harness.call_on_app(device, "glitch")
    assert _turn_on_count(harness) == base_count

    harness.advance_time(timedelta(seconds=10))
    assert _turn_on_count(harness) == base_count + 1
    harness.advance_time(timedelta(seconds=30))
    assert _turn_on_count(harness) == base_count + 4
    assert harness.get_state(target) == "off"


def test_switch_change_new_none_ignored(harness: Harness) -> None:
    auto_switch, _ = _initialize_with_stuck_target(harness, "Switched")
    test_select = _create_test_switch(
        harness, "test_select", entity=switch, stuck=True, state="auto"
    )
    assert harness.get_state(target) == "off"
    harness.call_on_app(auto_switch, "auto_turn_on")
    base_count = _turn_on_count(harness)
    assert base_count == 1

    harness.call_on_app(test_select, "glitch")
    assert _turn_on_count(harness) == base_count + 1
    assert harness.get_state(switch) == "auto"
    assert harness.get_state(target) == "off"

    harness.advance_time(timedelta(seconds=10))
    assert _turn_on_count(harness) == base_count + 2
    harness.advance_time(timedelta(seconds=30))
    assert _turn_on_count(harness) == base_count + 5
    assert harness.get_state(target) == "off"


def test_wrong_state_flap_single_recommand(harness: Harness) -> None:
    auto_switch, _ = _initialize_with_stuck_target(harness, "Basic")
    assert harness.get_state(target) == "off"
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "off"

    after_turn_on = _turn_on_count(harness)
    for _ in range(5):
        harness.set_state(target, "unavailable")
        harness.set_state(target, "off")
        assert harness.get_state(target) == "off"
    assert _turn_on_count(harness) == after_turn_on

    harness.advance_time(timedelta(seconds=10))
    assert _turn_on_count(harness) == after_turn_on + 1
    harness.advance_time(timedelta(seconds=10))
    assert _turn_on_count(harness) == after_turn_on + 2
    assert harness.get_state(target) == "off"


def _assert_five_retries(
    harness: Harness, state: str, initial_count: int
) -> None:
    for retry in range(1, 6):
        harness.advance_time(timedelta(seconds=10))
        assert _command_count(harness, state) == initial_count + retry
    harness.advance_time(timedelta(seconds=10))
    assert _command_count(harness, state) == initial_count + 5


@pytest.mark.parametrize(
    "mode, desired_state, initial_target_state",
    [
        ("auto", "on", "off"),
        ("auto", "on", "unknown"),
        ("auto", "off", "on"),
        ("auto", "off", "unknown"),
        ("on", "on", "off"),
        ("on", "on", "unknown"),
        ("off", "off", "on"),
        ("off", "off", "unknown"),
    ],
)
def test_retry_limit_is_initial_command_plus_five(
    harness: Harness,
    mode: str,
    desired_state: str,
    initial_target_state: str,
) -> None:
    auto_switch, _ = _initialize_with_stuck_target(
        harness, "Switched", initial_target_state
    )
    initial_count = _command_count(harness, desired_state)

    if mode == "auto":
        if desired_state == "on":
            harness.call_on_app(auto_switch, "auto_turn_on")
            assert _command_count(harness, desired_state) == initial_count + 1
        else:
            assert initial_count == 1
    else:
        harness.set_state(switch, mode)
        assert _command_count(harness, desired_state) == initial_count + 1

    _assert_five_retries(
        harness, desired_state, _command_count(harness, desired_state)
    )


@pytest.mark.parametrize(
    "initial_switch_state, desired_state",
    [("auto", "off"), ("on", "on"), ("off", "off")],
)
def test_unknown_target_at_startup_allows_command(
    harness: Harness, initial_switch_state: str, desired_state: str
) -> None:
    _initialize_with_stuck_target(
        harness, "Switched", "unknown", initial_switch_state
    )

    assert _command_count(harness, desired_state) >= 1


@pytest.mark.parametrize(
    "desired_state, initial_target_state",
    [("on", "off"), ("off", "on")],
)
def test_unknown_target_transition_is_mismatch(
    harness: Harness, desired_state: str, initial_target_state: str
) -> None:
    auto_switch, _ = _initialize_with_stuck_target(
        harness, "Basic", initial_target_state
    )
    if desired_state == "on":
        harness.call_on_app(auto_switch, "auto_turn_on")
    initial_count = _command_count(harness, desired_state)
    assert initial_count == (1 if desired_state == "on" else 2)

    harness.set_state(target, "unknown")
    assert _command_count(harness, desired_state) == initial_count
    harness.advance_time(timedelta(seconds=10))
    assert _command_count(harness, desired_state) == initial_count + 1


@pytest.mark.parametrize("reset_by", ["target", "mode", "automation", "enabler"])
def test_exhausted_retry_budget_resets_on_change(
    harness: Harness, reset_by: str
) -> None:
    type_ = (
        "Enabled"
        if reset_by == "enabler"
        else "Switched"
        if reset_by == "mode"
        else "Basic"
    )
    auto_switch, _ = _initialize_with_stuck_target(harness, type_)
    enabler = harness.get_app("switch_enabler")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert _command_count(harness, "on") == 1
    _assert_five_retries(harness, "on", 1)

    if reset_by == "target":
        harness.set_state(target, "unknown")
        harness.advance_time(timedelta(seconds=10))
    elif reset_by == "mode":
        harness.set_state(switch, "on")
    elif reset_by == "automation":
        harness.call_on_app(auto_switch, "auto_turn_off")
        harness.call_on_app(auto_switch, "auto_turn_on")
    else:
        assert isinstance(enabler, ScriptEnabler)
        harness.call_on_app(enabler, "disable")
        harness.call_on_app(enabler, "enable")

    assert _command_count(harness, "on") == 7
    _assert_five_retries(harness, "on", 7)


def test_unchanged_demand_and_retry_callbacks_do_not_reset_budget(
    harness: Harness,
) -> None:
    auto_switch, _ = _initialize_with_stuck_target(harness, "Basic")
    harness.call_on_app(auto_switch, "auto_turn_on")

    for _ in range(4):
        harness.advance_time(timedelta(seconds=10))
    assert _command_count(harness, "on") == 5

    harness.call_on_app(auto_switch, "auto_turn_on")
    assert _command_count(harness, "on") == 5
    harness.advance_time(timedelta(seconds=10))
    assert _command_count(harness, "on") == 6
    harness.advance_time(timedelta(seconds=50))
    assert _command_count(harness, "on") == 6


def test_matching_target_cancels_retries(harness: Harness) -> None:
    auto_switch, _ = _initialize_with_stuck_target(harness, "Basic")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert _command_count(harness, "on") == 1

    harness.set_state(target, "on")
    harness.advance_time(timedelta(seconds=60))
    assert _command_count(harness, "on") == 1


@pytest.mark.parametrize("mode", ["on", "off"])
@pytest.mark.parametrize("reset_by", ["automation", "enabler"])
def test_manual_retry_budget_restarts_on_demand_change(
    harness: Harness, mode: str, reset_by: str
) -> None:
    auto_switch, _ = _initialize_with_stuck_target(
        harness, "EnabledSwitched", "off" if mode == "on" else "on"
    )
    harness.call_on_app(auto_switch, "auto_turn_on")
    harness.set_state(switch, mode)
    initial_count = _command_count(harness, mode)
    _assert_five_retries(harness, mode, initial_count)

    if reset_by == "automation":
        harness.call_on_app(auto_switch, "auto_turn_off")
    else:
        enabler = harness.get_app("switch_enabler")
        assert isinstance(enabler, ScriptEnabler)
        harness.call_on_app(enabler, "disable")

    assert _command_count(harness, mode) == initial_count + 6
    _assert_five_retries(harness, mode, initial_count + 6)


def test_successful_stabilization_cancels_retries(harness: Harness) -> None:
    _create_test_switch(harness, "test_switch", entity=target)
    auto_switch, _ = _initialize(harness, "Basic")
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "on"
    assert _command_count(harness, "on") == 1

    harness.advance_time(timedelta(seconds=60))
    assert _command_count(harness, "on") == 1


@pytest.mark.parametrize(
    "mode, desired_state", [("auto", "off"), ("on", "on"), ("off", "off")]
)
def test_responsive_unknown_target_at_startup_stabilizes(
    harness: Harness, mode: str, desired_state: str
) -> None:
    _create_test_switch(harness, "test_switch", entity=target, state="unknown")
    _initialize(harness, "Switched", mode, "unknown")

    assert harness.get_state(target) == desired_state
    assert _command_count(harness, desired_state) == 1
    command_count = len(harness.service_calls(entity_id=target))

    harness.advance_time(timedelta(seconds=60))
    assert harness.get_state(target) == desired_state
    assert len(harness.service_calls(entity_id=target)) == command_count


@pytest.mark.parametrize(
    "mode, desired_state",
    [("auto", "on"), ("auto", "off"), ("on", "on"), ("off", "off")],
)
def test_responsive_unknown_target_transition_stabilizes(
    harness: Harness, mode: str, desired_state: str
) -> None:
    _create_test_switch(harness, "test_switch", entity=target)
    auto_switch, _ = _initialize(harness, "Switched", mode)
    if mode == "auto" and desired_state == "on":
        harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == desired_state
    initial_count = _command_count(harness, desired_state)

    harness.set_state(target, "unknown")
    assert harness.get_state(target) == desired_state
    assert _command_count(harness, desired_state) == initial_count + 1
    command_count = len(harness.service_calls(entity_id=target))

    harness.advance_time(timedelta(seconds=60))
    assert harness.get_state(target) == desired_state
    assert len(harness.service_calls(entity_id=target)) == command_count
