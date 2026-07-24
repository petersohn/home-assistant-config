from __future__ import annotations
from datetime import datetime, timedelta, time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import Harness


class Timing:
    def __init__(self, harness: Harness) -> None:
        self._h = harness

    def state_should_change_at(self, entity: str, value: Any, target_time: time | timedelta) -> None:
        target = self._h.date_from_time(target_time, future=True)
        self.state_should_change_at_datetime(entity, value, target)

    def state_should_change_at_datetime(self, entity: str, value: Any, target: datetime) -> None:
        deadline = target - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_until(entity, deadline)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_change_in(self, entity: str, value: Any, duration: timedelta) -> None:
        timeout = duration - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_for(entity, timeout)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_not_change_for(self, entity: str, duration: timedelta) -> None:
        old = self._h.get_state(entity)
        before = self._h.datetime
        self._h.wait_for_state_change(entity, timeout=duration)
        assert self._h.get_state(entity) == old
        assert self._h.datetime - before == duration

    def state_should_not_change_until(self, entity: str, target: datetime | time | timedelta) -> None:
        if not isinstance(target, datetime):
            target = self._h.date_from_time(target, future=True)
        old = self._h.get_state(entity)
        self._h.wait_for_state_change(entity, deadline_datetime=target)
        assert self._h.get_state(entity) == old
        assert self._h.datetime == target