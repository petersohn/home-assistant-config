from __future__ import annotations

from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.hass_client import HassClient
from appdaemon_integration_test.helpers.mqtt_client import MqttClient


def test_smoke_sensor_via_mqtt(
    mqtt_client: MqttClient,
    hass_client: HassClient,
    appdaemon_client: AppDaemonClient,
) -> None:
    mqtt_client.publish_state("smoke_sensor", 42)
    appdaemon_client.wait_for_state("sensor.smoke_sensor", 42)
    assert hass_client.get_state("sensor.smoke_sensor") == "42"