from __future__ import annotations
import auto_switch
import datetime
import enabler
import expression
import hass
import traceback
from typing import Any, Callable


class Trigger:
    def __init__(
        self,
        app: Any,
        expr: str | None,
        sensor: str | None,
        source_state: str | None,
        target_state: str | None,
        callback: Callable[[bool], None],
    ) -> None:
        self.app = app
        self.callback = callback
        self.expression: expression.ExpressionEvaluator | None = None
        self.saved_state: bool = False
        self.sensor: str | None = None
        self.source_state: str | None = None
        self.target_state: str | None = None
        import locker
        locker_app = app.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("Trigger")
        if expr is not None:
            self.expression = expression.ExpressionEvaluator(
                app, expr, self.on_expression_change
            )
            self.saved_state = self.expression.get() is True
        else:
            self.sensor = sensor
            self.source_state = source_state
            self.target_state = target_state
            self.saved_state = (
                self.source_state is None
                and self.app.get_state(self.sensor) == self.target_state
            )
            self.app.listen_state(
                self.on_state_change, entity_id=self.sensor
            )

    def cleanup(self) -> None:
        if self.expression is not None:
            self.expression.cleanup()

    def is_on(self) -> bool:
        return self.saved_state

    def _on_change(self, new_on: bool) -> None:
        if new_on != self.saved_state:
            self.saved_state = new_on
            self.callback(new_on)

    def on_state_change(
        self,
        entity: str,
        attribute: str | None,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None:
        self.app.log(
            "state changed: {} -> {} target={} -> {}".format(
                old, new, self.source_state, self.target_state
            )
        )
        with self.mutex.lock("on_state_change"):
            self._on_change(
                new == self.target_state
                and (self.source_state is None or old == self.source_state)
            )

    def on_expression_change(self, value: Any) -> None:
        with self.mutex.lock("on_expression_change"):
            self._on_change(value is True)


class Timer:
    def __init__(
        self,
        app: Any,
        time: Any,
        callback: Callable[[], None],
    ) -> None:
        self.app = app
        try:
            self.time: float | str = float(time) * 60
        except ValueError:
            self.time = time  # type: ignore[assignment]
        self.callback = callback
        self.timer: str | None = None
        import locker
        locker_app = app.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("Timer")

    def stop(self) -> None:
        with self.mutex.lock("stop"):
            self.app.log("Stop timer")
            if self.timer is not None:
                self.app.cancel_timer(self.timer)
                self.timer = None

    def start(self) -> None:
        with self.mutex.lock("start"):
            self.app.log("Start timer")
            if type(self.time) is float:
                delay: Any = self.time
            else:
                try:
                    delay = float(self.app.get_state(self.time)) * 60
                except Exception:
                    self.app.error(traceback.format_exc())
                    delay = 0
            self.timer = self.app.run_in(self.on_timeout, delay)

    def is_running(self) -> bool:
        with self.mutex.lock("is_running"):
            return self.timer is not None

    def on_timeout(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("on_timeout"):
            self.timer = None
        self.callback()


class TimerSwitch(hass.Hass):
    def initialize(self) -> None:
        self.trigger = Trigger(
            app=self,
            expr=self.args.get("expr"),
            sensor=self.args.get("sensor"),
            source_state=None,
            target_state=self.args.get("target_state", "on"),
            callback=self.on_change,
        )
        self.targets = auto_switch.MultiSwitcher(self, self.args["targets"])
        enabler_name = self.args.get("enabler")
        if enabler_name is not None:
            import enabler as enabler_mod
            enabler_app = self.get_app(enabler_name)
            assert isinstance(enabler_app, enabler_mod.Enabler)
            self.enabler: enabler.Enabler | None = enabler_app
            self.enabler_id: int | None = enabler_app.add_callback(
                self.on_enabled_changed
            )
        else:
            self.enabler = None
            self.enabler_id = None

        delay = self.args.get("delay")
        if delay is not None:
            self.delay: float | None = float(delay)
        else:
            self.delay = None

        self.delay_timer: str | None = None

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("TimerSwitch")
        with self.mutex.lock("initialize"):
            self.timer = Timer(self, self.args["time"], self.on_timeout)
            self.was_enabled: bool | None = None
            self.is_on: bool = self.trigger.is_on()
            self.run_in(lambda _: self.on_enabled_changed(), 0)

    def terminate(self) -> None:
        self.trigger.cleanup()
        self.targets.turn_off()
        if self.enabler is not None:
            assert self.enabler_id is not None
            self.enabler.remove_callback(self.enabler_id)

    def on_enabled_changed(self) -> None:
        with self.mutex.lock("on_enabled_changed"):
            self._set_enabled()

    def _set_enabled(self) -> None:
        enabled = self.enabler is None or self.enabler.is_enabled()
        if self.was_enabled != enabled:
            self.was_enabled = enabled
            self.log("enabled changed to {}".format(enabled))
            if enabled:
                if self.is_on:
                    self.__start()
            else:
                self.timer.stop()
                self.targets.turn_off()

    def __handle_start(self) -> None:
        if self.enabler is None or self.enabler.is_enabled():
            self.__start()

    def _handle_change(self, value: bool) -> None:
        self.is_on = value
        if value:
            self.__handle_start()
        else:
            self.__handle_stop()

    def on_change(self, value: bool) -> None:
        with self.mutex.lock("on_change"):
            self.log("on_change: {}".format(value))
            if self.delay is None:
                self._handle_change(value)
                return

            if self.delay_timer is not None:
                if value:
                    self.error("Timer should not be running")
                self.log("stop delay")
                self.cancel_timer(self.delay_timer)
                self.delay_timer = None

            if self.is_on == value:
                self.log("no change")
                return

            if value:
                self.delay_timer = self.run_in(self.on_delay, self.delay)
            else:
                self._handle_change(False)

    def on_delay(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("on_delay"):
            if self.delay_timer is not None:
                self._handle_change(True)
                self.delay_timer = None

    def __handle_stop(self) -> None:
        if not self.timer.is_running():
            self.timer.start()

    def __start(self) -> None:
        self.timer.stop()
        self.log("Turn on")
        self.targets.turn_on()

    def on_timeout(self) -> None:
        with self.mutex.lock("on_timeout"):
            self.log("Turn off")
            self.targets.turn_off()


class SequenceElement:
    def __init__(
        self,
        timer: Timer,
        targets: auto_switch.MultiSwitcher | None,
    ) -> None:
        self.timer = timer
        self.targets = targets


class TimerSequence(hass.Hass):
    def initialize(self) -> None:
        self.sequence: list[SequenceElement] = [
            SequenceElement(
                Timer(self, element["time"], self.on_timeout),
                (
                    auto_switch.MultiSwitcher(self, element["targets"])
                    if "targets" in element
                    else None
                ),
            )
            for element in self.args["sequence"]
        ]

        self.trigger = Trigger(
            app=self,
            expr=self.args.get("expr"),
            sensor=self.args.get("sensor"),
            source_state=self.args.get("source_state"),
            target_state=self.args.get("target_state", "on"),
            callback=self.on_change,
        )

        enabler_name = self.args.get("enabler")
        if enabler_name is not None:
            import enabler as enabler_mod
            enabler_app = self.get_app(enabler_name)
            assert isinstance(enabler_app, enabler_mod.Enabler)
            self.enabler: enabler.Enabler | None = enabler_app
            self.enabler_id: int | None = enabler_app.add_callback(
                self.on_enabled_changed
            )
        else:
            self.enabler = None
            self.enabler_id = None

        self.restart_on_trigger: bool = self.args.get(
            "restart_on_trigger", False
        )
        self.rising_edge: bool = self.args.get("rising_edge", True)
        self.falling_edge: bool = self.args.get("falling_edge", False)

        self.current_index: int | None = None
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("TimerSwitch")

    def terminate(self) -> None:
        self.trigger.cleanup()
        for element in self.sequence:
            if element.targets is not None:
                element.targets.turn_off()
        if self.enabler is not None:
            assert self.enabler_id is not None
            self.enabler.remove_callback(self.enabler_id)

    def on_enabled_changed(self) -> None:
        with self.mutex.lock("on_enabled_changed"):
            if self.enabler is not None and not self.enabler.is_enabled():
                self.__stop()

    def on_change(self, value: bool) -> None:
        if not ((self.rising_edge and value) or (self.falling_edge and not value)):
            return

        with self.mutex.lock("on_change"):
            if self.enabler is None or self.enabler.is_enabled():
                if self.restart_on_trigger:
                    if self.current_index == 0:
                        element = self.sequence[0]
                        element.timer.stop()
                        element.timer.start()
                    else:
                        self.__stop()
                if self.current_index is None:
                    self.current_index = 0
                    self.__start()

    def __start(self) -> None:
        if self.current_index is None or self.current_index == len(
            self.sequence
        ):
            self.current_index = None
            return

        element = self.sequence[self.current_index]
        if element.targets is not None:
            element.targets.turn_on()
        element.timer.start()

    def __stop(self) -> None:
        if self.current_index is not None:
            element = self.sequence[self.current_index]
            element.timer.stop()
            if element.targets is not None:
                element.targets.turn_off()
            self.current_index = None

    def on_timeout(self) -> None:
        with self.mutex.lock("on_timeout"):
            if self.current_index is None:
                return
            element = self.sequence[self.current_index]
            if element.targets is not None:
                element.targets.turn_off()
            self.current_index += 1
            self.__start()
