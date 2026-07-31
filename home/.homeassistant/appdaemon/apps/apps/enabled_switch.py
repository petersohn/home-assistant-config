from __future__ import annotations
import auto_switch
import enabler as enabler_mod
import hass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import locker


class EnabledSwitch(hass.Hass):
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))
    enabler: enabler_mod.Enabler = cast("enabler_mod.Enabler", cast(Any, None))
    targets: auto_switch.MultiSwitcher = cast(
        "auto_switch.MultiSwitcher", cast(Any, None)
    )
    enabler_id: int = 0
    on_guard: enabler_mod.Enabler | None = None
    on_guard_id: int | None = None
    off_guard: enabler_mod.Enabler | None = None
    off_guard_id: int | None = None

    def initialize(self) -> None:
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("EnabledSwitch")
        enabler_app = self.get_app(self.args["enabler"])
        assert isinstance(enabler_app, enabler_mod.Enabler)
        self.enabler = enabler_app
        self.targets = auto_switch.MultiSwitcher(
            self, self.args["targets"]
        )
        self.enabler_id = self.enabler.add_callback(self._on_change)

        def init_guard(arg: str) -> tuple[enabler_mod.Enabler | None, int | None]:
            name = self.args.get(arg)
            if name is None:
                return (None, None)
            assert name is not None
            guard_app = self.get_app(name)
            assert isinstance(guard_app, enabler_mod.Enabler)
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

    def _is_guard_on(self, guard: enabler_mod.Enabler | None) -> bool:
        if guard is None:
            return True
        return guard.is_enabled()

    def _on_change(self) -> None:
        with self.mutex.lock("set_state"):
            enabled = self.enabler.is_enabled()
            on_guard_on = self._is_guard_on(self.on_guard)
            off_guard_on = self._is_guard_on(self.off_guard)
            self.log(
                f"enabled={enabled} on_guard={on_guard_on} off_guard={off_guard_on}"
            )
            if enabled:
                if on_guard_on:
                    self.targets.turn_on()
            else:
                if off_guard_on:
                    self.targets.turn_off()
