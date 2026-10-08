from __future__ import annotations
from datetime import time, timedelta

import pytest
from appdaemon_unit_test.test_helpers.harness import Harness
from auto_switch import AutoSwitch
from enabler import ScriptEnabler

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
    auto_switch, _ = _initialize(harness, "Switched", initial, target)
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


def test_target_change_new_none_ignored(harness: Harness) -> None:
    # A None state report must not drive any reaction. Set an intended
    # state against a stuck target first: pre-fix the on_target_change
    # None fallback resolved None → actual state "off" → wrong state →
    # a 10s re-command timer on top of the idle retry timer. Post-fix
    # the None is rejected with zero extra commands. Compare against a
    # control run without the None event: the steady 10s retry (armed
    # by intended_state) fires either way, so only the counts must be
    # identical, with no timer interaction from the None event.
    auto_switch, _ = _initialize(harness, "Basic", initial_target_state="off")
    assert harness.get_state(target) == "off"
    # Device rejects commands: count turn_on calls, never reflect them.
    turn_ons: list[str] = []

    def counting_turn_on(entity_id: str, namespace: str | None = None, **kwargs: object) -> dict[str, object]:
        turn_ons.append(entity_id)
        return {}

    auto_switch.turn_on = counting_turn_on  # type: ignore[method-assign, assignment]
    harness.call_on_app(auto_switch, "auto_turn_on")
    # auto_turn_on commanded once (stuck target ignores it); intended
    # state is now "on" and the steady 10s retry is armed.
    base_count = len(turn_ons)
    assert base_count == 1
    assert auto_switch.intended_state == "on"
    # Fire the None report: must be ignored entirely (no extra command
    # now and no timer re-arm; post-fix logs "Invalid state: None").
    harness.call_on_app(
        auto_switch, "on_target_change", target, None, "off", None
    )
    assert len(turn_ons) == base_count
    assert auto_switch.intended_state == "on"
    # The retry timer keeps its original cadence: pre-fix the fallback
    # resolved None → "off" → wrong state → re-armed the re-command on
    # top, adding an extra command vs the control cadence below.
    harness.advance_time(timedelta(seconds=10))
    assert len(turn_ons) == base_count + 1
    # Post-fix the intended state survives the None event untouched;
    # the 30s advance shows the retry cadence stayed exactly 10s.
    assert auto_switch.intended_state == "on"
    harness.advance_time(timedelta(seconds=30))
    assert len(turn_ons) == base_count + 4
    assert harness.get_state(target) == "off"


def test_switch_change_new_none_ignored(harness: Harness) -> None:
    # A None state report on the switch entity must not drive any
    # reaction: pre-fix the on_switch_change None fallback resolved
    # None → get_state(switch) → "auto" → the "Setting to auto" branch
    # called __update(self.state) → __stop_timer (cancelling the armed
    # retry) → an immediate turn_on on top of the pre-existing retry.
    # Post-fix the None is rejected with zero commands and zero timer
    # interaction: the armed retry keeps its original cadence.
    auto_switch, _ = _initialize(harness, "Switched", "auto", "off")
    assert harness.get_state(target) == "off"
    # Device rejects commands: count turn_on calls, never reflect them.
    turn_ons: list[str] = []

    def counting_turn_on(entity_id: str, namespace: str | None = None, **kwargs: object) -> dict[str, object]:
        turn_ons.append(entity_id)
        return {}

    auto_switch.turn_on = counting_turn_on  # type: ignore[method-assign, assignment]
    harness.call_on_app(auto_switch, "auto_turn_on")
    # auto_turn_on commanded once (stuck target ignores it); intended
    # state is "on" and the steady 10s retry is armed.
    base_count = len(turn_ons)
    assert base_count == 1
    assert auto_switch.intended_state == "on"
    # Fire the None report: must be ignored entirely — no extra
    # command now, no mode change, no exception (post-fix logs
    # "Invalid switch state: None").
    harness.call_on_app(
        auto_switch, "on_switch_change", switch, None, "auto", None
    )
    assert len(turn_ons) == base_count
    assert auto_switch.intended_state == "on"
    assert harness.get_state(switch) == "auto"
    assert harness.get_state(target) == "off"
    # No delayed reaction beyond the pre-existing retry cadence: the
    # 10s retry fires exactly once per window, same as without the
    # None event (pre-fix the None reset the cadence but also added
    # an immediate extra command, caught above).
    harness.advance_time(timedelta(seconds=10))
    assert len(turn_ons) == base_count + 1
    harness.advance_time(timedelta(seconds=30))
    assert len(turn_ons) == base_count + 4
    assert harness.get_state(target) == "off"


def test_wrong_state_flap_single_recommand(harness: Harness) -> None:
    # The device keeps reporting the wrong state (stuck); each report
    # must defer the re-command instead of issuing one immediately, so
    # exactly one re-command happens after a quiet period.
    auto_switch, _ = _initialize(harness, "Basic", initial_target_state="off")
    assert harness.get_state(target) == "off"
    # Device rejects commands: count turn_on calls, never reflect them.
    turn_ons: list[str] = []

    def counting_turn_on(entity_id: str, namespace: str | None = None, **kwargs: object) -> dict[str, object]:
        turn_ons.append(entity_id)
        return {}

    auto_switch.turn_on = counting_turn_on  # type: ignore[method-assign, assignment]
    harness.call_on_app(auto_switch, "auto_turn_on")
    assert harness.get_state(target) == "off"
    after_turn_on = len(turn_ons)
    # Repeated wrong-state reports within the 10s windows; each only
    # re-schedules the re-command timer.
    for _ in range(5):
        harness.call_on_app(
            auto_switch, "on_target_change", target, None, "on", "off"
        )
        assert harness.get_state(target) == "off"
    assert len(turn_ons) == after_turn_on
    # The last flap (at t=0) re-armed the re-command timer to fire at
    # t=10. Advance the full 10s so the step boundary lands exactly on
    # the fire time — do not rely on the harness rounding a shorter
    # advance up to the next step boundary. The update then re-arms a
    # steady 10s retry while the device stays stuck, so the next full
    # window adds exactly one more.
    harness.advance_time(timedelta(seconds=10))
    assert len(turn_ons) == after_turn_on + 1
    harness.advance_time(timedelta(seconds=10))
    assert len(turn_ons) == after_turn_on + 2
