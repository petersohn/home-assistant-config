from __future__ import annotations
import os
import shutil
import subprocess
import time
from typing import Any

from appdaemon_integration_test.helpers.home_assistant import create_home_assistant_configuration
from appdaemon_integration_test.helpers.app_daemon import (
    create_appdaemon_configuration,
    create_appdaemon_apps_config,
)

import pytest

COMPOSE_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "docker", "compose.yml")
)

HASS_PORT = 18000
APPDAEMON_PORT = 18001


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-f", COMPOSE_FILE, *args]


@pytest.fixture(scope="session")
def home_assistant(clear_output_dir: Any, base_output_directory: str) -> Any:
    hass_path = os.path.join(base_output_directory, "hass")
    shutil.rmtree(hass_path, ignore_errors=True)
    create_home_assistant_configuration(hass_path, 8123)
    # Copy auth file
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "hass")
    os.makedirs(os.path.join(hass_path, ".storage"), exist_ok=True)
    shutil.copy(
        os.path.join(config_dir, "auth"),
        os.path.join(hass_path, ".storage", "auth"),
    )
    subprocess.run(_compose("up", "-d", "hass"), check=True)
    # Wait for HASS to start
    import requests
    from appdaemon_integration_test.helpers.hass_client import HASS_TOKEN
    headers = {"Authorization": f"Bearer {HASS_TOKEN}"}
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{HASS_PORT}/api/", headers=headers)
            if r.status_code == 200 and r.json().get("message") == "API running.":
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        raise RuntimeError("Home Assistant failed to start")
    yield {"host": f"127.0.0.1:{HASS_PORT}", "port": HASS_PORT}
    subprocess.run(_compose("stop", "hass"), check=True)


@pytest.fixture(scope="session")
def appdaemon(home_assistant: Any, base_output_directory: str) -> Any:
    appdaemon_dir = os.path.join(base_output_directory, "appdaemon")
    os.makedirs(appdaemon_dir, exist_ok=True)
    create_appdaemon_configuration(appdaemon_dir, "hass:8123", APPDAEMON_PORT)
    create_appdaemon_apps_config(appdaemon_dir, "TestApp")
    subprocess.run(_compose("up", "-d", "appdaemon"), check=True)
    # Wait for AppDaemon to start
    import requests
    test_arg = "This is a test"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.post(
                f"http://127.0.0.1:{APPDAEMON_PORT}/api/appdaemon/TestApp",
                json={"function": "test", "result_type": None, "arg_types": [], "kwarg_types": {}, "args": [test_arg], "kwargs": {}},
            )
            if r.status_code == 200 and r.json() == test_arg:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError("AppDaemon failed to start")
    yield {"host": f"127.0.0.1:{APPDAEMON_PORT}", "dir": appdaemon_dir}
    subprocess.run(_compose("stop", "appdaemon"), check=True)