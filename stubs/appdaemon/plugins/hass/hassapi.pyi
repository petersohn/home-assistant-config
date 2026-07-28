from __future__ import annotations
from typing import Any, override

from appdaemon.adapi import ADAPI
from appdaemon.adbase import ADBase


class Hass(ADBase, ADAPI):
    def turn_on(
        self,
        entity_id: str,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def turn_off(
        self,
        entity_id: str,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def select_option(
        self,
        entity_id: str,
        option: str,
        namespace: str | None = None,
    ) -> None: ...

    @override
    def call_service(
        self,
        service: str,
        namespace: str | None = None,
        timeout: str | int | float | None = -1,
        callback: Any | None = None,
        hass_timeout: str | int | float | None = None,
        suppress_log_messages: bool = False,
        return_response: bool = False,
        **kwargs: Any,
    ) -> Any: ...