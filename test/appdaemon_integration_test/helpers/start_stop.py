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
from appdaemon_integration_test.helpers.process_check import find_processes_matching_cmdline

import pytest


def _check_leftover_process(description: str, pattern: str) -> None:
    matches = find_processes_matching_cmdline(pattern)
    if matches:
        for pid, cmdline in matches:
            print(f"Leftover {description} process PID {pid}: {cmdline}")
        raise RuntimeError(f"Found {len(matches)} {description} process(es) from a previous run")


@pytest.fixture(scope="session")
def home_assistant(clear_output_dir: Any, base_output_directory: str) -> Any:
    port = 18000
    hass_path = os.path.join(base_output_directory, "hass")
    _check_leftover_process("hass", rf"hass .*{hass_path}")
    shutil.rmtree(hass_path, ignore_errors=True)
    create_home_assistant_configuration(hass_path, port)
    # Copy auth file
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "hass")
    os.makedirs(os.path.join(hass_path, ".storage"), exist_ok=True)
    shutil.copy(
        os.path.join(config_dir, "auth"),
        os.path.join(hass_path, ".storage", "auth"),
    )
    hass_bin = os.path.join(os.path.dirname(__file__), "..", "hass")
    proc = subprocess.Popen(
        [hass_bin, "--verbose", "--config", hass_path, "--log-file", f"{hass_path}/homeassistant.log"],
        stdout=open(f"{hass_path}/homeassistant.stdout", "w"),
        stderr=open(f"{hass_path}/homeassistant.stderr", "w"),
    )
    # Wait for HASS to start
    import requests
    from appdaemon_integration_test.helpers.hass_client import HASS_TOKEN
    headers = {"Authorization": f"Bearer {HASS_TOKEN}"}
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/api/", headers=headers)
            if r.status_code == 200 and r.json().get("message") == "API running.":
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        raise RuntimeError("Home Assistant failed to start")
    yield {"process": proc, "host": f"127.0.0.1:{port}", "port": port}
    proc.terminate()
    proc.wait(timeout=30)
    assert proc.poll() is not None


@pytest.fixture(scope="session")
def appdaemon(home_assistant: Any, base_output_directory: str) -> Any:
    port = home_assistant["port"] + 1
    appdaemon_dir = os.path.join(base_output_directory, "appdaemon")
    os.makedirs(appdaemon_dir, exist_ok=True)
    create_appdaemon_configuration(appdaemon_dir, home_assistant["host"], port)
    create_appdaemon_apps_config(appdaemon_dir, "TestApp")
    appdaemon_bin = os.path.join(os.path.dirname(__file__), "..", "appdaemon")
    proc = subprocess.Popen(
        [appdaemon_bin, "--config", appdaemon_dir],
        stdout=open(f"{appdaemon_dir}/appdaemon.stdout", "w"),
        stderr=open(f"{appdaemon_dir}/appdaemon.stderr", "w"),
    )
    # Wait for AppDaemon to start
    import requests
    test_arg = "This is a test"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.post(
                f"http://127.0.0.1:{port}/api/appdaemon/TestApp",
                json={"function": "test", "result_type": None, "arg_types": [], "kwarg_types": {}, "args": [test_arg], "kwargs": {}},
            )
            if r.status_code == 200 and r.json() == test_arg:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError("AppDaemon failed to start")
    yield {"process": proc, "host": f"127.0.0.1:{port}", "dir": appdaemon_dir}
    proc.terminate()
    proc.wait(timeout=10)
    assert proc.poll() is not None
    assert os.path.getsize(f"{appdaemon_dir}/appdaemon.stderr") == 0