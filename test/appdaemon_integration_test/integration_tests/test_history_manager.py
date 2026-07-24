from __future__ import annotations
import time
from datetime import datetime, timedelta

from helpers.appdaemon_client import AppDaemonClient
from helpers.hass_client import HassClient
from helpers.history_util import convert_history_output
from helpers.type_util import values_equal

sensor = "sensor.history_test"
sensor1 = "sensor.test_sensor1"
sensor2 = "sensor.test_sensor2"


def _initialize(appdaemon_client: AppDaemonClient) -> None:
    appdaemon_client.initialize_states(**{sensor: 0, sensor1: 0, sensor2: 0})
    appdaemon_client.load_apps()


def _history_should_be(
    appdaemon_client: AppDaemonClient, app: str, *expected: object
) -> None:
    history = appdaemon_client.call_on_app(app, "get_value_history")
    actual = convert_history_output(list(history))
    assert len(actual) == len(expected), (
        f"history length mismatch: {actual} != {list(expected)}"
    )
    for act, exp in zip(actual, expected):
        assert values_equal(act, exp), f"history mismatch: {actual} != {list(expected)}"


def _get_last_changed(appdaemon_client: AppDaemonClient, app: str) -> str:
    return appdaemon_client.call_on_app(app, "last_changed",
                                        result_type="datestr")


def _get_last_updated(appdaemon_client: AppDaemonClient, app: str) -> str:
    return appdaemon_client.call_on_app(app, "last_updated",
                                        result_type="datestr")


def _last_changed_and_last_updated_should_be_the_same(
    appdaemon_client: AppDaemonClient, app: str
) -> None:
    last_changed = _get_last_changed(appdaemon_client, app)
    last_updated = _get_last_updated(appdaemon_client, app)
    assert last_changed == last_updated


def _should_be_updated_after_changed(
    appdaemon_client: AppDaemonClient, app: str
) -> None:
    last_changed = _get_last_changed(appdaemon_client, app)
    last_updated = _get_last_updated(appdaemon_client, app)
    difference = (
        datetime.fromisoformat(last_updated)
        - datetime.fromisoformat(last_changed)
    )
    assert difference.total_seconds() > 0


def test_load_history(
    appdaemon_client: AppDaemonClient, hass_client: HassClient
) -> None:
    _initialize(appdaemon_client)
    appdaemon_client.set_state(sensor, 12)
    appdaemon_client.set_state(sensor, 3)
    appdaemon_client.set_state(sensor, 91)
    appdaemon_client.set_state(sensor, -32)
    hass_client.wait_for_history_size(sensor, 5)
    appdaemon_client.load_apps("HistoryManager")
    appdaemon_client.set_state(sensor, 23)
    appdaemon_client.set_state(sensor, 99)

    _history_should_be(
        appdaemon_client, "test_history_manager",
        0.0, 12.0, 3.0, 91.0, -32.0, 23.0, 99.0,
    )


def test_change_tracker(appdaemon_client: AppDaemonClient) -> None:
    _initialize(appdaemon_client)
    appdaemon_client.set_state(sensor1, 6, foo=1)
    appdaemon_client.set_state(sensor2, 6, foo=1)
    time.sleep(0.5)
    appdaemon_client.set_state(sensor1, 8, foo=2)
    appdaemon_client.set_state(sensor2, 6, foo=2)
    appdaemon_client.load_apps("ChangeTrackers")
    _last_changed_and_last_updated_should_be_the_same(appdaemon_client, "tracker1")
    _should_be_updated_after_changed(appdaemon_client, "tracker2")
    time.sleep(0.5)
    appdaemon_client.set_state(sensor1, 8, foo=3)
    appdaemon_client.set_state(sensor2, 8, foo=3)
    time.sleep(1)
    _should_be_updated_after_changed(appdaemon_client, "tracker1")
    _last_changed_and_last_updated_should_be_the_same(appdaemon_client, "tracker2")