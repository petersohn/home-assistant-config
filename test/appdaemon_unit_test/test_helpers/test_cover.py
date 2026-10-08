from __future__ import annotations
from appdaemon_unit_test.test_helpers.hass import Hass
from typing import Callable, override


class TestCover(Hass):
    def __init__(self) -> None:
        super(TestCover, self).__init__()
        self.entity: str = ""
        self.available_entity: str = ""
        self.position_entity: str = ""
        self.position: int = 0
        self.target: int | None = None
        self.process_id: str | None = None
        self.blocked: bool = False
        self.command_count: int = 0
        self.settle_delay: int = 0

    @override
    def initialize(self) -> None:
        entity = self.args["entity"]
        available_entity = self.args["available_entity"]
        position_entity = self.args["position_entity"]
        assert isinstance(entity, str)
        assert isinstance(available_entity, str)
        assert isinstance(position_entity, str)
        self.entity = entity
        self.available_entity = available_entity
        self.position_entity = position_entity
        self.blocked = bool(self.args.get("blocked", False))
        # Optional delay (simulated seconds) before each commanded move
        # completes. With the default 0 the settle lands in the same
        # harness step as the command, so a whole stop-short retry chain
        # plays out atomically inside one step. With a delay > 0 the
        # settle lands in a later step, pausing the chain between
        # stops — needed to exercise mid-sequence behaviour (a value
        # change or an unblock landing between two consecutive short
        # stops).
        settle_delay = self.args.get("settle_delay", 0)
        assert isinstance(settle_delay, int)
        self.settle_delay = settle_delay
        # Simulates a cover that gets stuck partway. Used to exercise
        # the repeated "Stopped at X, force resetting" logic of
        # CoverController and its attempt cap. When blocked, each
        # accepted command moves the position halfway toward the
        # target, then stops short of it (position != target with no
        # movement state), so the controller repeatedly observes a
        # stuck cover.
        self.set_state(self.entity, "unknown")
        self.process_id = None
        self.position = 0
        self.target = None
        self.command_count = 0
        self._register_service(
            "cover/set_cover_position",
            self.entity,
            lambda args: self.__do_set_position(args),
        )
        self._register_service(
            "cover/open_cover",
            self.entity,
            lambda args: self.set_position(100),
        )
        self._register_service(
            "cover/close_cover",
            self.entity,
            lambda args: self.set_position(0),
        )
        _ = self.listen_state(
            lambda *_: self.__set_availability(),  # pyright: ignore[reportUnknownLambdaType,reportUnknownArgumentType]
            self.available_entity,
        )

    def get_command_count(self) -> int:
        return self.command_count

    def set_blocked(self, value: bool) -> None:
        """Toggle the stuck-cover behaviour at runtime.

        Used to arrange a clean arrival first, then repeated short stops
        in the same test without recreating the app.
        """
        self.log(f"Blocked={value}")
        self.blocked = value

    def __do_set_position(self, args: dict[str, object]) -> None:
        position = args["position"]
        assert isinstance(position, int)
        self.set_position(position)

    def set_position(self, value: int) -> None:
        self.log(f"Set position to {value}")
        self.command_count += 1
        if not self.is_available():
            return
        self.target = value
        self.__set_state()
        self.__do_deferred(lambda: self.__set_position())

    def __set_position(self) -> None:
        if self.target is None:
            return
        if self.blocked:
            # Stuck cover: move halfway toward the target then stop,
            # never reaching it. The target is cleared and the state
            # recomputed so the controller observes a moving-to-idle
            # transition with position != target.
            halfway = (self.position + self.target) // 2
            self.position = halfway
            self.target = None
            self.__set_state()
            return
        self.position = self.target
        self.target = None
        self.__set_state()

    def __do_deferred(self, callback: Callable[[], None]) -> None:
        if self.process_id is not None:
            self.cancel_timer(self.process_id)
        self.process_id = self.run_in(
            lambda _: self.__call_callback(callback), self.settle_delay
        )

    def __call_callback(self, callback: Callable[[], None]) -> None:
        self.process_id = None
        callback()

    def __set_state(self) -> None:
        state = "unknown"
        is_available = self.is_available()
        if not is_available:
            state = "unavailable"
        elif self.target is None:
            state = "open" if self.position != 0 else "closed"
        else:
            state = "opening" if self.target > self.position else "closing"

        attributes: dict[str, str] = {}
        if is_available:
            attributes["current_position"] = str(self.position)
            self.set_state(self.position_entity, str(self.position))

        self.log(f"State={state} position={self.position}")
        self.set_state(self.entity, state, attributes)

    def __set_availability(self) -> None:
        if not self.is_available():
            self.target = None
        self.__set_state()

    def is_available(self) -> bool:
        return self.get_state(self.available_entity) == "on"
