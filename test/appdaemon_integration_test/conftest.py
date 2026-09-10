from __future__ import annotations
import os
import shutil
import sys
from typing import Any
from collections.abc import Iterator

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)

import pytest
import time
import requests
from appdaemon_integration_test.helpers.hass_client import HassClient, HASS_TOKEN
from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.history_watcher import HistoryWatcher
from appdaemon_integration_test.helpers.error_log import ErrorLogChecker
from appdaemon_integration_test.helpers.mqtt_client import MqttClient
# Registers the home_assistant and appdaemon session-scoped fixtures. pytest
# only auto-loads conftest.py on the ancestor chain of test files; helpers/ is
# a sibling of integration_tests/, so the fixtures must be registered as a
# plugin here.
pytest_plugins = ("appdaemon_integration_test.helpers.start_stop",)


@pytest.fixture(scope="session")
def base_output_directory() -> str:
    return os.path.join(os.path.dirname(__file__), "output")


@pytest.fixture(scope="session")
def global_mutex_graph() -> Any:
    graph: dict[str, Any] = {}
    yield graph


@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory: str) -> None:
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)


@pytest.fixture(scope="session")
def hass_client(home_assistant: Any) -> HassClient:
    return HassClient(home_assistant["host"])


@pytest.fixture(scope="session")
def appdaemon_client(
    appdaemon: Any, mqtt_client: MqttClient, global_mutex_graph: dict[str, Any]
) -> Any:
    client = AppDaemonClient(appdaemon["host"], appdaemon["dir"], mqtt_client)
    yield client
    client.check_mutex_graph(global_mutex_graph)


@pytest.fixture(scope="session")
def error_log_checker(appdaemon: Any) -> ErrorLogChecker:
    return ErrorLogChecker(os.path.join(appdaemon["dir"], "error.log"))


@pytest.fixture(scope="session")
def mqtt_client(mosquitto: Any, home_assistant: Any) -> Iterator[MqttClient]:
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {HASS_TOKEN}"
    host = home_assistant["host"]
    # Probe entities from every MQTT platform used by the test config. HASS
    # loads the mqtt integration (and its topic subscriptions) late in
    # startup, well after the HTTP API responds. Publishing a retained probe
    # and waiting for it to appear in HASS guarantees the subscriptions are
    # active before the first test publishes its states.
    with MqttClient(mosquitto["host"]) as client:
        probes = {"sensor.smoke_sensor": "probe", "binary_sensor.start": "on"}
        client.publish_state("smoke_sensor", "probe")
        client.publish_state("start", "on")
        deadline = time.time() + 120
        pending = dict(probes)
        while time.time() < deadline:
            for entity_id, expected in list(pending.items()):
                r = session.get(f"http://{host}/api/states/{entity_id}")
                if r.status_code == 200 and r.json()["state"] == expected:
                    del pending[entity_id]
            if not pending:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError(f"HASS MQTT not ready, missing: {pending}")
        yield client


@pytest.fixture(autouse=True)
def error_log(error_log_checker: ErrorLogChecker) -> Iterator[ErrorLogChecker]:
    """Per-test error.log gate.

    Marks the current end of error.log at test start, then asserts at teardown
    that no unexpected error blocks were written during the test. Tests that
    intentionally trigger an AppDaemon-internal race may wrap the triggering
    call in ``error_log.allow_errors("KeyError")`` to tolerate matching blocks.
    """
    error_log_checker.mark_test_start()
    yield error_log_checker
    error_log_checker.check_no_unexpected_errors()


@pytest.fixture
def history_watcher(appdaemon_client: AppDaemonClient) -> HistoryWatcher:
    return HistoryWatcher(appdaemon_client)


@pytest.fixture(autouse=True)
def cleanup_apps(appdaemon_client: AppDaemonClient) -> Any:
    yield
    appdaemon_client.unload_apps()