from __future__ import annotations
import appdaemon.plugins.hass.hassapi
import datetime
import http.client
import json
from typing import Any
from urllib import request


# Real appdaemon returns str handles from run_in/cancel_timer/etc., but the
# unit-test mock returns int. Use a union so the apps typecheck against both.
TimerHandle = int | str


class Hass(appdaemon.plugins.hass.hassapi.Hass):
    def cancel_timer(self, handle: TimerHandle) -> None:
        super().cancel_timer(handle)  # type: ignore[arg-type]

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
        now = datetime.datetime.now()
        begin_timestamp = (now - max_interval).strftime("%Y-%m-%dT%H:%M:%S")
        end_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
        path = "history/period/{}?filter_entity_id={}&end_time={}".format(
            begin_timestamp, entity_id, end_timestamp
        )
        return self._api_request(path)

    def load_states(self, entity_id: str) -> dict[str, Any]:
        return self._api_request("states/{}".format(entity_id))
