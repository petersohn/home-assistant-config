from __future__ import annotations
import datetime as dt
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Literal, Protocol, overload


TimerCallback = Callable[[dict[str, Any]], Any]


class StateCallback(Protocol):
    def __call__(
        self,
        entity: str,
        attribute: str,
        old: Any,
        new: Any,
        **kwargs: Any,
    ) -> None: ...


class ADAPI:
    AD: Any
    config: dict[str, Any]
    args: dict[str, Any]
    name: str
    namespace: str
    logger: Any
    err: Any
    entities: Any

    def log(
        self,
        msg: str,
        *args: object,
        level: str | int = "INFO",
        log: str | None = None,
        ascii_encode: bool | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: Any,
    ) -> None: ...

    def error(
        self,
        msg: str,
        *args: object,
        level: str | int = "ERROR",
        log: str | None = None,
        ascii_encode: bool | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
        **kwargs: Any,
    ) -> None: ...

    def get_app(self, name: str) -> "ADAPI": ...

    def listen_state(
        self,
        callback: Callable[..., Any],
        entity_id: str | Iterable[str] | None = None,
        namespace: str | None = None,
        new: str | Callable[[Any], bool] | None = None,
        old: str | Callable[[Any], bool] | None = None,
        duration: str | int | float | None = None,
        attribute: str | None = None,
        timeout: str | int | float | None = None,
        immediate: bool = False,
        oneshot: bool = False,
        pin: bool | None = None,
        pin_thread: int | None = None,
        **kwargs: Any,
    ) -> str: ...

    def cancel_listen_state(
        self,
        handle: str,
        name: str | None = None,
        silent: bool = False,
    ) -> bool: ...

    @overload
    def get_state(
        self,
        entity_id: str | None = None,
        attribute: None = None,
        default: Any | None = None,
        namespace: str | None = None,
        copy: bool = True,
    ) -> Any: ...
    @overload
    def get_state(
        self,
        entity_id: str | None = None,
        attribute: str | Literal["all"] = ...,
        default: Any | None = None,
        namespace: str | None = None,
        copy: bool = True,
    ) -> dict[str, Any] | None: ...

    def set_state(
        self,
        entity_id: str,
        state: Any | None = None,
        namespace: str | None = None,
        attributes: dict[str, Any] | None = None,
        replace: bool = True,
        check_existence: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def call_service(
        self,
        service: str,
        namespace: str | None = None,
        timeout: str | int | float | None = -1,
        callback: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> Any: ...

    def run_in(
        self,
        callback: TimerCallback,
        delay: str | int | float | dt.timedelta,
        *args: object,
        random_start: str | int | float | dt.timedelta | None = None,
        random_end: str | int | float | dt.timedelta | None = None,
        **kwargs: Any,
    ) -> str: ...

    def run_daily(
        self,
        callback: TimerCallback,
        start: str | dt.time | dt.datetime | None = None,
        *args: object,
        random_start: str | int | float | dt.timedelta | None = None,
        random_end: str | int | float | dt.timedelta | None = None,
        **kwargs: Any,
    ) -> str: ...

    def run_every(
        self,
        callback: TimerCallback,
        start: str | dt.time | dt.datetime | None = None,
        interval: str | int | float | dt.timedelta = 0,
        *args: object,
        random_start: str | int | float | dt.timedelta | None = None,
        random_end: str | int | float | dt.timedelta | None = None,
        **kwargs: Any,
    ) -> str: ...

    def cancel_timer(self, handle: str, silent: bool = False) -> bool: ...

    def datetime(self, aware: bool = False) -> dt.datetime: ...

    def date(self) -> dt.date: ...

    def register_endpoint(
        self,
        callback: Callable[[Any, dict[str, Any]], Any],
        endpoint: str | None = None,
        **kwargs: Any,
    ) -> str | None: ...