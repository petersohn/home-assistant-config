from __future__ import annotations
from datetime import time, timedelta
from typing import Any

from conftest import Harness
from apps.hass import Hass
from unit_helpers.timing import Timing
from unit_helpers.history_util import (
    convert_history_input,
    convert_history_output,
    is_expected_history_found,
)

# Use 00:00:00 (matching the original Robot harness) so that absolute-time
# State Should Change At assertions line up with the start of the day.
_default_start_time = time(0, 0, 0)

alert_sensor = "binary_sensor.alert_sensor"
sensor1 = "binary_sensor.error1"
sensor2 = "binary_sensor.error2"
sensor3 = "binary_sensor.error3"


def _create_alert_aggregator(harness: Harness, **extra_args: Any) -> tuple[Hass, Hass]:
    alert = harness.create_app(
        "alert", "AlertAggregator", "alert",
        sources=[sensor1, sensor2, sensor3],
        target=alert_sensor,
        trigger_expr="v[name]",
        text_expr="name + ' is bad'",
        **extra_args,
    )
    alert_history = harness.create_app(
        "history", "HistoryManager", "alert_history",
        entity=alert_sensor,
    )
    return alert, alert_history


def _alarm_text_should_be(harness: Harness, *lines: str) -> None:
    expected = "\n".join(lines)
    assert harness.get_state(alert_sensor, attribute="text") == expected


def _should_have_history(harness: Harness, alert_history: Any, *expected_values: Any) -> None:
    converted_expected = convert_history_input(list(expected_values))
    values = harness.call_on_app(alert_history, "get_recorded_history")
    converted_values = convert_history_output(list(values))
    assert is_expected_history_found(converted_expected, converted_values)


def _state_should_cycle_at(harness: Harness, timing: Timing, entity: str, target_time: timedelta) -> None:
    assert harness.get_state(entity) == "on"
    target_datetime = harness.date_from_time(target_time, future=True)
    deadline = target_datetime - harness.interval
    timing.state_should_not_change_until(entity, deadline)
    harness.step()
    date = harness.datetime
    alert_history = harness.get_app("alert_history")
    _should_have_history(harness, alert_history, date, 0, date, 1)
    assert harness.get_state(entity) == "on"


def test_turn_alert_on_and_off(harness: Harness, timing: Timing) -> None:
    harness.set_state(sensor1, "off")
    harness.set_state(sensor2, "off")
    harness.set_state(sensor3, "off")
    alert, alert_history = _create_alert_aggregator(harness)

    assert harness.get_state(alert_sensor) == "off"
    harness.schedule_call_at(timedelta(minutes=1), "set_state", sensor1, "on")
    harness.schedule_call_at(timedelta(minutes=2), "set_state", sensor3, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", sensor2, "on")
    harness.schedule_call_at(timedelta(minutes=4), "set_state", sensor3, "off")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", sensor1, "off")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", sensor2, "off")

    timing.state_should_change_at(alert_sensor, "on", timedelta(minutes=1))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad")

    _state_should_cycle_at(harness, timing, alert_sensor, timedelta(minutes=2))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad", "binary_sensor.error3 is bad")

    _state_should_cycle_at(harness, timing, alert_sensor, timedelta(minutes=3))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad", "binary_sensor.error2 is bad", "binary_sensor.error3 is bad")

    timing.state_should_not_change_until(alert_sensor, timedelta(minutes=4))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad", "binary_sensor.error2 is bad")
    assert harness.get_state(alert_sensor) == "on"

    timing.state_should_not_change_until(alert_sensor, timedelta(minutes=5))
    _alarm_text_should_be(harness, "binary_sensor.error2 is bad")
    assert harness.get_state(alert_sensor) == "on"

    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=6))


def test_alert_on_at_the_beginning(harness: Harness, timing: Timing) -> None:
    harness.set_state(sensor1, "off")
    harness.set_state(sensor2, "on")
    harness.set_state(sensor3, "on")
    alert, alert_history = _create_alert_aggregator(harness)

    assert harness.get_state(alert_sensor) == "on"
    _alarm_text_should_be(harness, "binary_sensor.error2 is bad", "binary_sensor.error3 is bad")

    harness.schedule_call_at(timedelta(minutes=1), "set_state", sensor2, "off")
    harness.schedule_call_at(timedelta(minutes=2), "set_state", sensor3, "off")

    timing.state_should_not_change_until(alert_sensor, timedelta(minutes=1))
    _alarm_text_should_be(harness, "binary_sensor.error3 is bad")
    assert harness.get_state(alert_sensor) == "on"

    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=2))


def test_timeout(harness: Harness, timing: Timing) -> None:
    harness.set_state(sensor1, "off")
    harness.set_state(sensor2, "off")
    harness.set_state(sensor3, "off")
    timeout = {"minutes": 1}
    alert, alert_history = _create_alert_aggregator(harness, timeout=timeout)

    assert harness.get_state(alert_sensor) == "off"
    harness.schedule_call_at(timedelta(seconds=20), "set_state", sensor1, "on")
    harness.schedule_call_at(timedelta(minutes=2), "set_state", sensor1, "off")

    harness.schedule_call_at(timedelta(minutes=2, seconds=30), "set_state", sensor1, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", sensor2, "on")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", sensor1, "off")
    harness.schedule_call_at(timedelta(minutes=5, seconds=20), "set_state", sensor2, "off")

    harness.schedule_call_at(timedelta(minutes=6), "set_state", sensor3, "on")
    harness.schedule_call_at(timedelta(minutes=8), "set_state", sensor1, "on")
    harness.schedule_call_at(timedelta(minutes=8, seconds=30), "set_state", sensor1, "off")
    harness.schedule_call_at(timedelta(minutes=9, seconds=30), "set_state", sensor1, "on")
    harness.schedule_call_at(timedelta(minutes=11), "set_state", sensor3, "off")
    harness.schedule_call_at(timedelta(minutes=11, seconds=30), "set_state", sensor2, "on")
    harness.schedule_call_at(timedelta(minutes=12), "set_state", sensor1, "off")
    harness.schedule_call_at(timedelta(minutes=13), "set_state", sensor2, "off")

    timing.state_should_change_at(alert_sensor, "on", timedelta(minutes=1, seconds=20))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad")
    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=2))

    timing.state_should_change_at(alert_sensor, "on", timedelta(minutes=3, seconds=30))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad")
    _state_should_cycle_at(harness, timing, alert_sensor, timedelta(minutes=4))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad", "binary_sensor.error2 is bad")
    timing.state_should_not_change_until(alert_sensor, timedelta(minutes=5))
    _alarm_text_should_be(harness, "binary_sensor.error2 is bad")
    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=5, seconds=20))

    timing.state_should_change_at(alert_sensor, "on", timedelta(minutes=7))
    _alarm_text_should_be(harness, "binary_sensor.error3 is bad")
    _state_should_cycle_at(harness, timing, alert_sensor, timedelta(minutes=10, seconds=30))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad", "binary_sensor.error3 is bad")
    timing.state_should_not_change_until(alert_sensor, timedelta(minutes=11))
    _alarm_text_should_be(harness, "binary_sensor.error1 is bad")
    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=12))
    timing.state_should_change_at(alert_sensor, "on", timedelta(minutes=12, seconds=30))
    _alarm_text_should_be(harness, "binary_sensor.error2 is bad")
    timing.state_should_change_at(alert_sensor, "off", timedelta(minutes=13))