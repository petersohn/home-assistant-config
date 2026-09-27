from __future__ import annotations

import datetime
import hass
import traceback
from hass_common import AttributeValue
from typing import Any, final, TYPE_CHECKING, cast

if TYPE_CHECKING:
    import locker


@final
class AdminSync(hass.Hass):
    mirrored: dict[str, tuple[str | None, dict[str, AttributeValue]]] = {}
    resync_timer: str | None = None
    listener_registered: bool = False
    resync_interval: datetime.timedelta = cast(
        "datetime.timedelta", cast(Any, None)
    )
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    def initialize(self) -> None:
        self.mirrored = {}
        self.resync_timer = None
        self.listener_registered = False
        interval: dict[str, int | float] = self.args.get(
            "resync_interval", {"minutes": 5}
        )
        assert isinstance(interval, dict)
        self.resync_interval = datetime.timedelta(**interval)

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("AdminSync")

        self._sync_with_retry()

    def _retry_init(self, kwargs: dict[str, object]) -> None:
        self._sync_with_retry()

    def _sync_with_retry(self) -> None:
        try:
            self._ensure_listener()
            self.full_sync({})
        except Exception:
            self.error(traceback.format_exc())
            _ = self.run_in(self._retry_init, 60)

    def _ensure_listener(self) -> None:
        if not self.listener_registered:
            self._register_listener()
            self.listener_registered = True

    def _register_listener(self) -> None:
        """Listen for admin namespace changes.

        AppDaemon does not dispatch ``listen_state`` callbacks for the
        admin namespace, and entity additions/removals surface as the
        ``__AD_ENTITY_ADDED`` and ``__AD_ENTITY_REMOVED`` system events,
        not as ``state_changed``. ``__silent`` suppresses the admin
        counter updates that every dispatched callback performs, which
        would otherwise feed this listener forever.
        """
        self.listen_event(
            self.on_admin_change,
            ["state_changed", "__AD_ENTITY_ADDED", "__AD_ENTITY_REMOVED"],
            namespace="admin",
            __silent=True,
        )

    def on_admin_change(
        self, event: str, data: dict[str, object], **kwargs: object
    ) -> None:
        entity = data.get("entity_id")
        if not isinstance(entity, str):
            return
        with self.mutex.lock("on_admin_change"):
            if event == "__AD_ENTITY_REMOVED":
                self._remove(entity)
            else:
                self._mirror(entity)

    def _remove(self, entity: str) -> None:
        if entity not in self.mirrored:
            return
        try:
            self.remove_entity(entity)
        except Exception:
            self.error(f"Failed to remove {entity}")
            self.error(traceback.format_exc())
        else:
            del self.mirrored[entity]

    def _mirror(self, entity: str) -> None:
        try:
            state = self.get_state(entity, attribute="all", namespace="admin")
            assert isinstance(state, dict)
            value = state.get("state")
            if value is not None and not isinstance(value, str):
                value = str(value)
            raw_attributes: dict[str, AttributeValue] | None = (
                state.get("attributes")
            )
            assert isinstance(raw_attributes, dict)
            attributes: dict[str, AttributeValue] = dict(raw_attributes)
            if self.mirrored.get(entity) == (value, attributes):
                return
            self.set_state(entity, state=value, attributes=attributes)
            self.mirrored[entity] = (value, attributes)
        except Exception:
            self.error(f"Failed to mirror {entity}")
            self.error(traceback.format_exc())

    def full_sync(self, kwargs: dict[str, object]) -> None:
        with self.mutex.lock("full_sync"):
            admin: dict[str, str] = self.get_state(
                entity_id=None, namespace="admin"
            )
            assert isinstance(admin, dict)
            for entity in admin:
                self._mirror(entity)
            for entity in list(self.mirrored):
                if entity not in admin:
                    self._remove(entity)
            if self.resync_timer is None:
                self.resync_timer = self.run_every(
                    self.full_sync,
                    self.datetime() + self.resync_interval,
                    int(self.resync_interval.total_seconds()),
                )

    def terminate(self) -> None:
        pass
