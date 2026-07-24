from __future__ import annotations
import time
from typing import Any


class HistoryWatcher:
    def __init__(self, appdaemon_client: Any):
        self._ad = appdaemon_client

    def get_history(self) -> list:
        return self._ad.call_on_app("history_watcher", "get_state_history")

    def check_history(self, *expected: Any) -> None:
        expected_pairs = [[expected[i], expected[i + 1]] for i in range(0, len(expected), 2)]
        actual = self.get_history()
        assert actual == expected_pairs

    def wait_for_history(self, *expected: Any) -> None:
        expected_pairs = [[expected[i], expected[i + 1]] for i in range(0, len(expected), 2)]
        deadline = time.time() + 30
        while time.time() < deadline:
            if self._ad.call_on_app("history_watcher", "has_history", expected_pairs):
                return
            time.sleep(0.2)
        assert self._ad.call_on_app("history_watcher", "has_history", expected_pairs)