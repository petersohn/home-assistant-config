from __future__ import annotations
from datetime import timedelta
from typing import Any

import admin_sync
import pytest
from appdaemon_unit_test.test_helpers.harness import Harness

admin_total = "sensor.total_apps"
admin_uptime = "sensor.appdaemon_uptime"


def _set_admin(
    harness: Harness, entity: str, state: str, **attributes: str
) -> None:
    harness.app_manager.set_state(
        "test", entity, state, attributes, namespace="admin"
    )
    harness.app_manager.call_pending_callbacks()


def _create_admin_sync(
    harness: Harness, **kwargs: object
) -> admin_sync.AdminSync:
    app = _create_admin_sync_app(harness, **kwargs)
    harness.advance_time(timedelta(seconds=1))
    return app


def _create_admin_sync_app(
    harness: Harness, **kwargs: object
) -> admin_sync.AdminSync:
    app = harness.create_app("admin_sync", "AdminSync", "admin_sync", **kwargs)
    assert isinstance(app, admin_sync.AdminSync)
    return app


def test_initial_sync_is_deferred_to_avoid_blocking_app_start(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "42")
    _set_admin(harness, admin_uptime, "0:00:00")
    _create_admin_sync_app(harness)
    assert harness.get_state(admin_total) is None
    assert harness.get_state(admin_uptime) is None
    harness.advance_time(timedelta(seconds=1))
    assert harness.get_state(admin_total) == "42"
    assert harness.get_state(admin_uptime) == "0:00:00"


def test_deferred_initial_sync_is_ignored_after_termination(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "42")
    app = _create_admin_sync_app(harness)

    # terminate() runs before AppDaemon removes the managed object.
    app.terminate()
    app._retry_init({})  # pyright: ignore[reportPrivateUsage]

    assert harness.get_state(admin_total) is None


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


@pytest.mark.parametrize(
    "harness", [{"interval": timedelta(seconds=1)}], indirect=True
)
def test_failed_deferred_initial_sync_retries_after_60_seconds(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "1")
    app = _create_admin_sync_app(harness)
    original_get_state = app.get_state
    fail_initial_sync = True

    def fail_first_get_state(
        entity_id: str | None = None,
        attribute: str | None = None,
        default: Any | None = None,
        namespace: str | None = None,
        copy: bool = True,
    ) -> Any:
        nonlocal fail_initial_sync
        if fail_initial_sync:
            fail_initial_sync = False
            raise RuntimeError("HASS down")
        return original_get_state(
            entity_id,
            attribute=attribute,
            namespace="default" if namespace is None else namespace,
        )

    app.get_state = fail_first_get_state  # type: ignore[method-assign]
    harness.clear_errors()
    try:
        harness.advance_time(timedelta(seconds=1))
        assert harness.get_state(admin_total) is None
        assert harness.app_manager.has_error()
        harness.clear_errors()

        harness.advance_time(timedelta(seconds=59))
        assert harness.get_state(admin_total) is None
        harness.advance_time(timedelta(seconds=1))
        assert not harness.app_manager.has_error()
        assert harness.get_state(admin_total) == "1"
    finally:
        app.get_state = original_get_state  # type: ignore[method-assign]


def test_mirror_failure_logged_not_fatal(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    app = _create_admin_sync(harness)
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
    app.on_admin_change("state_changed", {"entity_id": admin_total})
    harness.clear_errors()


def test_mirror_of_vanished_entity_skipped_silently(
    harness: Harness,
) -> None:
    app = _create_admin_sync(harness)
    harness.clear_errors()
    # Event fires for an entity that is already gone by the time the
    # callback reads it (fast scheduler_callback churn).
    app.on_admin_change("state_changed", {"entity_id": "scheduler_callback.gone"})
    assert harness.get_state("scheduler_callback.gone") is None
    assert not harness.app_manager.has_error()


def test_scheduler_callback_entities_are_excluded_from_full_sync(
    harness: Harness,
) -> None:
    scheduler_callback = "scheduler_callback.transient"
    _set_admin(harness, admin_total, "1")
    _set_admin(harness, scheduler_callback, "pending")

    _create_admin_sync(harness)

    assert harness.get_state(admin_total) == "1"
    assert harness.get_state(scheduler_callback) is None


def test_scheduler_callback_change_event_is_excluded_from_mirroring(
    harness: Harness,
) -> None:
    scheduler_callback = "scheduler_callback.transient"
    _create_admin_sync(harness)

    _set_admin(harness, scheduler_callback, "pending")

    assert harness.get_state(scheduler_callback) is None


def test_override_attributes_applied(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "1", friendly_name="Total Apps")
    _create_admin_sync(
        harness, attributes={admin_total: {"icon": "mdi:counter"}}
    )
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["icon"] == "mdi:counter"
    friendly_name = attributes["friendly_name"]
    assert isinstance(friendly_name, str)
    assert friendly_name == "Total Apps"


def test_override_wins_over_numeric_annotation(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "42")
    _create_admin_sync(
        harness,
        attributes={admin_total: {"unit_of_measurement": "apps"}},
    )
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["state_class"] == "measurement"
    assert attributes["unit_of_measurement"] == "apps"


def test_no_override_unchanged(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "1", friendly_name="Total Apps")
    _create_admin_sync(harness)
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert "icon" not in attributes


def test_override_for_unknown_entity_inert_until_present(
    harness: Harness,
) -> None:
    _create_admin_sync(
        harness, attributes={"sensor.ghost": {"icon": "mdi:ghost"}}
    )
    assert harness.get_state("sensor.ghost") is None
    _set_admin(harness, "sensor.ghost", "boo")
    assert harness.get_state("sensor.ghost") == "boo" or (
        harness.get_state("sensor.ghost") == "boo"
    )
    mirrored = harness.app_manager.get_state("sensor.ghost", "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["icon"] == "mdi:ghost"


def test_override_applies_on_resync(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "1")
    _create_admin_sync(harness)
    app = harness.get_app("admin_sync")
    assert isinstance(app, admin_sync.AdminSync)
    app.attributes = {admin_total: {"icon": "mdi:counter"}}
    harness.advance_time(timedelta(minutes=5))
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["icon"] == "mdi:counter"


def test_mirror_sanitizes_hyphens(harness: Harness) -> None:
    _set_admin(harness, "thread.thread-0", "idle", q="0")
    _create_admin_sync(harness)
    assert harness.get_state("thread.thread_0") == "idle"
    assert harness.get_state("thread.thread-0") is None
    mirrored = harness.app_manager.get_state("thread.thread_0", "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["q"] == "0"


def test_removal_uses_sanitized_name(harness: Harness) -> None:
    _set_admin(harness, "thread.thread-0", "idle")
    _create_admin_sync(harness)
    assert harness.get_state("thread.thread_0") == "idle"
    harness.app_manager.remove_entity("thread.thread-0", namespace="admin")
    harness.app_manager.call_pending_callbacks()
    assert harness.get_state("thread.thread_0") is None


def test_resync_removes_sanitized_stale_entities(
    harness: Harness,
) -> None:
    _set_admin(harness, "thread.thread-0", "idle")
    _create_admin_sync(harness)
    assert harness.get_state("thread.thread_0") == "idle"
    harness.app_manager.remove_entity("thread.thread-0", namespace="admin")
    harness.advance_time(timedelta(minutes=5))
    assert harness.get_state("thread.thread_0") is None


def test_numeric_state_gets_measurement_attributes(
    harness: Harness,
) -> None:
    _set_admin(harness, admin_total, "42")
    _create_admin_sync(harness)
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["state_class"] == "measurement"
    assert attributes["unit_of_measurement"] == ""


def test_non_numeric_state_not_annotated(harness: Harness) -> None:
    _set_admin(harness, admin_uptime, "1 day, 0:00:00")
    _create_admin_sync(harness)
    mirrored = harness.app_manager.get_state(admin_uptime, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert "state_class" not in attributes
    assert "unit_of_measurement" not in attributes


def test_numeric_app_state_annotated(harness: Harness) -> None:
    app_entity = "app.some_app"
    _set_admin(harness, app_entity, "3")
    _create_admin_sync(harness)
    mirrored = harness.app_manager.get_state(app_entity, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["state_class"] == "measurement"
    assert attributes["unit_of_measurement"] == ""


def test_numeric_change_keeps_annotation(harness: Harness) -> None:
    _set_admin(harness, admin_total, "1")
    _create_admin_sync(harness)
    _set_admin(harness, admin_total, "2")
    assert harness.get_state(admin_total) == "2"
    mirrored = harness.app_manager.get_state(admin_total, "all")
    assert isinstance(mirrored, dict)
    attributes = mirrored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["state_class"] == "measurement"
    assert attributes["unit_of_measurement"] == ""
