from __future__ import annotations
from typing import Any
import requests

from appdaemon_integration_test.helpers.type_util import values_equal

HASS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkY2U3MDgwNDIwYmI0Mjg3OWIyYjQ1MjQ4OTQzNjI4YiIsImlhdCI6MTU0NjI1MDYyNiwiZXhwIjoxODYxNjEwNjI2fQ.1YmZVaw3EH2bu0jExU2Q6mIyrD1Qf0cPPJmt877mNC0"


class HassClient:
    _session: requests.Session
    _host: str

    def __init__(self, host: str) -> None:
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {HASS_TOKEN}"
        self._session.headers["Connection"] = "keep-alive"
        self._host = host

    def get_state(self, entity_id: str) -> str | None:
        r = self._session.get(f"http://{self._host}/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()["state"]

    def get_attributes(self, entity_id: str) -> dict[str, Any]:
        r = self._session.get(f"http://{self._host}/api/states/{entity_id}")
        r.raise_for_status()
        attributes: dict[str, Any] = r.json()["attributes"]
        return attributes

    def wait_for_attributes(
        self, entity_id: str, expected: dict[str, Any], timeout: float = 15.0
    ) -> None:
        import time
        deadline = time.time() + timeout
        last: dict[str, Any] | None = None
        while time.time() < deadline:
            try:
                last = self.get_attributes(entity_id)
            except Exception:
                last = None
            if last is not None and all(
                key in last and values_equal(last[key], value)
                for key, value in expected.items()
            ):
                return
            time.sleep(0.1)
        assert last is not None and all(
            key in last and values_equal(last[key], value)
            for key, value in expected.items()
        ), f"{entity_id}: expected attributes {expected!r}, got {last!r}"

    def get_states(self) -> list[dict[str, Any]]:
        r = self._session.get(f"http://{self._host}/api/states")
        r.raise_for_status()
        return r.json()

    def clean_state(self, entity_id: str) -> None:
        if entity_id.startswith("input_boolean.") or entity_id.startswith("switch."):
            r = self._session.post(
                f"http://{self._host}/api/services/homeassistant/turn_off",
                json={"entity_id": entity_id},
            )
        else:
            r = self._session.delete(f"http://{self._host}/api/states/{entity_id}")
        r.raise_for_status()

    def clean_states(self) -> None:
        for entity in self.get_states():
            self.clean_state(entity["entity_id"])

    def clean_history(self) -> None:
        r = self._session.post(
            f"http://{self._host}/api/services/recorder/purge",
            json={"keep_days": 0},
        )
        r.raise_for_status()

    def clean_states_and_history(self) -> None:
        self.clean_states()
        self.clean_history()

    def get_history_size(self, entity_id: str) -> int:
        from datetime import datetime, timedelta
        begin = (datetime.now() - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        r = self._session.get(
            f"http://{self._host}/api/history/period/{begin}",
            params={"filter_entity_id": entity_id},
        )
        r.raise_for_status()
        content = r.json()
        if not content or not content[0]:
            return 0
        return len(
            [
                row
                for row in content[0]
                if row["state"] not in ("unavailable", "unknown")
            ]
        )

    def wait_for_history_size(
        self, entity_id: str, expected: int, timeout: float = 15.0
    ) -> None:
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.get_history_size(entity_id) == expected:
                return
            time.sleep(0.2)
        assert self.get_history_size(entity_id) == expected

    def wait_for_state(
        self, entity_id: str, expected: object, timeout: float = 15.0
    ) -> None:
        import time
        deadline = time.time() + timeout
        last: object = None
        while time.time() < deadline:
            try:
                last = self.get_state(entity_id)
            except Exception:
                last = None
            if values_equal(last, expected):
                return
            time.sleep(0.1)
        assert values_equal(last, expected), (
            f"{entity_id}: expected {expected!r}, got {last!r}"
        )

    def wait_for_app_state(
        self, entity_id: str, expected: object, timeout: float = 15.0
    ) -> None:
        import time
        deadline = time.time() + timeout
        last: object = None
        while time.time() < deadline:
            time.sleep(0.1)
            try:
                last = self.get_state(entity_id)
            except Exception:
                last = None
            if last == expected:
                return
        assert last == expected, (
            f"{entity_id}: expected {expected!r}, got {last!r}"
        )

    def wait_for_entity_gone(
        self, entity_id: str, timeout: float = 15.0
    ) -> None:
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            if all(
                state["entity_id"] != entity_id
                for state in self.get_states()
            ):
                return
            time.sleep(0.1)
        assert all(
            state["entity_id"] != entity_id for state in self.get_states()
        ), f"{entity_id} still present in HASS"