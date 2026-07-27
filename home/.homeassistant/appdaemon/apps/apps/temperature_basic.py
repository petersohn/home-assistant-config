from __future__ import annotations
import hass
from hass_common import EntityValue
from typing import Any, TYPE_CHECKING, cast

if TYPE_CHECKING:
    import locker


class TemperatureBasic(hass.Hass):
    sensor_in: str = ""
    sensor_out: str = ""
    target: str = ""
    minimum_out: float = 0.0
    maximum_out: float = 0.0
    target_difference: float = 0.0
    tolerance: float = 1.0
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))

    def initialize(self) -> None:
        self.sensor_in = self.args["sensor_in"]
        self.sensor_out = self.args["sensor_out"]
        self.target = self.args["target"]
        self.minimum_out = float(self.args["minimum_out"])
        self.maximum_out = float(self.args["maximum_out"])
        self.target_difference = float(self.args["target_difference"])
        self.tolerance = float(self.args.get("tolerance", "1"))
        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("TemperatureBasic")

        self.listen_state(self.on_change, self.sensor_in)
        self.listen_state(self.on_change, self.sensor_out)

    def __get_value_or_none(self, entity_id: str) -> float | None:
        value = self.get_state(entity_id)
        assert isinstance(value, str)
        if (
            value == "unavailable"
            or value == "unknown"
            or value == ""
        ):
            self.log(
                "Cannot evaluate {}: value is {}".format(entity_id, repr(value))
            )
            return None
        return float(value)

    def __get_value(self) -> bool | None:
        value_out = self.__get_value_or_none(self.sensor_out)
        if value_out is None:
            return None
        value_in = self.__get_value_or_none(self.sensor_in)
        if value_in is None:
            return None
        assert value_in is not None

        if value_out < self.minimum_out:
            return False
        if value_out >= self.maximum_out:
            return True
        diff = value_out - value_in
        current_value = self.get_state(self.target)
        if current_value == "on":
            return diff >= self.target_difference - self.tolerance
        else:
            return diff >= self.target_difference + self.tolerance

    def on_change(
        self,
        entity: str,
        attribute: str | None,
        old: EntityValue,
        new: EntityValue,
        **kwargs: Any,
    ) -> None:
        with self.mutex.lock("on_change"):
            value = self.__get_value()
            if value is None:
                return
            if value:
                self.turn_on(self.target)
            else:
                self.turn_off(self.target)
