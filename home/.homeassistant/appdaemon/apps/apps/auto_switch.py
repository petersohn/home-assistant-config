from __future__ import annotations
import hass
from hass_common import EntityValue
from typing import TYPE_CHECKING, Any, cast, final

if TYPE_CHECKING:
    import enabler
    import locker


class AutoSwitch(hass.Hass):
    target: str = ""
    switch: str | None = None
    reentrant: bool = False
    intended_state: str | None = None
    timer: str | None = None
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))
    listen_handles: list[str] = []
    state: int | None = None
    enabler: enabler.Enabler | None = None
    enabler_id: int | None = None

    def initialize(self) -> None:
        self.target = self.args["target"]
        self.switch = self.args.get("switch")
        self.reentrant = self.args.get("reentrant", False)
        self.intended_state = None
        self.timer = None

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("AutoSwitch")

        self.listen_handles = []

        with self.mutex.lock("initialize"):
            self.listen_handles.append(
                self.listen_state(self.on_target_change, entity_id=self.target)
            )
            if self.switch:
                self.run_in(self.initialize_state, 0)
                self.listen_handles.append(
                    self.listen_state(self.on_switch_change, entity_id=self.switch)
                )
            self.state = None
            self.run_in(lambda _: self.init(), 10 if self.switch else 0)

            enabler_name = self.args.get("enabler")
            if enabler_name is not None:
                import enabler as enabler_mod
                enabler_app = self.get_app(enabler_name)
                assert isinstance(enabler_app, enabler_mod.Enabler)
                self.enabler = enabler_app
                self.enabler_id = enabler_app.add_callback(
                    self.on_enabled_changed
                )
            else:
                self.enabler = None
                self.enabler_id = None

    def terminate(self) -> None:
        for handle in getattr(self, "listen_handles", []):
            self.cancel_listen_state(handle)
        if self.enabler is not None:
            assert self.enabler_id is not None
            self.enabler.remove_callback(self.enabler_id)

    def init(self) -> None:
        with self.mutex.lock("init"):
            try:
                self.log("init")
                if self.state is None:
                    self.__update(0)
            except Exception:
                self.run_in(lambda _: self.init(), 1)
                raise

    def initialize_state(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("initialize_state"):
            switch_state = self.get_state(self.switch)
            self.log(f"Switch state={switch_state}")
            if switch_state == "on":
                self.log("Initially turning on")
                self.turn_on(self.target)
            elif switch_state == "off":
                self.log("Initially turning off")
                self.turn_off(self.target)

    def auto_turn_on(self) -> None:
        with self.mutex.lock("auto_turn_on"):
            self.log("turn on")
            if self.reentrant:
                if self.state is None:
                    self.state = 0
                self.__update(self.state + 1)
            else:
                self.__update(1)

    def auto_turn_off(self) -> None:
        with self.mutex.lock("auto_turn_off"):
            self.log("turn off")
            if self.reentrant:
                assert self.state is not None and self.state != 0
                self.__update(self.state - 1)
            else:
                self.__update(0)

    def on_enabled_changed(self) -> None:
        with self.mutex.lock("on_enabled_changed"):
            self.__update(self.state)

    def __update(self, state: int | None) -> None:
        self.__stop_timer()
        self.log(f"Got new state: {self.state} -> {state}")
        self.state = state

        if self.switch and self.get_state(self.switch) != "auto":
            self.log("On manual mode")
            return

        if state == 0 or (
            self.enabler is not None and not self.enabler.is_enabled()
        ):
            self.__set_intended_state("off")
            if self.get_state(self.target) != "off":
                self.turn_off(self.target)
        else:
            self.__set_intended_state("on")
            if self.get_state(self.target) != "on":
                self.turn_on(self.target)

    def update(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("update"):
            self.log("Timeout")
            self.__update(self.state)

    def __set_intended_state(self, state: str) -> None:
        self.log("Turning " + state)
        if self.intended_state is not None or self.get_state(self.target) != state:
            self.intended_state = state
            self.timer = self.run_in(self.update, 10)

    def on_switch_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_switch_change"):
            self.log("on_switch_change")
            value = new if new is not None else self.get_state(entity)
            if value == "on":
                self.log("Manually turning on")
                self.__set_intended_state("on")
                if self.get_state(self.target) != "on":
                    self.turn_on(self.target)
            elif value == "off":
                self.log("Manually turning off")
                self.__set_intended_state("off")
                if self.get_state(self.target) != "off":
                    self.turn_off(self.target)
            else:
                self.log("Setting to auto")
                self.__update(self.state)

    def on_target_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_target_change"):
            self.log("on_target_change")
            value = new if new is not None else self.get_state(entity)
            if value != "on" and value != "off":
                self.log(f"Invalid state: {value}")
                return
            assert isinstance(value, str)
            if not self.intended_state:
                if self.switch is None or self.get_state(self.switch) == "auto":
                    self.log(f"State change detected: {value}")
                    self.__update(self.state)
                else:
                    switch_state = self.get_state(self.switch)
                    assert isinstance(switch_state, str)
                    self.log(f"Reverting target to manual state: {switch_state}")
                    self.__set_intended_state(switch_state)
                    if self.get_state(self.target) != switch_state:
                        if switch_state == "on":
                            self.turn_on(self.target)
                        else:
                            self.turn_off(self.target)
            elif value == self.intended_state:
                self.log(f"State stabilized to {new}")
                self.intended_state = None
                self.__stop_timer()
            else:
                self.log(
                    f"Wrong state: {value}, intended={self.intended_state}"
                )
                self.__update(self.state)

    def __stop_timer(self) -> None:
        if self.timer:
            self.cancel_timer(self.timer)
            self.timer = None


@final
class Switcher:
    def __init__(self, auto_switch: AutoSwitch) -> None:
        import locker
        locker_app = auto_switch.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("Switcher")
        self.auto_switch = auto_switch
        self.state = False

    def turn_on(self) -> None:
        with self.mutex.lock("turn_on"):
            if not self.state:
                self.auto_switch.auto_turn_on()
                self.state = True

    def turn_off(self) -> None:
        with self.mutex.lock("turn_off"):
            if self.state:
                self.auto_switch.auto_turn_off()
                self.state = False


@final
class MultiSwitcher:
    def __init__(self,         app: hass.Hass, targets: list[str]) -> None:
        self.app = app
        self.targets: list[Switcher] = [
            self.__make_switcher(app, target) for target in targets
        ]

    @staticmethod
    def __make_switcher(app: hass.Hass, target: str) -> Switcher:
        auto_switch = app.get_app(target)
        assert isinstance(auto_switch, AutoSwitch)
        return Switcher(auto_switch)

    def init(self, value: bool) -> None:
        for target in self.targets:
            if value:
                target.turn_on()
            elif target.auto_switch.reentrant:
                target.turn_off()

    def deinit(self) -> None:
        for target in self.targets:
            if target.auto_switch.reentrant:
                target.turn_off()

    def turn_on(self) -> None:
        for target in self.targets:
            target.turn_on()

    def turn_off(self) -> None:
        for target in self.targets:
            target.turn_off()
