import hass
from typing import Callable, override


class TestCover(hass.Hass):
    def __init__(self):
        super(TestCover, self).__init__()
        self.entity: str = ""
        self.available_entity: str = ""
        self.position_entity: str = ""
        self.position: int = 0
        self.target: int | None = None
        self.process_id: int | None = None

    @override
    def do_initialize(self) -> None:
        self.entity = self.args["entity"]
        self.available_entity = self.args["available_entity"]
        self.position_entity = self.args["position_entity"]
        self.set_state(self.entity, "unknown")
        self.process_id = None
        self.position = 0
        self.target = None
        self._register_service(
            "cover/set_cover_position",
            self.entity,
            lambda args: self.set_position(args["position"]),
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
            lambda *_: self.__set_availability(),
            self.available_entity,
        )

    def set_position(self, value: int) -> None:
        self.log("Set position to {}".format(value))
        if not self.is_available():
            return
        self.target = value
        self.__set_state()
        self.__do_deferred(lambda: self.__set_position())

    def __set_position(self):
        if self.target is None:
            return
        self.position = self.target
        self.target = None
        self.__set_state()

    def __do_deferred(self, callback: Callable[[], None]) -> None:
        if self.process_id is not None:
            self.cancel_timer(self.process_id)
        self.process_id = self.run_in(
            lambda _: self.__call_callback(callback), 0
        )

    def __call_callback(self, callback: Callable[[], None]) -> None:
        self.process_id = None
        callback()

    def __set_state(self):
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

        self.log("State={} position={}".format(state, self.position))
        self.set_state(self.entity, state, attributes)

    def __set_availability(self):
        if not self.is_available():
            self.target = None
        self.__set_state()

    def is_available(self):
        return self.get_state(self.available_entity) == "on"
