from __future__ import annotations
from typing import Protocol, runtime_checkable
from collections.abc import Callable
import datetime


@runtime_checkable
class CallbackProvider(Protocol):
    def add_callback(self, func: Callable[[], None]) -> int: ...
    def remove_callback(self, id: int) -> None: ...


@runtime_checkable
class EnablerProvider(Protocol):
    def is_enabled(self) -> bool: ...


@runtime_checkable
class ChangeTrackerProvider(Protocol):
    def last_changed(self) -> datetime.datetime | None: ...
    def last_updated(self) -> datetime.datetime | None: ...