from __future__ import annotations

import datetime
import hass
import traceback
from hass_common import EntityValue
from typing import Any, final, TYPE_CHECKING, cast

if TYPE_CHECKING:
    import locker


@final
class AdminSync(hass.Hass):
    mirrored: dict[str, tuple[str | None, dict[str, str]]] = {}
    resync_timer: str | None = None
    resync_interval: datetime.timedelta = cast(
        "datetime.timedelta", cast(Any, None)
    )
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    def initialize(self) -> None:
        self.mirrored = {}
        self.resync_timer = None
        interval = self.args.get("resync_interval", {"minutes": 5})
        assert isinstance(interval, dict)
        self.resync_interval = datetime.timedelta(**interval)

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("AdminSync")

        try:
            self._register_listener()
            self.full_sync({})
        except Exception:
            self.error(traceback.format_exc())
            _ = self.run_in(self._retry_init, 60)

    def _retry_init(self, kwargs: dict[str, Any]) -> None:
        try:
            self._register_listener()
            self.full_sync({})
        except Exception:
            self.error(traceback.format_exc())
            _ = self.run_in(self._retry_init, 60)

    def _register_listener(self) -> None:
        self.listen_state(self.on_admin_change, entity_id=None, namespace="admin")

    def on_admin_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_admin_change"):
            self._mirror(entity)

    def _mirror(self, entity: str) -> None:
        try:
            state = self.get_state(entity, attribute="all", namespace="admin")
            assert isinstance(state, dict)
            value = state.get("state")
            assert value is None or isinstance(value, str)
            raw_attributes = state.get("attributes")
            assert isinstance(raw_attributes, dict)
            attributes: dict[str, str] = dict(raw_attributes)
            if self.mirrored.get(entity) == (value, attributes):
                return
            self.set_state(entity, state=value, attributes=attributes)
            self.mirrored[entity] = (value, attributes)
        except Exception:
            self.error(f"Failed to mirror {entity}")
            self.error(traceback.format_exc())

    def full_sync(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("full_sync"):
            try:
                admin = self.get_state(entity_id=None, namespace="admin")
                assert isinstance(admin, dict)
                for entity in admin:
                    self._mirror(entity)
                for entity in list(self.mirrored):
                    if entity not in admin:
                        try:
                            self.remove_entity(entity)
                        except Exception:
                            self.error(f"Failed to remove {entity}")
                            self.error(traceback.format_exc())
                        else:
                            del self.mirrored[entity]
            except Exception:
                self.error(traceback.format_exc())
        if self.resync_timer is None:
            self.resync_timer = self.run_every(
                self.full_sync,
                self.datetime() + self.resync_interval,
                int(self.resync_interval.total_seconds()),
            )

    def terminate(self) -> None:
        pass