from __future__ import annotations
import time
from typing import Any

from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.hass_client import HassClient
from appdaemon_integration_test.helpers.type_util import values_equal


def _wait_for_hass_state(
    hass_client: HassClient, entity_id: str, expected: Any, timeout: float = 15.0
) -> None:
    deadline = time.time() + timeout
    last: Any = None
    while time.time() < deadline:
        try:
            last = hass_client.get_state(entity_id)
        except Exception:
            last = None
        if values_equal(last, expected):
            return
        time.sleep(0.1)
    assert values_equal(last, expected), (
        f"{entity_id}: expected {expected!r}, got {last!r}"
    )


def _wait_for_hass_entity_gone(
    hass_client: HassClient, entity_id: str, timeout: float = 15.0
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(s["entity_id"] != entity_id for s in hass_client.get_states()):
            return
        time.sleep(0.1)
    assert all(
        s["entity_id"] != entity_id for s in hass_client.get_states()
    ), f"{entity_id} still present in HASS"


def _admin_set_state(
    appdaemon_client: AppDaemonClient, entity_id: str, value: Any
) -> None:
    appdaemon_client.call_function(
        "set_state", entity_id, state=value, namespace="admin"
    )


def test_admin_entities_synced_to_hass(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    admin_total = appdaemon_client.call_function(
        "get_state", "sensor.total_apps", namespace="admin"
    )
    assert admin_total is not None
    _wait_for_hass_state(hass_client, "sensor.total_apps", admin_total)

    app_state = appdaemon_client.call_function(
        "get_state", "app.admin_sync", namespace="admin"
    )
    assert app_state is not None
    _wait_for_hass_state(hass_client, "app.admin_sync", app_state)


def test_admin_change_propagates(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    _admin_set_state(appdaemon_client, "sensor.total_apps", 123)
    _wait_for_hass_state(hass_client, "sensor.total_apps", 123)

    _admin_set_state(appdaemon_client, "sensor.total_apps", 456)
    _wait_for_hass_state(hass_client, "sensor.total_apps", 456)


def test_admin_entity_removal_syncs(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    _admin_set_state(appdaemon_client, "sensor.admin_sync_probe", "probe")
    _wait_for_hass_state(hass_client, "sensor.admin_sync_probe", "probe")

    appdaemon_client.call_function(
        "remove_entity", "sensor.admin_sync_probe", namespace="admin"
    )
    appdaemon_client.call_on_app("admin_sync", "full_sync", {})
    _wait_for_hass_entity_gone(hass_client, "sensor.admin_sync_probe")