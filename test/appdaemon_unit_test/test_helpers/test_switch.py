from __future__ import annotations

from typing import override

from appdaemon_unit_test.test_helpers.hass import Hass


class TestSwitch(Hass):
    """Device double for a switch-like entity commanded through
    `homeassistant/turn_on` / `homeassistant/turn_off`.

    Registers handlers for both services on its entity, so every command
    is recorded in the harness service-call log and routed here instead
    of being reflected directly into the state.

    With the `stuck` arg the device ignores commands: the state never
    reflects them (the commands still show up in the service-call log),
    which lets tests observe retry cadences. Without it the double
    reflects each command like a healthy device.

    The `glitch` method simulates a flapping device: it momentarily
    reports an invalid None state and then re-reports its actual
    state."""

    def __init__(self) -> None:
        super(TestSwitch, self).__init__()
        self.entity: str = ""
        self.stuck: bool = False

    @override
    def initialize(self) -> None:
        entity = self.args["entity"]
        assert isinstance(entity, str)
        self.entity = entity
        self.stuck = bool(self.args.get("stuck", False))
        state = self.args.get("state", "off")
        assert isinstance(state, str)
        self.set_state(self.entity, state)
        self._register_service(
            "homeassistant/turn_on", entity, self.__handle_turn_on
        )
        self._register_service(
            "homeassistant/turn_off", entity, self.__handle_turn_off
        )

    def glitch(self) -> None:
        """Report an invalid None state and then re-report the actual
        state, as a glitching device does. Both reports are dispatched
        through the normal state-change machinery, so listeners see a
        None state report followed by the re-report."""
        value = self.get_state(self.entity)
        assert isinstance(value, str)
        self.log(f"Glitch: None report, re-reporting {value}")
        self.set_state(self.entity, None)
        self.set_state(self.entity, value)

    def __handle_turn_on(self, _args: dict[str, object]) -> None:
        if self.stuck:
            self.log("Commanded on; stuck device ignores it")
            return
        self.log("Commanded on; device turns on")
        self.set_state(self.entity, "on")

    def __handle_turn_off(self, _args: dict[str, object]) -> None:
        if self.stuck:
            self.log("Commanded off; stuck device ignores it")
            return
        self.log("Commanded off; device turns off")
        self.set_state(self.entity, "off")