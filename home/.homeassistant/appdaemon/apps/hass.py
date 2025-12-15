import appdaemon.plugins.hass.hassapi
from urllib import request
import http.client
import json
import datetime


class Hass(appdaemon.plugins.hass.hassapi.Hass):
    def initialize(self):
        self.do_initialize()
        self.is_loaded = True
        self.log("App loaded")

    def terminate(self):
        try:
            self.do_terminate()
        finally:
            self.is_loaded = False

    def do_initialize(self):
        pass

    def do_terminate(self):
        pass

    def _api_request(self, path):
        hass_config = [
            config
            for config in self.config["plugins"].values()
            if config["type"] == "hass"
        ][0]
        url = "{}/api/{}".format(hass_config["ha_url"], path)
        self.log("Calling API: " + url)
        with request.urlopen(
            request.Request(
                url, headers={"Authorization": "Bearer " + hass_config["token"]}
            )
        ) as result:
            if result.status >= 300:
                raise http.client.HTTPException(result.reason)
            return json.loads(result.read().decode())

    def load_history(self, entity_id, max_interval):
        now = datetime.datetime.now()
        begin_timestamp = (now - max_interval).strftime("%Y-%m-%dT%H:%M:%S")
        end_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
        path = "history/period/{}?filter_entity_id={}&end_time={}".format(
            begin_timestamp, entity_id, end_timestamp
        )
        return self._api_request(path)

    def load_states(self, entity_id):
        return self._api_request("states/{}".format(entity_id))
