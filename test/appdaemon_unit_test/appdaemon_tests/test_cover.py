from __future__ import annotations
from datetime import time, timedelta
from typing import TYPE_CHECKING, cast

from appdaemon_unit_test.test_helpers.harness import Harness
from appdaemon_unit_test.test_helpers.timing import Timing

if TYPE_CHECKING:
    # The harness loads the helper as top-level module "test_cover"; it
    # is only importable at runtime, so import it dynamically in
    # _get_test_cover and narrow with assert isinstance there.
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


def _get_test_cover(harness: Harness) -> "TestCover":
    # The harness loads the helper as top-level module "test_cover" and
    # the CoverController app registers a TestCover instance under the
    # same app name; narrow both to the runtime type.
    import importlib
    module = importlib.import_module("test_cover")
    test_cover = harness.get_app("test_cover")
    assert test_cover is not None
    assert isinstance(test_cover, module.TestCover)  # type: ignore[attr-defined]
    narrowed = cast("TestCover", test_cover)
    return narrowed


_test_cover_helper_args = ("blocked", "settle_delay")


def _initialize(harness: Harness, **args: object) -> None:
    harness.set_state(input_entity, 0)
    harness.set_state(availability_entity, "on")
    harness.set_state(mode_switch, "auto")
    helper_args = {
        key: args.pop(key) for key in _test_cover_helper_args
        if key in args
    }
    harness.create_app(
        "test_cover", "TestCover", "test_cover",
        entity=cover_entity,
        position_entity=position_entity,
        available_entity=availability_entity,
        **helper_args,
    )
    harness.create_app(
        "cover", "CoverController", "cover",
        expr=f"v.{input_entity}",
        target=cover_entity,
        **args,
    )


def _initialize_with_delay(harness: Harness, minutes: int, **args: object) -> None:
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

    # The reset after becoming available is deferred by the reset
    # delay (5s), so the command lands in the harness step after the
    # availability flips back on (2:05 and 5:05 execute in the steps
    # ending 2:10 and 5:10). The 6:40 availability flip still defers a
    # reset, but by then the cover had settled: the AUTO-mode guard in
    # the reset callback drops it, and the position only changes when
    # the 7:00 expression delay expires.
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
    # @0: init: cmd 0 → position 0 closed → arrived → stable.
    harness.schedule_call_at(timedelta(seconds=10), "set_state", availability_entity, "off")
    # New value delivered while unavailable: expected becomes 75, stable
    # mode flips back to auto on the change.
    harness.schedule_call_at(timedelta(seconds=20), "set_state", input_entity, 75)
    # Storm: raw availability toggles inside one simulation step. The
    # TestCover listener callbacks all run after the raw toggles and
    # read the final state, so the controller observes a single
    # became-available edge and defers one reset — no position command
    # during the storm. (The per-flap reschedule path is only a reset
    # timing delta and is not pinned by this test.)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=31), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=32), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=33), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=34), "set_state", availability_entity, "off")
    harness.schedule_call_at(timedelta(seconds=35), "set_state", availability_entity, "on")
    # Storm settled: still 0 at 40s; the deferred reset fires and
    # re-delivers 75 in the step reaching 50 — exactly once. Pre-fix the
    # reset commanded on each became-available edge and the position
    # would have changed already.
    timing.state_should_not_change_until(position_entity, timedelta(seconds=40))
    assert harness.get_state(position_entity, type="int") == 0
    harness.step()
    assert harness.get_state(position_entity, type="int") == 75


def test_powerup_deferred_reset(harness: Harness, timing: Timing) -> None:
    _initialize_with_delay(harness, 1, mode_switch=mode_switch)
    # @0: init: cmd 0 → position 0 closed → arrived → stable.
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "off")
    # New value delivered while unavailable: expected becomes 75 and the
    # stable mode flips back to auto, still without commanding.
    harness.schedule_call_at(timedelta(seconds=35), "set_state", input_entity, 75)
    # Cover reports "unknown" at power-up 4s after the availability
    # flip; the unknown report's callback is processed after the
    # deferred reset already fired, so it hits no scheduling branch —
    # this test pins the availability-edge deferral. With the 5s reset
    # delay the timer (scheduled 105s) fires in the step reaching 110s
    # — one full step after the availability flip. Pre-fix the reset
    # commanded synchronously on the became-available edge at 100s.
    # (The unknown-branch deferral is covered by
    # test_unknown_state_deferred_reset.)
    harness.schedule_call_at(timedelta(seconds=100), "set_state", availability_entity, "on")
    harness.schedule_call_at(timedelta(seconds=104), "set_state", cover_entity, "unknown")
    timing.state_should_not_change_until(position_entity, timedelta(seconds=100))
    assert harness.get_state(position_entity, type="int") == 0
    _state_should_change_at(harness, timing, position_entity, 75, timedelta(seconds=110))


def test_unknown_state_deferred_reset(harness: Harness) -> None:
    # Pins the "State unknown, need to reset" branch: the reset must be
    # DEFERRED by the reset delay, not commanded synchronously. The
    # branch only fires in AUTO mode with an expected value, so the
    # "unknown" report must land while a commanded move is in flight.
    # settle_delay=25 keeps the settle far past the report.
    _initialize(harness, mode_switch=mode_switch, settle_delay=25)
    cover = _get_test_cover(harness)
    # @0: init commands 0 (count 1); mode settles STABLE after the
    # settle completes in the step reaching 30s. Advance there.
    harness.advance_time(timedelta(seconds=30))
    assert harness.get_state(position_entity, type="int") == 0
    assert harness.get_state(mode_switch) == "stable"
    # New value 75: STABLE→AUTO flip, commands 75 (count 2), state
    # "opening", settle armed for +25s (55s). Mode is AUTO while
    # moving. NOTE: the mode-select callback ALSO re-commands once
    # more ("Back to auto, resetting value") — a known duplicate of
    # the existing STABLE→AUTO flip path (count 3), not this test's
    # subject.
    harness.set_state(input_entity, 75)
    assert harness.get_state(mode_switch) == "auto"
    assert harness.call_on_app(cover, "get_command_count") == 3
    # Unknown report at 56s — AFTER the settle task (55s) but before
    # its listener callback: within the step reaching 60s the settle
    # task completes the move to 75 first, then the report sets the
    # entity to "unknown". The listener callbacks pop LIFO, so the
    # unknown callback runs FIRST (mode still AUTO, move not yet
    # confirmed): the branch must DEFER the reset (armed for 61s).
    # The settle callback then runs: "Arrived at target" → STABLE.
    # At the step reaching 70s the deferred reset fires and is
    # dropped by the AUTO guard. Still 3 commands.
    # Pre-fix (immediate _reset_value() in the unknown branch) a 4th
    # command fires in the 60s step and re-arms the settle past this
    # window — the count assert fails.
    harness.schedule_call_at(timedelta(seconds=56), "set_state", cover_entity, "unknown")
    harness.advance_time(timedelta(seconds=40))
    assert harness.get_state(position_entity, type="int") == 75
    assert harness.get_state(mode_switch) == "stable"
    assert harness.call_on_app(cover, "get_command_count") == 3


def test_blocked_cover_goes_stable(harness: Harness) -> None:
    _initialize(harness, blocked=True, mode_switch=mode_switch)
    # The stuck cover stops halfway on every command. Deliver the target
    # through the scheduler and run the chain with advance_time so the
    # cap's error log does not abort the advance (the harness rejects
    # error logs from direct calls); clear it afterwards.
    harness.schedule_call_at(timedelta(seconds=10), "set_state", input_entity, 50)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    cover = _get_test_cover(harness)
    final_count = harness.call_on_app(cover, "get_command_count")
    assert harness.get_state(mode_switch) == "stable"
    harness.advance_time(timedelta(seconds=60))
    harness.clear_errors()
    assert harness.call_on_app(cover, "get_command_count") == final_count
    assert harness.get_state(cover_entity) == "open"


def test_blocked_cover_recovers_on_new_target(harness: Harness) -> None:
    _initialize(harness, blocked=True, mode_switch=mode_switch)
    harness.schedule_call_at(timedelta(seconds=10), "set_state", input_entity, 50)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    cover = _get_test_cover(harness)
    assert harness.get_state(mode_switch) == "stable"
    # A new target value flips the mode back to auto and commands once
    # more; the stuck cover caps out again after a fresh attempt budget.
    harness.schedule_call_at(timedelta(seconds=30), "set_state", input_entity, 75)
    harness.advance_time(timedelta(seconds=20))
    harness.clear_errors()
    assert harness.get_state(mode_switch) == "stable"
    final_count = harness.call_on_app(cover, "get_command_count")
    assert final_count >= 2
    harness.advance_time(timedelta(seconds=60))
    harness.clear_errors()
    assert harness.call_on_app(cover, "get_command_count") == final_count


def test_arrived_resets_counter(harness: Harness) -> None:
    # settle_delay=2 lets each commanded move settle two simulated
    # seconds after the command, so the stuck-cover retry chain pauses
    # between steps instead of playing out atomically. That pause is
    # what makes the arrival reset observable: the counter can sit at a
    # nonzero value across a step boundary and still be nonzero at the
    # clean arrival.
    _initialize(harness, mode_switch=mode_switch, settle_delay=2)
    cover = _get_test_cover(harness)
    controller = harness.get_app("cover")
    assert controller is not None
    # @0: init commands 0; the settle completes in the next step and
    # the cover arrives cleanly at 0.
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "stable"
    # Block and command 25: the cover stops short once (halfway, at 12)
    # and the chain pauses on the pending settle — counter=1, well
    # under the cap, no give-up (which would zero the counter).
    harness.call_on_app(cover, "set_blocked", True)
    harness.set_state(input_entity, 25)
    harness.advance_time(timedelta(seconds=10))
    assert harness.call_on_app(controller, "get_force_reset_count") == 1
    assert harness.get_state(position_entity, type="int") == 12
    # Unblock: the pending settle completes the in-flight retry and the
    # cover arrives cleanly at 25. No give-up or value change runs in
    # between, so the counter 1→0 transition happens on the arrival
    # line only.
    harness.call_on_app(cover, "set_blocked", False)
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(position_entity, type="int") == 25
    assert harness.get_state(mode_switch) == "stable"
    assert harness.call_on_app(controller, "get_force_reset_count") == 0
    # Re-block and reposition the cover with a manual service call
    # (ignored by the controller in stable mode: it only clears its
    # target). Then flip the mode back to auto: the re-command of the
    # same 25 target must get the FULL 3-attempt budget again. A
    # retained counter=1 would trip the cap after only 2 short stops
    # (one fewer re-command, and a stop-short position one link earlier
    # in the halfway chain).
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
    # Step at 50s: the auto flip re-commands 25 from position 52.
    harness.advance_time(timedelta(seconds=10))
    harness.clear_errors()
    # Steps at 60s/70s/80s: short stops at 38/31/28 (the halfway
    # chain); the cap trips at the third stop and the give-up error is
    # logged. With a retained counter=1 the cap would already trip at
    # the stop at 31 (70s), leaving one command fewer and the position
    # at 31.
    harness.advance_time(timedelta(seconds=30))
    harness.clear_errors()
    assert harness.get_state(position_entity, type="int") == 28
    assert harness.get_state(mode_switch) == "stable"
    # Command count: init 0, arrival chain 25, M1-leftover 25, retry
    # after 12, manual 80, flip re-command, retries after 38 and 31.
    assert harness.call_on_app(cover, "get_command_count") == 8


def test_expression_change_mid_sequence_resets_counter(harness: Harness) -> None:
    # settle_delay=2 makes each commanded move settle two simulated
    # seconds after the command, so the stuck-cover retry chain pauses
    # between steps. A value change can then land mid-sequence,
    # between two consecutive short stops, with a NONZERO counter and
    # no give-up in between — the only situation in which the
    # expression-change reset is observable.
    _initialize(harness, mode_switch=mode_switch, settle_delay=2)
    cover = _get_test_cover(harness)
    controller = harness.get_app("cover")
    assert controller is not None
    # @0: init commands 0; the cover arrives cleanly in the next step.
    harness.advance_time(timedelta(seconds=10))
    assert harness.get_state(mode_switch) == "stable"
    # Block and command 25: the cover stops short once (at 12,
    # counter=1) and the chain pauses on the pending settle.
    harness.call_on_app(cover, "set_blocked", True)
    harness.set_state(input_entity, 25)
    harness.advance_time(timedelta(seconds=10))
    assert harness.call_on_app(controller, "get_force_reset_count") == 1
    # New value 75 scheduled at 21s: it lands inside the step reaching
    # 30s, between the two pending chain events. The settle task (22s)
    # still runs first — a second short stop at 18 (counter=2, no cap,
    # no give-up) — and then the value change fires mid-sequence with
    # the counter NONZERO. The change must zero the counter and
    # re-target the cover to 75; the new command cancels the pending 25
    # settle, so the 75 sequence starts from position 18.
    harness.schedule_call_at(timedelta(seconds=21), "set_state", input_entity, 75)
    harness.advance_time(timedelta(seconds=10))
    harness.clear_errors()
    assert harness.get_state(mode_switch) == "auto"
    # Steps at 40s/50s/60s: short stops at 46/60/67; the cap trips at
    # the third stop and the give-up error is logged. A retained
    # counter=2 would trip the cap at the FIRST 75 stop (at 46, 40s),
    # leaving two commands fewer and the position at 46.
    harness.advance_time(timedelta(seconds=30))
    harness.clear_errors()
    assert harness.get_state(position_entity, type="int") == 67
    assert harness.get_state(mode_switch) == "stable"
    # Command count: init 0, arrival chain 25, M1-leftover 25, retries
    # after 12 and 18, mid-sequence 75, retries after 46 and 60.
    assert harness.call_on_app(cover, "get_command_count") == 8


def test_reset_delay_arg(harness: Harness) -> None:
    _initialize(harness, reset_delay={"seconds": 25})
    harness.set_state(input_entity, 50)
    cover = _get_test_cover(harness)
    assert harness.call_on_app(cover, "get_command_count") == 2
    harness.schedule_call_at(timedelta(seconds=10), "set_state", availability_entity, "off")
    # New value delivered while unavailable; stable mode flips back to
    # auto so the deferred reset will be able to command it.
    harness.schedule_call_at(timedelta(seconds=20), "set_state", input_entity, 75)
    harness.schedule_call_at(timedelta(seconds=30), "set_state", availability_entity, "on")
    # Became available at 30s: reset scheduled at 55s (custom 25s delay).
    # Nothing may fire before 55s.
    harness.advance_time_to(timedelta(seconds=50))
    assert harness.call_on_app(cover, "get_command_count") == 2
    harness.advance_time(timedelta(seconds=10))
    # Reset fires in the step that runs at 60s (scheduled 55s).
    assert harness.call_on_app(cover, "get_command_count") == 3
    assert harness.get_state(position_entity, type="int") == 75


def test_direct_command_supersedes_pending_reset(harness: Harness) -> None:
    # Pins the supersede-cancel: a pending deferred reset (from a
    # became-available edge) must be cancelled when a direct command
    # executes — the value change re-commands immediately and the
    # pending reset must not issue a duplicate later.
    # Pre-fix (no cancel in _reset_value/_set_value) the pending reset
    # survives and fires while the re-commanded move is still in
    # flight (settle_delay=40 keeps it moving past the fire time):
    # a duplicate command and re-armed settle follow — count assert
    # fails.
    _initialize(
        harness, mode_switch=mode_switch, settle_delay=40,
        reset_delay={"seconds": 5},
    )
    cover = _get_test_cover(harness)
    # @0: init commands 0 (count 1); settle at 40s; step at 40s:
    # arrival at 0 → STABLE.
    harness.advance_time(timedelta(seconds=40))
    assert harness.get_state(mode_switch) == "stable"
    assert harness.call_on_app(cover, "get_command_count") == 1
    # Go unavailable, then change the value to 50 (delivered while
    # unavailable: expected_value updates, STABLE→AUTO, no command —
    # cover unavailable).
    harness.set_state(availability_entity, "off")
    harness.set_state(input_entity, 50)
    assert harness.call_on_app(cover, "get_command_count") == 1
    # Became available: a reset is deferred, armed for +5s.
    harness.set_state(availability_entity, "on")
    assert harness.call_on_app(cover, "get_command_count") == 1
    # Direct command: a NEW value 75 arrives while available —
    # on_expression_change runs _set_value immediately (count 2) and
    # must CANCEL the pending reset. The cover starts moving toward
    # 75, settle armed for +40s — the move is still in flight well
    # past the would-be reset fire time.
    harness.set_state(input_entity, 75)
    assert harness.call_on_app(cover, "get_command_count") == 2
    # Advance past the would-be fire time: with the supersede-cancel
    # the reset is gone — the cover settles and arrives at 75, exactly
    # 2 commands. Pre-fix the reset fires while the move is in flight
    # (AUTO mode, available): a duplicate command (count 3) whose
    # settle lands past this window.
    harness.advance_time(timedelta(seconds=60))
    assert harness.get_state(position_entity, type="int") == 75
    assert harness.get_state(mode_switch) == "stable"
    assert harness.call_on_app(cover, "get_command_count") == 2


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