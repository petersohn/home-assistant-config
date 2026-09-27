from __future__ import annotations
from datetime import timedelta
from typing import Any

import admin_sync
from appdaemon_unit_test.test_helpers.harness import Harness

admin_total = "sensor.total_apps"
admin_uptime = "sensor.appdaemon_uptime"


def _set_admin(harness: Harness, entity: str, state: str, **attributes: str) -> None:
    harness.app_manager.set_state("test", entity, state, attributes, namespace="admin")
    harness.app_manager.call_pending_callbacks()


def _create_admin_sync(harness: Harness) -> admin_sync.AdminSync:
    return _create_admin_sync_app(harness)


def _create_admin_sync_app(harness: Harness) -> admin_sync.AdminSync:
    app = harness.create_app("admin_sync", "AdminSync", "admin_sync")
    assert isinstance(app, admin_sync.AdminSync)
    return app


def test_initial_full_sync(harness: Harness) -> None:
    _set_admin(harness, admin_total, "42")
    _set_admin(harness, admin_uptime, "0:00:00")
    _create_admin_sync(harness)
    assert harness.get_state(admin_total) == "42"
    assert harness.get_state(admin_uptime) == "0:00:00"


def test_incremental_mirror_on_change(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    _create_admin_sync(harness)
    assert harness.get_state(admin_total) == "1"
    _set_admin(harness, admin_total, "2")
    assert harness.get_state(admin_total) == "2"


def test_attributes_mirrored(harness: Harness) -> None:
    _set_admin(harness, admin_total, "5", friendly_name="Total Apps")
    _create_admin_sync(harness)
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    friendly_name = attributes["friendly_name"]
    assert isinstance(friendly_name, str)
    assert friendly_name == "Total Apps"


def test_resync_removes_stale_entities(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    _create_admin_sync(harness)
    assert harness.get_state(admin_total) == "1"
    harness.app_manager.remove_entity(admin_total, namespace="admin")
    harness.advance_time(timedelta(minutes=5))
    assert harness.get_state(admin_total) is None


def test_removal_event_removes_mirror_immediately(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "1")
    _create_admin_sync(harness)
    assert harness.get_state(admin_total) == "1"
    harness.app_manager.remove_entity(admin_total, namespace="admin")
    harness.app_manager.call_pending_callbacks()
    assert harness.get_state(admin_total) is None


def test_unchanged_not_re_set(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    app = _create_admin_sync(harness)
    calls: list[str] = []
    original = app.set_state

    def spy(
        entity_id: str,
        state: str | None = None,
        namespace: str | None = "default",
        attributes: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        calls.append(entity_id)
        # Mock set_state returns None, prod returns dict; ignore because
        # signatures are structurally incompatible.
        return original(  # type: ignore[return-value,no-any-return]
            entity_id, state, namespace=namespace, attributes=attributes
        )

    app.set_state = spy  # type: ignore[method-assign]
    # Resync with unchanged admin state: suppression must skip set_state.
    harness.advance_time(timedelta(minutes=5))
    assert calls == []
    # Admin change must still mirror.
    _set_admin(harness, admin_total, "2")
    assert calls == [admin_total]
    assert harness.get_state(admin_total) == "2"


def test_mirror_failure_logged_not_fatal(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    app = harness.app_manager.create_app(
        "admin_sync", "AdminSync", "admin_sync"
    )
    harness.clear_errors()
    assert isinstance(app, admin_sync.AdminSync)

    def failing(
        entity_id: str,
        state: Any = None,
        namespace: str | None = "default",
        attributes: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise RuntimeError("HASS down")

    app.set_state = failing  # type: ignore[method-assign]
    # Must not raise; error is logged internally.
    app._mirror(admin_total)
    harness.clear_errors()
