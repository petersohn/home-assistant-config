from __future__ import annotations
from datetime import time, timedelta
from typing import Any

from conftest import Harness
from unit_helpers.timing import Timing

# Use 00:00:00 (matching the original Robot harness).
_default_start_time = time(0, 0, 0)

input_entity = "sensor.target_position"
cover_entity = "cover.test_cover"
position_entity = "sensor.cover_position"
availability_entity = "sensor.cover_available"
mode_switch = "input_select.test_cover_mode"


def _state_should_change_at(
    harness: Harness, timing: Timing, entity: str, value: int, target_time: timedelta,
) -> None:
    target = harness.date_from_time(target_time, future=True)
    deadline = target - harness.interval
    assert harness.get_state(entity, type="int") != value
    timing.state_should_not_change_until(entity, deadline)
    assert harness.get_state(entity, type="int") != value
    harness.step()
    assert harness.get_state(entity, type="int") == value


def _initialize(harness: Harness, **args: Any) -> None:
    harness.set_state(input_entity, 0)
    harness.set_state(availability_entity, "on")
    harness.set_state(mode_switch, "auto")
    harness.create_app(
        "test_cover", "TestCover", "test_cover",
        entity=cover_entity,
        position_entity=position_entity,
        available_entity=availability_entity,
    )
    harness.create_app(
        "cover", "CoverController", "cover",
        expr=f"v.{input_entity}",
        target=cover_entity,
        **args,
    )


def _initialize_with_delay(harness: Harness, minutes: int, **args: Any) -> None:
    delay = {"minutes": minutes}
    _initialize(harness, delay=delay, **args)


def test_basic(harness: Harness) -> None:
    _initialize(harness)
    # NOTE: rows share state — invalid inputs leave position unchanged from
    # the previous valid value, so order matters.
    rows = [
        ("open", 100),
        ("closed", 0),
        ("Open", 100),
        ("Closed", 0),
        ("OPEN", 100),
        ("CLOSED", 0),
        (10, 10),
        (55, 55),
        (100, 100),
        (0, 0),
        (72, 72),
        (101, 72),
        (-1, 72),
        ("foo", 72),
        (11, 11),
    ]
    for input_value, expected in rows:
        harness.set_state(input_entity, input_value)
        assert harness.get_state(position_entity, type="int") == expected


def _test_delay(harness: Harness, timing: Timing) -> None:
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=2), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(minutes=2, seconds=30), "set_state", input_entity, "closed")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=1, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 0, timedelta(minutes=3, seconds=30))


def test_delay(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1)
    _test_delay(harness, timing)


def test_delay_with_mode_switch(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    _test_delay(harness, timing)


def _test_availability(harness: Harness, timing: Timing) -> None:
    harness.schedule_call_at(timedelta(seconds=10), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=2), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(minutes=3), "set_state", input_entity, "open")
    harness.schedule_call_at(timedelta(minutes=3, seconds=10), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(minutes=6), "set_state", input_entity, "closed")
    harness.schedule_call_at(timedelta(minutes=6, seconds=30), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(minutes=6, seconds=40), "set_state", availability_entity, "on")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=2))
    _state_should_change_at(harness, timing, position_entity, 100, timedelta(minutes=5))
    _state_should_change_at(harness, timing, position_entity, 0, timedelta(minutes=7))


def test_availability(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1)
    _test_availability(harness, timing)


def test_availability_with_mode_switch(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    _test_availability(harness, timing)


def _test_temporary_manual_mode(harness: Harness, timing: Timing) -> None:
    harness.schedule_call_at(timedelta(minutes=1), "set_state", input_entity, 50)
    harness.schedule_call_at(
        timedelta(minutes=3), "call_service",
        "cover/set_cover_position", entity_id=cover_entity, position=80,
    )
    harness.schedule_call_at(timedelta(minutes=4), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(minutes=7), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=8, seconds=30), "set_state", input_entity, "closed")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=2))
    _state_should_change_at(harness, timing, position_entity, 80, timedelta(minutes=3))
    _state_should_change_at(harness, timing, position_entity, 0, timedelta(minutes=9, seconds=30))


def test_temporary_manual_mode(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1)
    _test_temporary_manual_mode(harness, timing)


def test_temporary_manual_mode_with_mode_switch(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    _test_temporary_manual_mode(harness, timing)


def test_manual_mode_from_stable_to_auto(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(
        timedelta(minutes=2), "call_service",
        "cover/set_cover_position", entity_id=cover_entity, position=10,
    )
    harness.schedule_call_at(timedelta(minutes=3), "select_option", mode_switch, "auto")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=1, seconds=30))
    assert harness.get_state(mode_switch) == "stable"
    _state_should_change_at(harness, timing, position_entity, 10, timedelta(minutes=2))
    assert harness.get_state(mode_switch) == "stable"
    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=3))
    assert harness.get_state(mode_switch) == "stable"


def test_manual_mode_availability_change(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=2), "select_option", mode_switch, "manual")
    harness.schedule_call_at(
        timedelta(minutes=2, seconds=30), "call_service",
        "cover/set_cover_position", entity_id=cover_entity, position=10,
    )
    harness.schedule_call_at(timedelta(minutes=4), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(minutes=5), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(minutes=6), "select_option", mode_switch, "auto")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=1, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 10, timedelta(minutes=2, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=6))


def test_manual_mode_state_change_auto(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=2), "select_option", mode_switch, "manual")
    harness.schedule_call_at(
        timedelta(minutes=2, seconds=30), "call_service",
        "cover/set_cover_position", entity_id=cover_entity, position=10,
    )
    harness.schedule_call_at(timedelta(minutes=4), "set_state", input_entity, "open")
    harness.schedule_call_at(timedelta(minutes=6), "select_option", mode_switch, "auto")
    harness.schedule_call_at(timedelta(minutes=6, seconds=10), "select_option", mode_switch, "manual")
    harness.schedule_call_at(
        timedelta(minutes=6, seconds=30), "call_service",
        "cover/close_cover", entity_id=cover_entity,
    )
    harness.schedule_call_at(timedelta(minutes=7), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(minutes=7, seconds=30), "select_option", mode_switch, "auto")

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=1, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 10, timedelta(minutes=2, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 100, timedelta(minutes=6))
    _state_should_change_at(harness, timing, position_entity, 0, timedelta(minutes=6, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 100, timedelta(minutes=7, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 75, timedelta(minutes=8))


def test_manual_mode_state_change_stable(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 50)
    harness.schedule_call_at(timedelta(minutes=2), "select_option", mode_switch, "manual")
    harness.schedule_call_at(
        timedelta(minutes=2, seconds=30), "call_service",
        "cover/set_cover_position", entity_id=cover_entity, position=10,
    )
    harness.schedule_call_at(timedelta(minutes=4), "set_state", input_entity, "open")
    harness.schedule_call_at(timedelta(minutes=6), "select_option", mode_switch, "stable")
    harness.schedule_call_at(
        timedelta(minutes=6, seconds=30), "call_service",
        "cover/close_cover", entity_id=cover_entity,
    )
    harness.schedule_call_at(timedelta(minutes=7), "set_state", input_entity, 75)

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=1, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 10, timedelta(minutes=2, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 0, timedelta(minutes=6, seconds=30))
    _state_should_change_at(harness, timing, position_entity, 75, timedelta(minutes=8))