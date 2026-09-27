from __future__ import annotations

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