from __future__ import annotations

import time
from typing import Any

from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.hass_client import HassClient


def _admin_get_active_apps(appdaemon_client: AppDaemonClient) -> float:
    value = appdaemon_client.call_function(
        "get_state", "sensor.active_apps", namespace="admin"
    )
    assert isinstance(value, int | float | str)
    return float(value)


def _admin_get_app_state(
    appdaemon_client: AppDaemonClient, app_name: str
) -> str:
    value = appdaemon_client.call_function(
        "get_state", "app." + app_name, namespace="admin"
    )
    assert isinstance(value, str)
    return value


def test_admin_entities_synced_to_hass(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    active_apps = _admin_get_active_apps(appdaemon_client)
    hass_client.wait_for_state("sensor.active_apps", active_apps)

    app_state = _admin_get_app_state(appdaemon_client, "admin_sync")
    hass_client.wait_for_state("app.admin_sync", app_state)


def test_admin_change_propagates(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    active_apps = _admin_get_active_apps(appdaemon_client)
    hass_client.wait_for_state("sensor.active_apps", active_apps)

    appdaemon_client.load_apps("AdminSync", "dummy1")
    active_apps_after_load = _admin_get_active_apps(appdaemon_client)
    assert active_apps_after_load == active_apps + 1
    hass_client.wait_for_state("sensor.active_apps", active_apps_after_load)

    app_state = _admin_get_app_state(appdaemon_client, "dummy1")
    hass_client.wait_for_state("app.dummy1", app_state)

    appdaemon_client.load_apps("AdminSync")
    hass_client.wait_for_app_state("app.dummy1", "terminated")
    active_apps_after_unload = _admin_get_active_apps(appdaemon_client)
    assert active_apps_after_unload == active_apps
    hass_client.wait_for_state(
        "sensor.active_apps", active_apps_after_unload
    )


def test_admin_entity_removal_syncs(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    appdaemon_client.call_function(
        "set_state",
        "sensor.admin_sync_probe",
        state="probe",
        namespace="admin",
    )
    hass_client.wait_for_state("sensor.admin_sync_probe", "probe")

    appdaemon_client.call_function(
        "remove_entity", "sensor.admin_sync_probe", namespace="admin"
    )
    hass_client.wait_for_entity_gone("sensor.admin_sync_probe")


def test_override_attributes_applied(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    active_apps = _admin_get_active_apps(appdaemon_client)
    hass_client.wait_for_state("sensor.active_apps", active_apps)
    hass_client.wait_for_attributes(
        "sensor.active_apps", {"icon": "mdi:cog-play"}
    )


def test_thread_domain_entities_present(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    admin: dict[str, Any] = appdaemon_client.call_function(
        "get_state", None, namespace="admin"
    )
    assert isinstance(admin, dict)
    assert all(isinstance(entity, str) for entity in admin)
    thread_entities: list[str] = [
        entity for entity in admin if entity.startswith("thread.")
    ]
    assert len(thread_entities) >= 3

    hass_thread_entities: list[str] = []
    for _ in range(150):
        hass_thread_entities = [
            state["entity_id"]
            for state in hass_client.get_states()
            if state["entity_id"].startswith("thread.")
        ]
        if len(hass_thread_entities) == len(thread_entities):
            break
        time.sleep(0.1)

    assert sorted(hass_thread_entities) == sorted(
        entity.replace("-", "_") for entity in thread_entities
    )
    for entity in thread_entities:
        if "-" not in entity:
            continue
        hass_client.wait_for_state(
            entity.replace("-", "_"), admin[entity]["state"]
        )
    assert "thread.thread-0" not in (
        state["entity_id"] for state in hass_client.get_states()
    )


def test_thread_aggregate_sensors(
    hass_client: HassClient, appdaemon_client: AppDaemonClient
) -> None:
    appdaemon_client.load_apps("AdminSync")

    admin: dict[str, Any] = appdaemon_client.call_function(
        "get_state", None, namespace="admin"
    )
    thread_entities: list[str] = [
        entity for entity in admin if entity.startswith("thread.")
    ]

    hass_client.wait_for_state("sensor.total_threads", len(thread_entities))

    def _active_in_hass() -> tuple[int, bool]:
        admin = appdaemon_client.call_function(
            "get_state", None, namespace="admin"
        )
        active = sum(
            1
            for entity in admin
            if entity.startswith("thread.")
            and admin[entity]["state"] != "idle"
        )
        return active, hass_client.get_state(
            "sensor.active_threads"
        ) == str(active)

    for _ in range(150):
        active, matches = _active_in_hass()
        if matches:
            break
        time.sleep(0.1)
    else:
        assert False, "sensor.active_threads did not converge"
    assert hass_client.get_state("sensor.active_threads") == str(active)