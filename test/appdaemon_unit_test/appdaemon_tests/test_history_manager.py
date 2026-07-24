from __future__ import annotations
from datetime import timedelta, time
from typing import Any

from conftest import Harness
from apps.hass import Hass
from unit_helpers.timing import Timing
from unit_helpers.history_util import convert_history_input, convert_history_output
from unit_helpers.race_test_helper import patch_load_history

# Use 00:00:00 (matching the original Robot harness) so absolute-time
# assertions (e.g. ChangeTracker Check Date Updates) line up with the
# start of the day.
_default_start_time = time(0, 0, 0)

entity = "sensor.test_sensor"
aggregated_entity = "sensor.test_sensor_aggregated"
sum_entity = "sensor.test_sensor_sum"
min_entity = "sensor.test_sensor_min"
max_entity = "sensor.test_sensor_max"
enabler_entity = "input_boolean.test_switch2"


def _create_history_manager(harness: Harness, name: str = "history_manager") -> Hass:
    return harness.create_app(
        "history", "HistoryManager", name,
        entity=entity, max_interval={"hours": 1},
    )


def _initialize_history_manager(harness: Harness, name: str = "history_manager") -> Hass:
    harness.set_state(entity, 0)
    return _create_history_manager(harness, name)


def _initialize_history_manager_with_race(
    harness: Harness, history: Any, race_value: Any,
) -> Hass:
    harness.set_state(entity, 0)
    patch_load_history(harness.app_manager, history, race_value)
    return _create_history_manager(harness)


def _history_should_be(harness: Harness, app: Hass, *expected_values: Any) -> None:
    converted_expected = convert_history_input(list(expected_values))
    values = harness.call_on_app(app, "get_recorded_history")
    converted_values = convert_history_output(list(values))
    assert converted_values == converted_expected


def _times_should_match(harness: Harness, actual: Any, expected_time: time | timedelta) -> None:
    expected = harness.date_from_time(expected_time, future=False)
    assert actual == expected


def _check_date_updates(
    harness: Harness, change_tracker: Hass,
    expected_changed: timedelta, expected_updated: timedelta,
) -> None:
    actual_changed = harness.call_on_app(change_tracker, "last_changed")
    _times_should_match(harness, actual_changed, expected_changed)
    actual_updated = harness.call_on_app(change_tracker, "last_updated")
    _times_should_match(harness, actual_updated, expected_updated)


def test_get_history(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    harness.set_state(entity, 3)
    date1 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 2)
    date2 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 3)
    date3 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 0)
    date4 = harness.datetime
    _history_should_be(harness, history_manager, date1, 3, date2, 2, date3, 3, date4, 0)


def test_old_history_elements_are_removed(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    harness.set_state(entity, 20)
    harness.advance_time(timedelta(minutes=20))
    harness.set_state(entity, 13)
    date1 = harness.datetime
    harness.advance_time(timedelta(minutes=20))
    harness.set_state(entity, 1)
    date2 = harness.datetime
    harness.advance_time(timedelta(minutes=20))
    harness.set_state(entity, 6)
    date3 = harness.datetime
    harness.advance_time(timedelta(minutes=21))
    harness.set_state(entity, 54)
    date4 = harness.datetime
    _history_should_be(harness, history_manager, date1, 13, date2, 1, date3, 6, date4, 54)


def test_nothing_happens_for_a_long_time(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    harness.set_state(entity, 42)
    date1 = harness.datetime
    harness.advance_time(timedelta(hours=2))
    _history_should_be(harness, history_manager, date1, 42)
    harness.set_state(entity, 10)
    date2 = harness.datetime
    _history_should_be(harness, history_manager, date1, 42, date2, 10)
    harness.advance_time(timedelta(minutes=61))
    _history_should_be(harness, history_manager, date2, 10)


def test_history_enabler(harness: Harness, timing: Timing) -> None:
    harness.set_state(enabler_entity, "off")
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 5}
    base_interval = {"minutes": 1}
    harness.create_app(
        "enabler", "HistoryEnabler", "history_enabler",
        manager="history_manager",
        interval=interval,
        base_interval=base_interval,
        aggregator="integral",
        min=10, max=20,
    )
    harness.create_app("auto_switch", "AutoSwitch", "switch", target=enabler_entity)
    harness.create_app(
        "enabled_switch", "EnabledSwitch", "enabled_switch",
        enabler="history_enabler", targets=["switch"],
    )

    harness.schedule_call_at(timedelta(minutes=2), "set_state", entity, 3)
    harness.schedule_call_at(timedelta(minutes=20, seconds=30), "set_state", entity, 5)
    harness.schedule_call_at(timedelta(minutes=40), "set_state", entity, 1)
    timing.state_should_change_at(enabler_entity, "on", timedelta(minutes=6))
    timing.state_should_change_at(enabler_entity, "off", timedelta(minutes=23, seconds=30))
    timing.state_should_change_at(enabler_entity, "on", timedelta(minutes=42))
    timing.state_should_change_at(enabler_entity, "off", timedelta(minutes=44))


def test_aggregated_value(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 3}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="integral",
    )

    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 0
    harness.set_state(entity, 4)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 4
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 8
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 12
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 12
    harness.set_state(entity, 10)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 18
    harness.advance_time(timedelta(seconds=30))
    assert harness.get_state(aggregated_entity, type="int") == 18
    harness.set_state(entity, 3)
    assert harness.get_state(aggregated_entity, type="int") == 21
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 20
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 16
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 9
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 9


def test_aggregated_value_with_base_interval(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 3}
    base_interval = {"seconds": 10}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, base_interval=base_interval, aggregator="integral",
    )

    harness.advance_time(timedelta(seconds=20))
    harness.set_state(entity, 3)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 3
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 6
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 9
    harness.advance_time(timedelta(seconds=30))
    assert harness.get_state(aggregated_entity, type="int") == 18
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 36
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 54
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 54
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 54
    harness.set_state(entity, 5)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 56
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 58
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 60
    harness.advance_time(timedelta(seconds=30))
    assert harness.get_state(aggregated_entity, type="int") == 66
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 78
    harness.advance_time(timedelta(seconds=50))
    assert harness.get_state(aggregated_entity, type="int") == 88
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(aggregated_entity, type="int") == 90


def test_mean_value(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 3}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="mean",
    )

    harness.set_state(entity, 0)
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 20)
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 10)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 10


def test_mean_value_irregular_intervals(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 3}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="mean",
    )

    harness.set_state(entity, 20)
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 16)
    harness.advance_time(timedelta(seconds=30))
    harness.set_state(entity, 6)
    harness.advance_time(timedelta(seconds=30))
    harness.set_state(entity, 2)
    harness.advance_time(timedelta(minutes=1, seconds=30))
    harness.set_state(entity, 0)
    assert harness.get_state(aggregated_entity, type="int") == 8


def test_anglemean(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 4}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="anglemean",
    )

    harness.set_state(entity, 30)
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 60)
    harness.advance_time(timedelta(minutes=2))
    harness.set_state(entity, 300)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 22
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 330
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 300
    harness.set_state(entity, 180)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 270
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 240
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 210
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="int") == 180


def test_min_max_sum_values(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 5}
    harness.create_app(
        "history", "AggregatedValue", "sum_value",
        manager="history_manager", target=sum_entity,
        interval=interval, aggregator="sum",
    )
    harness.create_app(
        "history", "AggregatedValue", "min_value",
        manager="history_manager", target=min_entity,
        interval=interval, aggregator="min",
    )
    harness.create_app(
        "history", "AggregatedValue", "max_value",
        manager="history_manager", target=max_entity,
        interval=interval, aggregator="max",
    )

    harness.set_state(entity, 20)
    harness.advance_time(timedelta(minutes=5))
    assert harness.get_state(min_entity, type="int") == 20
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 20
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 6)
    assert harness.get_state(min_entity, type="int") == 6
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 26
    harness.advance_time(timedelta(seconds=30))
    harness.set_state(entity, 10)
    assert harness.get_state(min_entity, type="int") == 6
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 36
    harness.advance_time(timedelta(seconds=30))
    harness.set_state(entity, -2)
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 34
    harness.advance_time(timedelta(seconds=30))
    harness.set_state(entity, 12)
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 46
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 0)
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 46
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 46
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 20
    assert harness.get_state(sum_entity, type="int") == 46
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(min_entity, type="int") == -2
    assert harness.get_state(max_entity, type="int") == 12
    assert harness.get_state(sum_entity, type="int") == 20
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(min_entity, type="int") == 0
    assert harness.get_state(max_entity, type="int") == 12
    assert harness.get_state(sum_entity, type="int") == 12
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(min_entity, type="int") == 0
    assert harness.get_state(max_entity, type="int") == 0
    assert harness.get_state(sum_entity, type="int") == 0


def test_decaying_sum_value(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 1}
    harness.create_app(
        "history", "AggregatedValue", "aggregated_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="decay_sum", fraction=0.5,
    )

    harness.set_state(entity, 100)
    assert harness.get_state(aggregated_entity, type="float") == 100.0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="float") == 50.0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="float") == 25.0
    harness.set_state(entity, 1)
    assert harness.get_state(aggregated_entity, type="float") == 26.0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="float") == 13.0
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="float") == 6.5
    harness.advance_time(timedelta(minutes=6))
    assert harness.get_state(aggregated_entity, type="float") == 0.1015625


def test_binary_input(harness: Harness) -> None:
    history_manager = _initialize_history_manager(harness)
    interval = {"minutes": 5}
    harness.create_app(
        "history", "AggregatedValue", "sum_value",
        manager="history_manager", target=aggregated_entity,
        interval=interval, aggregator="mean",
    )

    harness.advance_time_to(timedelta(minutes=5))
    harness.turn_on(entity)
    harness.advance_time(timedelta(minutes=2))
    assert harness.get_state(aggregated_entity, type="percent") == 40
    harness.turn_off(entity)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 40
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 40
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 40
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 20
    harness.turn_on(entity)
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 20
    harness.advance_time(timedelta(seconds=30))
    harness.turn_off(entity)
    assert harness.get_state(aggregated_entity, type="percent") == 30
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 30
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 30
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 30
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 20
    harness.advance_time(timedelta(minutes=1))
    assert harness.get_state(aggregated_entity, type="percent") == 0


def test_change_tracker(harness: Harness) -> None:
    harness.set_state(entity, 0)
    change_tracker = harness.create_app(
        "history", "ChangeTracker", "change_tracker", entity=entity,
    )
    harness.advance_time_to(timedelta(minutes=1))
    harness.set_state(entity, "a")
    _check_date_updates(harness, change_tracker, timedelta(minutes=1), timedelta(minutes=1))
    harness.advance_time_to(timedelta(minutes=2))
    harness.set_state(entity, "b", foo="bar")
    _check_date_updates(harness, change_tracker, timedelta(minutes=2), timedelta(minutes=2))
    harness.advance_time_to(timedelta(minutes=3))
    harness.set_state(entity, "b", foo="baz")
    _check_date_updates(harness, change_tracker, timedelta(minutes=2), timedelta(minutes=3))
    harness.advance_time_to(timedelta(minutes=4))
    harness.set_state(entity, "b", foo="baz")
    _check_date_updates(harness, change_tracker, timedelta(minutes=2), timedelta(minutes=3))


def test_state_change_during_load_is_not_lost(harness: Harness) -> None:
    harness.set_state(entity, 5)
    time0 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    history = [[(time0, 5)]]
    history_manager = _initialize_history_manager_with_race(harness, history, 10)
    time1 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 7)
    time2 = harness.datetime
    _history_should_be(harness, history_manager, time0, 5, time1, 10, time2, 7)


def test_state_in_query_and_listener_is_not_duplicated(harness: Harness) -> None:
    harness.set_state(entity, 5)
    time0 = harness.datetime
    harness.advance_time(timedelta(minutes=1))
    time1 = harness.datetime
    history = [[(time0, 5), (time1, 10)]]
    history_manager = _initialize_history_manager_with_race(harness, history, 10)
    harness.advance_time(timedelta(minutes=1))
    harness.set_state(entity, 7)
    time2 = harness.datetime
    _history_should_be(harness, history_manager, time0, 5, time1, 10, time2, 7)