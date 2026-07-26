from __future__ import annotations
import os
import shutil
import sys
from typing import Any, Iterator

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)

import pytest
from appdaemon_integration_test.helpers.hass_client import HassClient
from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.history_watcher import HistoryWatcher
from appdaemon_integration_test.helpers.error_log import ErrorLogChecker
from appdaemon_integration_test.helpers.start_stop import home_assistant, appdaemon


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
def appdaemon_client(appdaemon: Any, global_mutex_graph: dict[str, Any]) -> Any:
    client = AppDaemonClient(appdaemon["host"], appdaemon["dir"])
    yield client
    client.check_mutex_graph(global_mutex_graph)


@pytest.fixture(scope="session")
def error_log_checker(appdaemon: Any) -> ErrorLogChecker:
    return ErrorLogChecker(os.path.join(appdaemon["dir"], "error.log"))


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