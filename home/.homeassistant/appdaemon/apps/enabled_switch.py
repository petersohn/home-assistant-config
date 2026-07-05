from __future__ import annotations
import auto_switch
import enabler
import hass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class EnabledSwitch(hass.Hass):
    def initialize(self) -> None:
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("EnabledSwitch")
        enabler_app = self.get_app(self.args["enabler"])
        assert isinstance(enabler_app, enabler.Enabler)
        self.enabler: enabler.Enabler = enabler_app
        self.targets = auto_switch.MultiSwitcher(
            self, self.args["targets"]
        )
        self.enabler_id: int = self.enabler.add_callback(self._on_change)

        def init_guard(arg: str) -> tuple[enabler.Enabler | None, int | None]:
            name = self.args.get(arg)
            if name is None:
                return (None, None)
            assert name is not None
            guard_app = self.get_app(name)
            assert isinstance(guard_app, enabler.Enabler)
            guard_id: int = guard_app.add_callback(self._on_change)
            return (guard_app, guard_id)

        (self.on_guard, self.on_guard_id) = init_guard("on_guard")
        (self.off_guard, self.off_guard_id) = init_guard("off_guard")

        self.targets.init(self.enabler.is_enabled())

    def terminate(self) -> None:
        self.enabler.remove_callback(self.enabler_id)
        if self.on_guard is not None:
            assert self.on_guard_id is not None
            self.on_guard.remove_callback(self.on_guard_id)
        if self.off_guard is not None:
            assert self.off_guard_id is not None
            self.off_guard.remove_callback(self.off_guard_id)
        self.targets.deinit()

    def _is_guard_on(self, guard: enabler.Enabler | None) -> bool:
        if guard is None:
            return True
        return guard.is_enabled()

    def _on_change(self) -> None:
        with self.mutex.lock("set_state"):
            enabled = self.enabler.is_enabled()
            on_guard_on = self._is_guard_on(self.on_guard)
            off_guard_on = self._is_guard_on(self.off_guard)
            self.log(
                "enabled={} on_guard={} off_guard={}".format(
                    enabled, on_guard_on, off_guard_on
                )
            )
            if enabled:
                if on_guard_on:
                    self.targets.turn_on()
            else:
                if off_guard_on:
                    self.targets.turn_off()
