from __future__ import annotations
import os
import shutil
import sys
import types
from collections.abc import Iterator
from datetime import time, date, timedelta
from typing import cast

_HERE = os.path.dirname(__file__)
_APP_DIR = os.path.normpath(
    os.path.join(_HERE, "..", "..", "home", ".homeassistant", "appdaemon", "apps")
)
sys.path.insert(0, os.path.join(_HERE, "test_helpers"))
sys.path.insert(1, os.path.join(_APP_DIR, "apps"))
sys.path.insert(2, _APP_DIR)

import pytest
from pytest import FixtureRequest
from mutex_graph import Graph, GraphValue, find_cycle
from appdaemon_unit_test.test_helpers.harness import Harness
from appdaemon_unit_test.test_helpers.timing import Timing


@pytest.fixture(scope="session")
def base_output_directory() -> str:
    return os.path.join(os.path.dirname(__file__), "output")


@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory: str) -> None:
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)


@pytest.fixture(scope="module", autouse=True)
def global_mutex_graph() -> Iterator[Graph]:
    graph: Graph = {}
    yield graph
    assert not find_cycle(graph)


@pytest.fixture
def harness(
    request: FixtureRequest,
    base_output_directory: str,
    global_mutex_graph: Graph,
) -> Iterator[Harness]:
    params = getattr(request, "param", {})
    start_date = params.get("start_date", date(2018, 1, 1))
    module = cast(types.ModuleType, request.module)
    module_default_start_time = getattr(
        module, "_default_start_time", time(1, 0, 0)
    )
    start_time = params.get("start_time", module_default_start_time)
    interval = params.get("interval", timedelta(seconds=10))
    node = cast(pytest.Item, request.node)
    safe_name = node.name.replace("[", "_").replace("]", "")
    log_dir = os.path.join(base_output_directory, "logs", module.__name__)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{safe_name}.log")
    h = Harness(
        start_date, start_time, interval, log_path,
        cast(dict[str, GraphValue], global_mutex_graph),
    )
    yield h
    h.cleanup()


@pytest.fixture
def timing(harness: Harness) -> Timing:
    return Timing(harness)