from __future__ import annotations

from datetime import datetime, timedelta, time
import pytest
from appdaemon_unit_test.test_helpers.harness import Harness
from appdaemon_unit_test.test_helpers.hass import ServiceCallRecord
from appdaemon_unit_test.test_helpers.timing import Timing


@pytest.fixture
def setup_harness(harness: Harness) -> Harness:
    """Default harness with test_sensor set."""
    harness.set_state("sensor.test_sensor", "sensor state")
    return harness


def test_start_time(setup_harness: Harness) -> None:
    assert setup_harness.datetime.time() == time(1, 0, 0)


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0)}], indirect=True)
def test_different_start_time(harness: Harness) -> None:
    assert harness.datetime.time() == time(21, 30, 0)


def test_set_state(setup_harness: Harness) -> None:
    setup_harness.set_state("sensor.test_sensor", "new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_set_attribute(setup_harness: Harness) -> None:
    setup_harness.set_state("sensor.test_sensor", "foobar", a="attr1", b="attr2")
    assert setup_harness.get_state("sensor.test_sensor") == "foobar"
    assert setup_harness.get_state("sensor.test_sensor", attribute="a") == "attr1"
    assert setup_harness.get_state("sensor.test_sensor", attribute="b") == "attr2"


def test_step(setup_harness: Harness) -> None:
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 10)
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_advance_time(setup_harness: Harness) -> None:
    setup_harness.advance_time(timedelta(minutes=2))
    assert setup_harness.datetime.time() == time(1, 2, 0)
    setup_harness.advance_time(timedelta(minutes=5))
    assert setup_harness.datetime.time() == time(1, 7, 0)


def test_advance_time_to(setup_harness: Harness) -> None:
    setup_harness.advance_time_to(time(1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)
    setup_harness.advance_time_to(time(1, 10, 0))
    assert setup_harness.datetime.time() == time(1, 10, 0)


def test_advance_time_to_datetime(setup_harness: Harness) -> None:
    setup_harness.advance_time_to_datetime(datetime(2018, 1, 1, 1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)


def test_schedule_state_change_in_some_time(setup_harness: Harness) -> None:
    setup_harness.schedule_call_in(timedelta(minutes=2), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time(timedelta(minutes=1, seconds=50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_some_time(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at(time(1, 10, 0), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_exact_time(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at_datetime(
        datetime(2018, 1, 1, 1, 10, 0),
        "set_state", "sensor.test_sensor", "new sensor state",
    )
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_wait_for_state_change(setup_harness: Harness) -> None:
    change_time = time(1, 2, 10)
    setup_harness.schedule_call_at(change_time, "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == change_time


def test_wait_for_later_state_change(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at(time(1, 1, 10), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.schedule_call_at(time(1, 1, 30), "set_state", "sensor.test_sensor2", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor2")
    assert setup_harness.get_state("sensor.test_sensor2") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 30)


def test_wait_for_state_change_with_timeout(setup_harness: Harness) -> None:
    setup_harness.schedule_call_in(timedelta(minutes=1, seconds=50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_deadline(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at(time(1, 1, 50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 1, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 2, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_new_state(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", new="new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 40)


def test_wait_for_state_change_with_old_state(setup_harness: Harness) -> None:
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", old="intermediate sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_state_should_not_change_for_some_time(setup_harness: Harness, timing: Timing) -> None:
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_for("sensor.test_sensor", timedelta(seconds=20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_not_change_until_some_time(setup_harness: Harness, timing: Timing) -> None:
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_until("sensor.test_sensor", datetime(2018, 1, 1, 1, 0, 20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_change_in_some_time(setup_harness: Harness, timing: Timing) -> None:
    duration = timedelta(seconds=30)
    setup_harness.schedule_call_in(duration, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_in("sensor.test_sensor", "new sensor state", duration)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 30)


def test_state_should_change_at_some_time(setup_harness: Harness, timing: Timing) -> None:
    target = time(1, 1, 0)
    setup_harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == target


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0), "interval": timedelta(minutes=10)}], indirect=True)
def test_state_should_change_next_day(harness: Harness) -> None:
    harness.set_state("sensor.test_sensor", "sensor state")
    target = time(1, 0, 0)
    harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    from appdaemon_unit_test.test_helpers.timing import Timing
    timing = Timing(harness)
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert harness.get_state("sensor.test_sensor") == "new sensor state"
    assert harness.datetime == datetime(2018, 1, 2, 1, 0, 0)


def test_converted_state_expectations(setup_harness: Harness) -> None:
    setup_harness.set_state("sensor.test_sensor", "12")
    assert setup_harness.get_state("sensor.test_sensor", type="int") == 12


def test_service_call_log_records_calls(setup_harness: Harness) -> None:
    setup_harness.test_app.register_service(
        "light/turn_on", "light.test_light", lambda _args: None
    )
    setup_harness.call_on_app(
        setup_harness.test_app, "call_service", "light/turn_on",
        "light.test_light", brightness="5",
    )
    assert setup_harness.service_calls() == [
        ServiceCallRecord(
            app="test_app",
            service="light/turn_on",
            entity_id="light.test_light",
            kwargs={"brightness": "5"},
        )
    ]


def test_service_calls_filtering(setup_harness: Harness) -> None:
    setup_harness.test_app.register_service(
        "light/turn_on", "light.a", lambda _args: None
    )
    setup_harness.test_app.register_service(
        "switch/turn_off", "switch.b", lambda _args: None
    )
    light_on_a = ServiceCallRecord(
        app="test_app", service="light/turn_on", entity_id="light.a",
        kwargs={},
    )
    switch_off_b = ServiceCallRecord(
        app="test_app", service="switch/turn_off", entity_id="switch.b",
        kwargs={},
    )
    setup_harness.call_on_app(
        setup_harness.test_app, "call_service", "light/turn_on", "light.a"
    )
    setup_harness.call_on_app(
        setup_harness.test_app, "call_service", "switch/turn_off", "switch.b"
    )
    setup_harness.call_on_app(
        setup_harness.test_app, "call_service", "light/turn_on", "light.a"
    )
    assert setup_harness.service_calls() == [
        light_on_a, switch_off_b, light_on_a,
    ]
    assert setup_harness.service_calls(service="light/turn_on") == [
        light_on_a, light_on_a,
    ]
    assert setup_harness.service_calls(entity_id="switch.b") == [switch_off_b]
    assert setup_harness.service_calls(
        service="light/turn_on", entity_id="switch.b"
    ) == []


def test_turn_on_without_handler_reflects_state(setup_harness: Harness) -> None:
    setup_harness.call_on_app(
        setup_harness.test_app, "turn_on", "switch.test_switch"
    )
    assert setup_harness.get_state("switch.test_switch") == "on"
    assert setup_harness.service_calls(entity_id="switch.test_switch") == [
        ServiceCallRecord(
            app="test_app",
            service="homeassistant/turn_on",
            entity_id="switch.test_switch",
            kwargs={},
        )
    ]


def test_turn_off_without_handler_reflects_state(setup_harness: Harness) -> None:
    setup_harness.set_state("switch.test_switch", "on")
    setup_harness.call_on_app(
        setup_harness.test_app, "turn_off", "switch.test_switch"
    )
    assert setup_harness.get_state("switch.test_switch") == "off"
    assert setup_harness.service_calls(entity_id="switch.test_switch") == [
        ServiceCallRecord(
            app="test_app",
            service="homeassistant/turn_off",
            entity_id="switch.test_switch",
            kwargs={},
        )
    ]


def test_turn_on_with_handler_routes_and_does_not_reflect(
    setup_harness: Harness,
) -> None:
    received: list[dict[str, object]] = []
    setup_harness.test_app.register_service(
        "homeassistant/turn_on",
        "switch.test_switch",
        lambda args: received.append(dict(args)),
    )
    setup_harness.call_on_app(
        setup_harness.test_app, "turn_on", "switch.test_switch"
    )
    assert received == [{}]
    # The device double owns the state: a routed command is not reflected.
    assert setup_harness.get_state("switch.test_switch") is None
    assert setup_harness.service_calls(
        service="homeassistant/turn_on", entity_id="switch.test_switch"
    ) == [
        ServiceCallRecord(
            app="test_app",
            service="homeassistant/turn_on",
            entity_id="switch.test_switch",
            kwargs={},
        )
    ]


def test_turn_off_with_handler_routes_and_does_not_reflect(
    setup_harness: Harness,
) -> None:
    received: list[dict[str, object]] = []
    setup_harness.test_app.register_service(
        "homeassistant/turn_off",
        "switch.test_switch",
        lambda args: received.append(dict(args)),
    )
    setup_harness.set_state("switch.test_switch", "on")
    setup_harness.call_on_app(
        setup_harness.test_app, "turn_off", "switch.test_switch"
    )
    assert received == [{}]
    assert setup_harness.get_state("switch.test_switch") == "on"
    assert setup_harness.service_calls(
        service="homeassistant/turn_off", entity_id="switch.test_switch"
    ) == [
        ServiceCallRecord(
            app="test_app",
            service="homeassistant/turn_off",
            entity_id="switch.test_switch",
            kwargs={},
        )
    ]


def test_turn_on_handler_matches_only_registered_entity(
    setup_harness: Harness,
) -> None:
    setup_harness.test_app.register_service(
        "homeassistant/turn_on", "switch.a", lambda _args: None
    )
    setup_harness.call_on_app(setup_harness.test_app, "turn_on", "switch.b")
    assert setup_harness.get_state("switch.b") == "on"


def test_call_service_unregistered_raises(setup_harness: Harness) -> None:
    with pytest.raises(KeyError):
        setup_harness.call_on_app(
            setup_harness.test_app, "call_service", "light/turn_on", "light.x"
        )
    # The log records call ATTEMPTS: the failed call is logged even
    # though no handler ran.
    assert len(setup_harness.service_calls(service="light/turn_on")) == 1
