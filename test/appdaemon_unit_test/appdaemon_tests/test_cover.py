from __future__ import annotations
from datetime import time, timedelta
from typing import TYPE_CHECKING, cast

from appdaemon_unit_test.test_helpers.harness import Harness
from appdaemon_unit_test.test_helpers.timing import Timing

if TYPE_CHECKING:
    # Static type only: the harness loads the helper as top-level module
    # "test_cover" (distinct class object from this package-qualified
    # module, same file), so isinstance cannot hold at runtime. The
    # creation site casts instead, with a comment there.
    from appdaemon_unit_test.test_helpers.test_cover import TestCover

# Use 00:00:00.
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


_test_cover_helper_args = ("blocked", "settle_delay")


def _command_count(harness: Harness) -> int:
    return len(harness.service_calls(entity_id=cover_entity))


def _initialize(harness: Harness, **args: object) -> "TestCover":
    harness.set_state(input_entity, 0)
    harness.set_state(availability_entity, "on")
    harness.set_state(mode_switch, "auto")
    helper_args = {
        key: args.pop(key) for key in _test_cover_helper_args
        if key in args
    }
    test_cover = cast(
        "TestCover",
        harness.create_app(
            "test_cover", "TestCover", "test_cover",
            entity=cover_entity,
            position_entity=position_entity,
            available_entity=availability_entity,
            **helper_args,
        ),
    )
    harness.create_app(
        "cover", "CoverController", "cover",
        expr=f"v.{input_entity}",
        target=cover_entity,
        **args,
    )
    return test_cover


def _initialize_with_delay(
    harness: Harness, minutes: int, **args: object
) -> "TestCover":
    delay = {"minutes": minutes}
    return _initialize(harness, delay=delay, **args)


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

    _state_should_change_at(harness, timing, position_entity, 50, timedelta(minutes=2, seconds=10))
    _state_should_change_at(harness, timing, position_entity, 100, timedelta(minutes=5, seconds=10))
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


def test_flap_storm_single_reset(harness: Harness, timing: Timing) -> None:
    _initialize(harness, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=10), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=31), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=32), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=33), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=34), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=35), "set_state", availability_entity, "on")
    timing.state_should_not_change_until(position_entity, timedelta(seconds=40))
    assert harness.get_state(position_entity, type="int") == 0
    harness.step()
    assert harness.get_state(position_entity, type="int") == 75


def test_powerup_deferred_reset(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=35), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(seconds=100), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=104), "set_state", cover_entity, "unknown")
    timing.state_should_not_change_until(position_entity, timedelta(seconds=100))
    assert harness.get_state(position_entity, type="int") == 0
    _state_should_change_at(harness, timing, position_entity, 75, timedelta(seconds=110))


def test_unknown_state_deferred_reset(harness: Harness) -> None:
    _initialize(harness, mode_switch=mode_switch, settle_delay=25)
    harness.advance_time(timedelta(seconds=30))
    assert harness.get_state(position_entity, type="int") == 0
    assert harness.get_state(mode_switch) == "stable"
    harness.set_state(input_entity, 75)
    assert harness.get_state(mode_switch) == "auto"
    assert _command_count(harness) == 3
    harness.schedule_call_at(timedelta(seconds=56), "set_state", cover_entity, "unknown")
    harness.advance_time(timedelta(seconds=40))
    assert harness.get_state(position_entity, type="int") == 75
    assert harness.get_state(mode_switch) == "stable"
    assert _command_count(harness) == 3


def test_blocked_cover_goes_stable(harness: Harness) -> None:
    _initialize(harness, blocked=True, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=10), "set_state", input_entity, 50)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    final_count = _command_count(harness)
    assert harness.get_state(mode_switch) == "stable"
    harness.advance_time(timedelta(seconds=60))
    harness.clear_errors()
    assert _command_count(harness) == final_count
    assert harness.get_state(cover_entity) == "open"


def test_blocked_cover_recovers_on_new_target(harness: Harness) -> None:
    _initialize(harness, blocked=True, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=10), "set_state", input_entity, 50)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    assert harness.get_state(mode_switch) == "stable"
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 75)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    assert harness.get_state(mode_switch) == "stable"
    final_count = _command_count(harness)
    assert final_count >= 2
    harness.advance_time(timedelta(seconds=60))
    harness.clear_errors()
    assert _command_count(harness) == final_count


def test_arrived_resets_counter(harness: Harness) -> None:
    cover = _initialize(harness, mode_switch=mode_switch, settle_delay=2)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "stable"
    harness.call_on_app(cover, "set_blocked", True)
    harness.set_state(input_entity, 25)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "auto"
    assert harness.get_state(position_entity, type="int") == 12
    harness.call_on_app(cover, "set_blocked", False)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(position_entity, type="int") == 25
    assert harness.get_state(mode_switch) == "stable"
    harness.call_on_app(cover, "set_blocked", True)
    harness.call_on_app(
        harness.test_app, "call_service", "cover/set_cover_position",
        entity_id=cover_entity, position=80,
    )
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(position_entity, type="int") == 52
    harness.schedule_call_at(
        timedelta(seconds=45), "select_option", mode_switch, "auto",
    )
    harness.advance_time(timedelta(seconds=10))
    harness.clear_errors()
    harness.advance_time(timedelta(seconds=30))
    harness.clear_errors()
    assert harness.get_state(position_entity, type="int") == 28
    assert harness.get_state(mode_switch) == "stable"
    assert _command_count(harness) == 8


def test_expression_change_mid_sequence_resets_counter(harness: Harness) -> None:
    cover = _initialize(harness, mode_switch=mode_switch, settle_delay=2)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "stable"
    harness.call_on_app(cover, "set_blocked", True)
    harness.set_state(input_entity, 25)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "auto"
    assert harness.get_state(position_entity, type="int") == 12
    harness.schedule_call_at(timedelta(seconds=21), "set_state", input_entity, 75)
    harness.advance_time(timedelta(seconds=10))
    harness.clear_errors()
    assert harness.get_state(mode_switch) == "auto"
    harness.advance_time(timedelta(seconds=30))
    harness.clear_errors()
    assert harness.get_state(position_entity, type="int") == 67
    assert harness.get_state(mode_switch) == "stable"
    assert _command_count(harness) == 8


def test_reset_delay_arg(harness: Harness) -> None:
    _initialize(harness, reset_delay={"seconds": 25})
    harness.set_state(input_entity, 50)
    assert _command_count(harness) == 2
    harness.schedule_call_at(timedelta(seconds=10), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=20), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "on")
    harness.advance_time_to(timedelta(seconds=50))
    assert _command_count(harness) == 2
    harness.advance_time(timedelta(seconds=10))
    assert _command_count(harness) == 3
    assert harness.get_state(position_entity, type="int") == 75


def test_direct_command_supersedes_pending_reset(harness: Harness) -> None:
    _initialize(
        harness, mode_switch=mode_switch, settle_delay=40,
        reset_delay={"seconds": 5},
    )
    harness.advance_time(timedelta(seconds=40))
    assert harness.get_state(mode_switch) == "stable"
    assert _command_count(harness) == 1
    harness.set_state(availability_entity, "off")
    harness.set_state(input_entity, 50)
    assert _command_count(harness) == 1
    harness.set_state(availability_entity, "on")
    assert _command_count(harness) == 1
    harness.set_state(input_entity, 75)
    assert _command_count(harness) == 2
    harness.advance_time(timedelta(seconds=60))
    assert harness.get_state(position_entity, type="int") == 75
    assert harness.get_state(mode_switch) == "stable"
    assert _command_count(harness) == 2


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
