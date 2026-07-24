from __future__ import annotations
from datetime import time, timedelta
from typing import Any

from helpers.history_util import convert_history_input, convert_history_output

# Use 00:00:00 (matching the original Robot harness) so the absolute
# datetime history assertions in the timer sequence tests match.
_default_start_time = time(0, 0, 0)

motion_detector = "binary_sensor.motion_detector"
sensor = "sensor.test_sensor"
switch = "input_boolean.test_switch"
switch2 = "input_boolean.test_switch2"
switch3 = "input_boolean.test_switch3"
time_entity = "sensor.timer_switch_time"


def _create_auto_switch(harness, name, target):
    return harness.create_app(
        "auto_switch", "AutoSwitch", name,
        reentrant=True, target=target,
    )


def _create_timer_switch(harness, time: Any = 1, **args):
    _create_auto_switch(harness, "auto_switch", switch)
    enabler = harness.create_app("enabler", "ScriptEnabler", "enabler")
    harness.create_app(
        "timer_switch", "TimerSwitch", "timer_switch",
        enabler="enabler", targets=["auto_switch"], time=time, **args,
    )
    return enabler


def _create_timer_sequence(harness, **args):
    enabler = harness.create_app("enabler", "ScriptEnabler", "enabler")
    harness.create_app(
        "timer_switch", "TimerSequence", "timer_sequence",
        enabler="enabler", **args,
    )
    return enabler


def _create_history_manager(harness, name, entity):
    return harness.create_app(
        "history", "HistoryManager", name,
        entity=entity, max_interval={"hours": 1},
    )


def _history_should_be(harness, app, *expected_values):
    converted_expected = convert_history_input(list(expected_values))
    values = harness.call_on_app(app, "get_recorded_history")
    converted_values = convert_history_output(list(values))
    assert converted_values == converted_expected


def _set_enabled_state(harness, enabler, state):
    harness.call_on_app(enabler, state)


def test_switch_on_and_off_normal(harness):
    _create_timer_switch(harness, sensor=motion_detector)

    harness.set_state(motion_detector, "on")
    harness.set_state(motion_detector, "off")
    assert harness.get_state(switch) == "on"
    assert harness.get_state(switch) == "on"
    deadline = harness.date_from_time(timedelta(minutes=1), future=True) - harness.interval
    harness.wait_for_state_change(switch, deadline_datetime=deadline)
    assert harness.get_state(switch) == "on"
    harness.step()
    assert harness.get_state(switch) == "off"


def test_switch_on_and_off_expr(harness):
    _create_timer_switch(harness, expr=f"v.{motion_detector}")

    harness.set_state(motion_detector, "on")
    harness.set_state(motion_detector, "off")
    assert harness.get_state(switch) == "on"
    deadline = harness.date_from_time(timedelta(minutes=1), future=True) - harness.interval
    harness.wait_for_state_change(switch, deadline_datetime=deadline)
    assert harness.get_state(switch) == "on"
    harness.step()
    assert harness.get_state(switch) == "off"


def _switch_off_after_motion_restarts(harness, **args):
    _create_timer_switch(harness, **args)
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=30), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(seconds=50), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=20))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2))


def test_switch_off_after_motion_restarts_normal(harness):
    _switch_off_after_motion_restarts(harness, sensor=motion_detector)


def test_switch_off_after_motion_restarts_expr(harness):
    _switch_off_after_motion_restarts(harness, expr=f"v.{motion_detector}")


def _do_not_start_if_enabler_is_disabled(harness, **args):
    enabler = _create_timer_switch(harness, **args)
    _set_enabled_state(harness, enabler, "disable")
    harness.set_state(motion_detector, "on")
    harness.set_state(motion_detector, "off")
    assert harness.get_state(switch) == "off"


def test_do_not_start_if_enabler_is_disabled_normal(harness):
    _do_not_start_if_enabler_is_disabled(harness, sensor=motion_detector)


def test_do_not_start_if_enabler_is_disabled_expr(harness):
    _do_not_start_if_enabler_is_disabled(harness, expr=f"v.{motion_detector}")


def _switch_off_when_enabler_is_disabled(harness, **args):
    enabler = _create_timer_switch(harness, **args)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=40), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=1), "call_on_app", enabler, "disable")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=30))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=1))


def test_switch_off_when_enabler_is_disabled_normal(harness):
    _switch_off_when_enabler_is_disabled(harness, sensor=motion_detector)


def test_switch_off_when_enabler_is_disabled_expr(harness):
    _switch_off_when_enabler_is_disabled(harness, expr=f"v.{motion_detector}")


def _switch_on_when_enabler_is_enabled_while_in_motion(harness, **args):
    enabler = _create_timer_switch(harness, **args)
    _set_enabled_state(harness, enabler, "disable")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=50), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=50))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2))


def test_switch_on_when_enabler_is_enabled_while_in_motion_normal(harness):
    _switch_on_when_enabler_is_enabled_while_in_motion(harness, sensor=motion_detector)


def test_switch_on_when_enabler_is_enabled_while_in_motion_expr(harness):
    _switch_on_when_enabler_is_enabled_while_in_motion(harness, expr=f"v.{motion_detector}")


def _stop_at_disabling_and_restart_after_enabling(harness, **args):
    enabler = _create_timer_switch(harness, **args)
    harness.set_state(motion_detector, "on")
    harness.set_state(motion_detector, "off")
    assert harness.get_state(switch) == "on"
    harness.schedule_call_at(timedelta(seconds=30), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=1, seconds=10), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1, seconds=20), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=2, seconds=30), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=2, seconds=40), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=2, seconds=50), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "off", timedelta(seconds=30))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=2, seconds=40))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=3, seconds=50))


def test_stop_at_disabling_and_restart_after_enabling_normal(harness):
    _stop_at_disabling_and_restart_after_enabling(harness, sensor=motion_detector)


def test_stop_at_disabling_and_restart_after_enabling_expr(harness):
    _stop_at_disabling_and_restart_after_enabling(harness, expr=f"v.{motion_detector}")


def _stop_at_disabling_and_restart_at_enabling_while_in_motion(harness, **args):
    enabler = _create_timer_switch(harness, **args)
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=30), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=1), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=1, seconds=30), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=20))
    _state_should_change_at(harness, switch, "off", timedelta(seconds=30))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=1))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2, seconds=30))


def test_stop_at_disabling_and_restart_at_enabling_while_in_motion_normal(harness):
    _stop_at_disabling_and_restart_at_enabling_while_in_motion(harness, sensor=motion_detector)


def test_stop_at_disabling_and_restart_at_enabling_while_in_motion_expr(harness):
    _stop_at_disabling_and_restart_at_enabling_while_in_motion(harness, expr=f"v.{motion_detector}")


def _start_when_motion_at_initialization(harness, **args):
    harness.set_state(motion_detector, "on")
    _create_timer_switch(harness, **args)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", motion_detector, "off")

    assert harness.get_state(switch) == "on"
    _state_should_change_at(harness, switch, "off", timedelta(minutes=1, seconds=30))


def test_start_when_motion_at_initialization_normal(harness):
    _start_when_motion_at_initialization(harness, sensor=motion_detector)


def test_start_when_motion_at_initialization_expr(harness):
    _start_when_motion_at_initialization(harness, expr=f"v.{motion_detector}")


def _delay(harness, **args):
    _create_timer_switch(harness, time=1, delay=30, **args)
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1, seconds=40), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=4), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=4, seconds=20), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(minutes=1, seconds=30))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2, seconds=40))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=5, seconds=30))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=7))


def test_delay_normal(harness):
    _delay(harness, sensor=motion_detector)


def test_delay_expr(harness):
    _delay(harness, expr=f"v.{motion_detector}")


def test_timer_sequence(harness):
    _create_auto_switch(harness, "auto_switch", switch)
    sequence = [{"targets": ["auto_switch"], "time": 1}]
    enabler = _create_timer_sequence(harness, sensor=motion_detector, sequence=sequence)

    _set_enabled_state(harness, enabler, "disable")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=40), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(seconds=50), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=1, seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1, seconds=40), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=5, seconds=30), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=5, seconds=40), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=6, seconds=10), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(minutes=1, seconds=20))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2, seconds=20))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=3))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=4))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=5, seconds=30))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=6, seconds=30))


def test_multi_timer_sequence(harness):
    _create_auto_switch(harness, "auto_switch1", switch)
    _create_auto_switch(harness, "auto_switch2", switch2)
    _create_auto_switch(harness, "auto_switch3", switch3)
    sequence = [
        {"targets": ["auto_switch1", "auto_switch3"], "time": 1},
        {"time": 3},
        {"targets": ["auto_switch2"], "time": 2},
    ]
    enabler = _create_timer_sequence(harness, sensor=motion_detector, sequence=sequence)

    switch1_history = _create_history_manager(harness, "history1", switch)
    switch2_history = _create_history_manager(harness, "history2", switch2)
    switch3_history = _create_history_manager(harness, "history3", switch3)

    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=30), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=7), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=7, seconds=10), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=11, seconds=30), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=11, seconds=40), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=12), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=12, seconds=10), "set_state", motion_detector, "off")

    harness.advance_time_to(timedelta(minutes=19))
    _history_should_be(harness, switch1_history,
                       "2018-01-01 00:00:20", 1,
                       "2018-01-01 00:01:20", 0,
                       "2018-01-01 00:07:00", 1,
                       "2018-01-01 00:08:00", 0,
                       "2018-01-01 00:12:00", 1,
                       "2018-01-01 00:13:00", 0)
    _history_should_be(harness, switch2_history,
                       "2018-01-01 00:04:20", 1,
                       "2018-01-01 00:06:20", 0,
                       "2018-01-01 00:11:00", 1,
                       "2018-01-01 00:11:30", 0,
                       "2018-01-01 00:16:00", 1,
                       "2018-01-01 00:18:00", 0)
    _history_should_be(harness, switch3_history,
                       "2018-01-01 00:00:20", 1,
                       "2018-01-01 00:01:20", 0,
                       "2018-01-01 00:07:00", 1,
                       "2018-01-01 00:08:00", 0,
                       "2018-01-01 00:12:00", 1,
                       "2018-01-01 00:13:00", 0)


def test_other_target_state(harness):
    harness.set_state(motion_detector, "on")
    _create_timer_switch(harness, time=1, sensor=motion_detector, target_state="off")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(seconds=50), "set_state", motion_detector, "on")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=20))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=1, seconds=50))


def test_indirect_time(harness):
    _create_timer_switch(harness, time=time_entity, sensor=motion_detector)
    harness.set_state(time_entity, 1.5)
    harness.schedule_call_at(timedelta(seconds=20), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(seconds=30), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=3, seconds=20), "set_state", time_entity, 2)
    harness.schedule_call_at(timedelta(minutes=3, seconds=30), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=6, seconds=10), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=6, seconds=20), "set_state", time_entity, 1)
    harness.schedule_call_at(timedelta(minutes=9), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=9, seconds=10), "set_state", motion_detector, "off")

    _state_should_change_at(harness, switch, "on", timedelta(seconds=20))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=2))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=3))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=5, seconds=30))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=6))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=8, seconds=10))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=9))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=10, seconds=10))


def test_source_state(harness):
    _create_auto_switch(harness, "auto_switch", switch)
    sequence = [{"targets": ["auto_switch"], "time": 1}]
    enabler = _create_timer_sequence(
        harness, sensor=sensor, sequence=sequence,
        source_state="foo", target_state="bar",
    )
    _set_enabled_state(harness, enabler, "enable")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", sensor, "foobar")
    harness.schedule_call_at(timedelta(minutes=1), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=2), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=2, seconds=30), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=8), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=8, seconds=10), "call_on_app", enabler, "disable")
    harness.schedule_call_at(timedelta(minutes=8, seconds=20), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=8, seconds=30), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=8, seconds=50), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=9), "call_on_app", enabler, "enable")
    harness.schedule_call_at(timedelta(minutes=10), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=12), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=13), "set_state", sensor, "")
    harness.schedule_call_at(timedelta(minutes=14), "set_state", sensor, "bar")
    harness.schedule_call_at(timedelta(minutes=15), "set_state", sensor, "foo")
    harness.schedule_call_at(timedelta(minutes=17), "set_state", sensor, "bar")

    _state_should_change_at(harness, switch, "on", timedelta(minutes=2, seconds=30))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=3, seconds=30))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=6))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=7))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=10))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=11))
    _state_should_change_at(harness, switch, "on", timedelta(minutes=17))
    _state_should_change_at(harness, switch, "off", timedelta(minutes=18))


def test_timer_sequence_restart(harness):
    _create_auto_switch(harness, "auto_switch1", switch)
    _create_auto_switch(harness, "auto_switch2", switch2)
    sequence = [
        {"targets": ["auto_switch1"], "time": 1},
        {"targets": ["auto_switch2"], "time": 2},
    ]
    _create_timer_sequence(
        harness, sensor=motion_detector, sequence=sequence, restart_on_trigger=True,
    )

    switch1_history = _create_history_manager(harness, "history1", switch)
    switch2_history = _create_history_manager(harness, "history2", switch2)

    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1, seconds=10), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=1, seconds=30), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=1, seconds=40), "set_state", motion_detector, "off")
    harness.schedule_call_at(timedelta(minutes=3, seconds=30), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=3, seconds=40), "set_state", motion_detector, "off")

    harness.advance_time_to(timedelta(minutes=8))
    _history_should_be(harness, switch1_history,
                       "2018-01-01 00:01:00", 1,
                       "2018-01-01 00:02:30", 0,
                       "2018-01-01 00:03:30", 1,
                       "2018-01-01 00:04:30", 0)
    _history_should_be(harness, switch2_history,
                       "2018-01-01 00:02:30", 1,
                       "2018-01-01 00:03:30", 0,
                       "2018-01-01 00:04:30", 1,
                       "2018-01-01 00:06:30", 0)


def test_timer_sequence_rising_edge(harness):
    _create_auto_switch(harness, "auto_switch1", switch)
    sequence = [{"targets": ["auto_switch1"], "time": 1}]
    _create_timer_sequence(
        harness, sensor=motion_detector, sequence=sequence,
        rising_edge=True, falling_edge=False,
    )
    history = _create_history_manager(harness, "history", switch)
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", motion_detector, "off")

    harness.advance_time_to(timedelta(minutes=5))
    _history_should_be(harness, history,
                       "2018-01-01 00:01:00", 1,
                       "2018-01-01 00:02:00", 0)


def test_timer_sequence_falling_edge(harness):
    _create_auto_switch(harness, "auto_switch1", switch)
    sequence = [{"targets": ["auto_switch1"], "time": 1}]
    _create_timer_sequence(
        harness, sensor=motion_detector, sequence=sequence,
        rising_edge=False, falling_edge=True,
    )
    history = _create_history_manager(harness, "history", switch)
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", motion_detector, "off")

    harness.advance_time_to(timedelta(minutes=5))
    _history_should_be(harness, history,
                       "2018-01-01 00:03:00", 1,
                       "2018-01-01 00:04:00", 0)


def test_timer_sequence_both_edges(harness):
    _create_auto_switch(harness, "auto_switch1", switch)
    sequence = [{"targets": ["auto_switch1"], "time": 1}]
    _create_timer_sequence(
        harness, sensor=motion_detector, sequence=sequence,
        rising_edge=True, falling_edge=True,
    )
    history = _create_history_manager(harness, "history", switch)
    harness.schedule_call_at(timedelta(minutes=1), "set_state", motion_detector, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", motion_detector, "off")

    harness.advance_time_to(timedelta(minutes=5))
    _history_should_be(harness, history,
                       "2018-01-01 00:01:00", 1,
                       "2018-01-01 00:02:00", 0,
                       "2018-01-01 00:03:00", 1,
                       "2018-01-01 00:04:00", 0)


def _state_should_change_at(harness, entity, value, target_time):
    target = harness.date_from_time(target_time, future=True)
    deadline = target - harness.interval
    assert harness.get_state(entity) != value
    harness.wait_for_state_change(entity, deadline_datetime=deadline)
    assert harness.get_state(entity) != value
    assert harness.datetime == deadline
    harness.step()
    assert harness.get_state(entity) == value