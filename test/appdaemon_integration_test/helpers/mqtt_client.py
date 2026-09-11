from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

TOPIC_PREFIX = "home/test"

# Sensors configured in the HASS test config with a value_template reading
# value_json.state. Every publish to these must be a JSON body, even when
# the caller passes no attributes.
JSON_TEMPLATE_SENSORS: frozenset[str] = frozenset({"test_sensor1", "test_sensor2"})


class MqttClient:
    """Publishes test entity states and emulates MQTT switch devices.

    Publish path mirrors a real device: retained state topic updates.
    The emulator echoes command topics to state topics so MQTT switch
    entities confirm state like a Tasmota-style device would.
    """

    _client: mqtt.Client
    _published_topics: set[str]
    _logger: logging.Logger
    _emulate: bool

    def __init__(self, host_port: str, *, emulate_devices: bool = True) -> None:
        self._published_topics = set()
        self._logger = logging.getLogger("MqttClient")
        self._emulate = emulate_devices
        host, port = host_port.rsplit(":", 1)
        self._client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(host, int(port))
        self._client.loop_start()

    def __enter__(self) -> "MqttClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.cleanup_retained()
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(
        self, _client: Any, _userdata: Any, _flags: Any, rc: Any, *_extra: Any
    ) -> None:
        if self._emulate:
            self._client.subscribe(f"{TOPIC_PREFIX}/+/command")

    def _on_message(self, _client: Any, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        if not message.topic.endswith("/command"):
            self._logger.warning(
                "ignoring non-command message on %s", message.topic
            )
            return
        state_topic = message.topic[: -len("/command")] + "/state"
        self._logger.info("echo %s -> %s", message.payload, state_topic)
        # Publish without wait_for_publish: this runs on the paho network
        # thread, and blocking here would deadlock the PUBACK handling (the
        # command echo would never be delivered). The network loop sends the
        # message as soon as this callback returns.
        self._client.publish(state_topic, message.payload, retain=True, qos=1)
        self._published_topics.add(state_topic)

    def _publish(self, topic: str, payload: object, *, retain: bool) -> None:
        info = self._client.publish(topic, str(payload), retain=retain, qos=1)
        info.wait_for_publish(timeout=5)
        if retain:
            self._published_topics.add(topic)

    def publish_state(
        self, name: str, payload: object, *, retain: bool = True, attributes: dict[str, object] | None = None
    ) -> None:
        if attributes or name in JSON_TEMPLATE_SENSORS:
            body = json.dumps({"state": payload, **(attributes or {})})
        else:
            body = str(payload)
        self._publish(f"{TOPIC_PREFIX}/{name}/state", body, retain=retain)

    def set_switch_state(self, name: str, on: bool) -> None:
        self.publish_state(name, "on" if on else "off")

    def cleanup_retained(self) -> None:
        for topic in self._published_topics:
            self._client.publish(topic, "", retain=True, qos=1).wait_for_publish(timeout=5)
        self._published_topics.clear()