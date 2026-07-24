from __future__ import annotations
import appdaemon.plugins.hass.hassapi
import datetime
import http.client
import json
from typing import Any, Callable
from urllib import request


EntityValue = str | dict[str, Any] | None


class Hass(appdaemon.plugins.hass.hassapi.Hass):
    def add_callback(self, func: Callable[[], None]) -> int:
        raise NotImplementedError

    def remove_callback(self, id: int) -> None:
        raise NotImplementedError

    def _api_request(self, path: str) -> Any:
        hass_config = [
            config
            for config in self.config["plugins"].values()
            if config["type"] == "hass"
        ][0]
        token = hass_config["token"]
        if hasattr(token, "get_secret_value"):
            token = token.get_secret_value()
        url = "{}/api/{}".format(hass_config["ha_url"], path)
        self.log("Calling API: " + url)
        with request.urlopen(
            request.Request(
                url, headers={"Authorization": "Bearer " + token}
            )
        ) as result:
            if result.status >= 300:
                raise http.client.HTTPException(result.reason)
            return json.loads(result.read().decode())

    def load_history(
        self, entity_id: str, max_interval: datetime.timedelta
    ) -> Any:
        now = datetime.datetime.now(datetime.timezone.utc)
        begin_timestamp = (now - max_interval).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        path = "history/period/{}?filter_entity_id={}&end_time={}".format(
            begin_timestamp, entity_id, end_timestamp
        )
        return self._api_request(path)

    def load_states(self, entity_id: str) -> dict[str, Any]:
        return self._api_request("states/{}".format(entity_id))
