from __future__ import annotations
from datetime import datetime, timedelta, time


class Timing:
    def __init__(self, harness):
        self._h = harness

    def state_should_change_at(self, entity: str, value, target_time: time | timedelta):
        target = self._h.date_from_time(target_time, future=True)
        self.state_should_change_at_datetime(entity, value, target)

    def state_should_change_at_datetime(self, entity: str, value, target: datetime):
        deadline = target - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_until(entity, deadline)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_change_in(self, entity: str, value, duration: timedelta):
        timeout = duration - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_for(entity, timeout)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_not_change_for(self, entity: str, duration: timedelta):
        old = self._h.get_state(entity)
        before = self._h.datetime
        self._h.wait_for_state_change(entity, timeout=duration)
        assert self._h.get_state(entity) == old
        assert self._h.datetime - before == duration

    def state_should_not_change_until(self, entity: str, target: datetime | time | timedelta):
        if not isinstance(target, datetime):
            target = self._h.date_from_time(target, future=True)
        old = self._h.get_state(entity)
        self._h.wait_for_state_change(entity, deadline_datetime=target)
        assert self._h.get_state(entity) == old
        assert self._h.datetime == target