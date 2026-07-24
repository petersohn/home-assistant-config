from __future__ import annotations
import os
import shutil
import subprocess
import time
import pytest
from helpers.home_assistant import create_home_assistant_configuration
from helpers.app_daemon import create_appdaemon_configuration
from helpers.process_check import find_processes_matching_cmdline
from helpers.hass_client import HassClient
from helpers.appdaemon_client import AppDaemonClient
from helpers.history_watcher import HistoryWatcher


@pytest.fixture(scope="session")
def base_output_directory():
    return os.path.join(os.path.dirname(__file__), "output")


@pytest.fixture(scope="session")
def global_mutex_graph():
    graph: dict = {}
    yield graph


@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory):
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)


def _check_leftover_process(description: str, pattern: str) -> None:
    matches = find_processes_matching_cmdline(pattern)
    if matches:
        for pid, cmdline in matches:
            print(f"Leftover {description} process PID {pid}: {cmdline}")
        raise RuntimeError(f"Found {len(matches)} {description} process(es) from a previous run")


@pytest.fixture(scope="session")
def home_assistant(base_output_directory):
    port = 18000
    hass_path = os.path.join(base_output_directory, "hass")
    _check_leftover_process("hass", rf"hass .*{hass_path}")
    shutil.rmtree(hass_path, ignore_errors=True)
    create_home_assistant_configuration(hass_path, port)
    # Copy auth file
    import shutil as sh
    config_dir = os.path.join(os.path.dirname(__file__), "config", "hass")
    os.makedirs(os.path.join(hass_path, ".storage"), exist_ok=True)
    sh.copy(os.path.join(config_dir, "auth"), os.path.join(hass_path, ".storage", "auth"))
    proc = subprocess.Popen(
        ["./hass", "--verbose", "--config", hass_path, "--log-file", f"{hass_path}/homeassistant.log"],
        stdout=open(f"{hass_path}/homeassistant.stdout", "w"),
        stderr=open(f"{hass_path}/homeassistant.stderr", "w"),
    )
    # Wait for HASS to start
    import requests
    from helpers.hass_client import HASS_TOKEN
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
def appdaemon(home_assistant, base_output_directory):
    port = home_assistant["port"] + 1
    appdaemon_dir = os.path.join(base_output_directory, "appdaemon")
    os.makedirs(appdaemon_dir, exist_ok=True)
    create_appdaemon_configuration(appdaemon_dir, home_assistant["host"], port)
    from helpers.app_daemon import create_appdaemon_apps_config
    create_appdaemon_apps_config(appdaemon_dir, "TestApp")
    proc = subprocess.Popen(
        ["./appdaemon", "--config", appdaemon_dir],
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
    assert os.path.getsize(f"{appdaemon_dir}/error.log") == 0


@pytest.fixture(scope="session")
def hass_client(home_assistant):
    return HassClient(home_assistant["host"])


@pytest.fixture(scope="session")
def appdaemon_client(appdaemon, global_mutex_graph):
    client = AppDaemonClient(appdaemon["host"], appdaemon["dir"])
    yield client
    client.check_mutex_graph(global_mutex_graph)


@pytest.fixture
def history_watcher(appdaemon_client):
    return HistoryWatcher(appdaemon_client)


@pytest.fixture(autouse=True)
def cleanup_apps(appdaemon_client):
    yield
    appdaemon_client.unload_apps()