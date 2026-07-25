from __future__ import annotations
import hass


class Dummy(hass.Hass):
    def initialize(self) -> None:
        pass
