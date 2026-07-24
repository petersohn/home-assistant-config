from __future__ import annotations
import requests  # type: ignore[import-untyped]

HASS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkY2U3MDgwNDIwYmI0Mjg3OWIyYjQ1MjQ4OTQzNjI4YiIsImlhdCI6MTU0NjI1MDYyNiwiZXhwIjoxODYxNjEwNjI2fQ.1YmZVaw3EH2bu0jExU2Q6mIyrD1Qf0cPPJmt877mNC0"


class HassClient:
    def __init__(self, host: str):
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {HASS_TOKEN}"
        self._session.headers["Connection"] = "keep-alive"
        self._host = host

    def get_state(self, entity_id: str) -> str | None:
        r = self._session.get(f"http://{self._host}/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()["state"]

    def get_states(self) -> list:
        r = self._session.get(f"http://{self._host}/api/states")
        r.raise_for_status()
        return r.json()

    def clean_state(self, entity_id: str) -> None:
        if entity_id.startswith("input_boolean.") or entity_id.startswith("switch."):
            self._session.post(
                f"http://{self._host}/api/services/homeassistant/turn_off",
                json={"entity_id": entity_id},
            )
        else:
            self._session.delete(f"http://{self._host}/api/states/{entity_id}")

    def clean_states(self) -> None:
        for entity in self.get_states():
            self.clean_state(entity["entity_id"])

    def clean_history(self) -> None:
        self._session.post(
            f"http://{self._host}/api/services/recorder/purge",
            json={"keep_days": 0},
        )

    def clean_states_and_history(self) -> None:
        self.clean_states()
        self.clean_history()