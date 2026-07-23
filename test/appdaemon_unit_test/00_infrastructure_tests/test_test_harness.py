from datetime import datetime, timedelta, time
import pytest


@pytest.fixture
def setup_harness(harness):
    """Default harness with test_sensor set."""
    harness.set_state("sensor.test_sensor", "sensor state")
    return harness


def test_start_time(setup_harness):
    assert setup_harness.datetime.time() == time(1, 0, 0)


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0)}], indirect=True)
def test_different_start_time(harness):
    assert harness.datetime.time() == time(21, 30, 0)


def test_set_state(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_set_attribute(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "foobar", a="attr1", b="attr2")
    assert setup_harness.get_state("sensor.test_sensor") == "foobar"
    assert setup_harness.get_state("sensor.test_sensor", attribute="a") == "attr1"
    assert setup_harness.get_state("sensor.test_sensor", attribute="b") == "attr2"


def test_step(setup_harness):
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 10)
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_advance_time(setup_harness):
    setup_harness.advance_time(timedelta(minutes=2))
    assert setup_harness.datetime.time() == time(1, 2, 0)
    setup_harness.advance_time(timedelta(minutes=5))
    assert setup_harness.datetime.time() == time(1, 7, 0)


def test_advance_time_to(setup_harness):
    setup_harness.advance_time_to(time(1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)
    setup_harness.advance_time_to(time(1, 10, 0))
    assert setup_harness.datetime.time() == time(1, 10, 0)


def test_advance_time_to_datetime(setup_harness):
    setup_harness.advance_time_to_datetime(datetime(2018, 1, 1, 1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)


def test_schedule_state_change_in_some_time(setup_harness):
    setup_harness.schedule_call_in(timedelta(minutes=2), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time(timedelta(minutes=1, seconds=50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_some_time(setup_harness):
    setup_harness.schedule_call_at(time(1, 10, 0), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_exact_time(setup_harness):
    setup_harness.schedule_call_at_datetime(
        datetime(2018, 1, 1, 1, 10, 0),
        "set_state", "sensor.test_sensor", "new sensor state",
    )
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_wait_for_state_change(setup_harness):
    change_time = time(1, 2, 10)
    setup_harness.schedule_call_at(change_time, "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == change_time


def test_wait_for_later_state_change(setup_harness):
    setup_harness.schedule_call_at(time(1, 1, 10), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.schedule_call_at(time(1, 1, 30), "set_state", "sensor.test_sensor2", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor2")
    assert setup_harness.get_state("sensor.test_sensor2") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 30)


def test_wait_for_state_change_with_timeout(setup_harness):
    setup_harness.schedule_call_in(timedelta(minutes=1, seconds=50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_deadline(setup_harness):
    setup_harness.schedule_call_at(time(1, 1, 50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 1, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 2, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_new_state(setup_harness):
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", new="new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 40)


def test_wait_for_state_change_with_old_state(setup_harness):
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", old="intermediate sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_state_should_not_change_for_some_time(setup_harness, timing):
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_for("sensor.test_sensor", timedelta(seconds=20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_not_change_until_some_time(setup_harness, timing):
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_until("sensor.test_sensor", datetime(2018, 1, 1, 1, 0, 20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_change_in_some_time(setup_harness, timing):
    duration = timedelta(seconds=30)
    setup_harness.schedule_call_in(duration, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_in("sensor.test_sensor", "new sensor state", duration)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 30)


def test_state_should_change_at_some_time(setup_harness, timing):
    target = time(1, 1, 0)
    setup_harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == target


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0), "interval": timedelta(minutes=10)}], indirect=True)
def test_state_should_change_next_day(harness):
    harness.set_state("sensor.test_sensor", "sensor state")
    target = time(1, 0, 0)
    harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    from helpers.timing import Timing
    timing = Timing(harness)
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert harness.get_state("sensor.test_sensor") == "new sensor state"
    assert harness.datetime == datetime(2018, 1, 2, 1, 0, 0)


def test_converted_state_expectations(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "12")
    assert setup_harness.get_state("sensor.test_sensor", type="int") == 12