# Migrate Tests to pytest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Robot Framework with pytest for all AppDaemon tests, keeping the current project structure and shell-script-based integration test wrapping.

**Architecture:** In-place replacement of `.robot` files with `test_*.py`. Unit tests use a `Harness` fixture wrapping the mock `AppManager`, a `Timing` helper object for composite timing assertions, and bare `assert` for state checks. Integration tests use `HassClient` + `AppDaemonClient` + `HistoryWatcher` classes with `requests` for HTTP, spawned via existing `./hass` and `./appdaemon` shell scripts.

**Tech Stack:** pytest, requests, pyyaml, python-dateutil, psutil, datetime

## Global Constraints

- Time constants are native `datetime` types: `timedelta(minutes=1)`, `time(1, 0, 0)`, `datetime(2018, 1, 1)`, `date(2018, 1, 1)`. No string-parsing time helpers.
- Bare `assert` for all state checks (pytest AST rewriting shows actual vs expected).
- `@pytest.mark.parametrize` for all templated/parametrized tests.
- No `run-test` scripts; invoke `pytest` directly.
- Keep `./hass` and `./appdaemon` shell scripts unchanged.
- snake_case directory names; `libraries/` → `helpers/`; no "Suite" in dir names; venv env name `robot` → `test`.
- Log paths use `request.module.__name__` + sanitized `request.node.name` (no `request.node.nodeid`).

---

## Task 1: Rename directories and update path references

**Files:**
- Rename: `test/AppDaemonUnitTest/` → `test/appdaemon_unit_test/`
- Rename: `test/AppDaemonIntegrationTest/` → `test/appdaemon_integration_test/`
- Rename: `test/AppDaemonUnitTest/00InfrastructureSuite/` → `test/appdaemon_unit_test/00_infrastructure_tests/`
- Rename: `test/AppDaemonUnitTest/AppDaemonSuite/` → `test/appdaemon_unit_test/appdaemon_tests/`
- Rename: `test/AppDaemonIntegrationTest/AppDaemonSuite/` → `test/appdaemon_integration_test/appdaemon_tests/`
- Rename: `test/AppDaemonUnitTest/libraries/` → `test/appdaemon_unit_test/helpers/`
- Rename: `test/AppDaemonIntegrationTest/libraries/` → `test/appdaemon_integration_test/helpers/`
- Rename: `test/dependencies/robot/` → `test/dependencies/test/`
- Modify: `test/setup_virtualenv.sh`
- Modify: `bin/mypy`
- Modify: `test/AppDaemonIntegrationTest/libraries/directories.py` (moves to `helpers/`)

**Interfaces:**
- Consumes: nothing
- Produces: new directory structure that all subsequent tasks use

- [ ] **Step 1: Rename directories with git mv**

```bash
cd /home/petersohn/workspace/home-assistant-config
git mv test/AppDaemonUnitTest test/appdaemon_unit_test
git mv test/AppDaemonIntegrationTest test/appdaemon_integration_test
git mv test/appdaemon_unit_test/00InfrastructureSuite test/appdaemon_unit_test/00_infrastructure_tests
git mv test/appdaemon_unit_test/AppDaemonSuite test/appdaemon_unit_test/appdaemon_tests
git mv test/appdaemon_integration_test/AppDaemonSuite test/appdaemon_integration_test/appdaemon_tests
git mv test/appdaemon_unit_test/libraries test/appdaemon_unit_test/helpers
git mv test/appdaemon_integration_test/libraries test/appdaemon_integration_test/helpers
git mv test/dependencies/robot test/dependencies/test
```

- [ ] **Step 2: Update setup_virtualenv.sh**

In `test/setup_virtualenv.sh`, replace:
- `robot)` → `test)` (line 43)
- `robot=1` → `test=1` (line 37)
- `setup_sync python3.12 .venv dependencies/robot` → `setup_sync python3.12 .venv dependencies/test` (line 57)

- [ ] **Step 3: Update bin/mypy**

```bash
#!/usr/bin/env bash
set -e
exec "$(cd "$(dirname "$0")/.." && pwd)/test/appdaemon_integration_test/.appdaemon/bin/mypy" "$@"
```

- [ ] **Step 4: Verify directory structure**

Run: `ls -la test/appdaemon_unit_test/ test/appdaemon_integration_test/ test/dependencies/`
Expected: all renamed dirs present.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: rename test directories to snake_case, libraries to helpers"
```

---

## Task 2: Update dependencies

**Files:**
- Modify: `test/dependencies/test/pyproject.toml`
- Regenerate: `test/dependencies/test/uv.lock`
- Modify: `test/docker/Dockerfile`

**Interfaces:**
- Consumes: Task 1 (renamed `test/dependencies/test/`)
- Produces: pytest + requests available in the test venv

- [ ] **Step 1: Update pyproject.toml**

Write `test/dependencies/test/pyproject.toml`:

```toml
[project]
name = "test"
version = "0.1.0"
description = "Test runner for home-assistant-config"
requires-python = ">=3.12,<3.13"
dependencies = [
    "pytest",
    "requests",
    "pyyaml",
    "python-dateutil",
    "psutil",
]
```

- [ ] **Step 2: Regenerate uv.lock**

```bash
cd test/dependencies/test
uv lock
cd ../../..
```

- [ ] **Step 3: Update Dockerfile**

In `test/docker/Dockerfile`, replace lines 14-18:

```dockerfile
# Test env (Python 3.12 venv)
RUN uv venv /test --python 3.12
WORKDIR /deps/test
COPY --from=deps test/dependencies/test/ ./
RUN VIRTUAL_ENV=/test uv sync --frozen --no-install-project --active
```

- [ ] **Step 4: Reinstall venv and verify pytest is available**

```bash
./test/setup_virtualenv.sh test
source test/.venv/bin/activate
pytest --version
```

Expected: `pytest 8.x.x`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "deps: replace robotframework with pytest+requests"
```

---

## Task 3: Remove Robot dependency from helper modules

**Files:**
- Modify: `test/appdaemon_unit_test/helpers/date_time_util.py`
- Modify: `test/appdaemon_unit_test/helpers/history_util.py`
- Modify: `test/appdaemon_unit_test/helpers/config.py`
- Modify: `test/appdaemon_integration_test/helpers/mutex_graph.py`
- Modify: `test/appdaemon_integration_test/config/appdaemon/apps/test_app.py`

**Interfaces:**
- Consumes: Task 2 (pytest venv with python-dateutil)
- Produces: helper modules with no `robot.libraries` imports

- [ ] **Step 1: Rewrite date_time_util.py**

Write `test/appdaemon_unit_test/helpers/date_time_util.py`:

```python
from datetime import datetime, time, timedelta
from dateutil import parser as date_parser


def to_time(input: str) -> time:
    parsed = date_parser.parse(input)
    return parsed.time()


def find_time(start_date: str, new_time: str) -> datetime:
    start_datetime = date_parser.parse(start_date)
    target_time = to_time(new_time)
    result = start_datetime.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=target_time.second,
        microsecond=target_time.microsecond,
    )
    if target_time < start_datetime.time():
        result += timedelta(days=1)
    return result


def add_times(*times: timedelta) -> timedelta:
    return sum(times, timedelta())
```

- [ ] **Step 2: Rewrite history_util.py (unit test)**

Write `test/appdaemon_unit_test/helpers/history_util.py`:

```python
from datetime import datetime
from dateutil import parser as date_parser
from typing import Any


def convert_history_input(args: list[str | int]) -> list[tuple[str, int]]:
    return [
        (_convert_timestamp(args[i]), int(args[i + 1]))
        for i in range(0, len(args), 2)
    ]


def _convert_timestamp(value: str | int | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    parsed = date_parser.parse(str(value))
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def convert_history_output(
    result: list[tuple[datetime | str, float]],
) -> list[tuple[str, float]]:
    return [
        (_convert_timestamp(date), int(value))
        for date, value in result
    ]


def is_expected_history_found(
    converted_input: Any, converted_output: Any
) -> bool:
    return all(i in converted_output for i in converted_input)
```

- [ ] **Step 3: Rewrite config.py (remove print)**

Write `test/appdaemon_unit_test/helpers/config.py`:

```python
from typing import Any
from apps import hass
from datetime import datetime


def extract_from_dictionary(dictionary: Any, key: Any) -> Any:
    return _extract_from_dictionary(dictionary, key)


def _extract_from_dictionary[Key, Value](
    dictionary: dict[Key, Value], key: Key
) -> Value | None:
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]
    return result


def repeat_item[T](item: T, count: int) -> list[T]:
    return [item] * count


def create_app_manager(
    start_datetime: datetime, log_filename: str
) -> hass.AppManager:
    return hass.AppManager(start_datetime, log_filename)
```

- [ ] **Step 4: Remove Robot-specific attributes from integration mutex_graph.py**

In `test/appdaemon_integration_test/helpers/mutex_graph.py`, remove the last 3 lines (lines 89-94):

```python
# Delete these lines:
# setattr(append_graph, "robot_types", None)
# setattr(find_cycle, "robot_types", None)
# setattr(format_graph, "robot_types", None)
```

- [ ] **Step 5: Fix integration test_app.py DateTime import**

In `test/appdaemon_integration_test/config/appdaemon/apps/test_app.py`, replace line 8:

```python
# Before:
from robot.libraries import DateTime
# After:
from datetime import datetime as dt_module
```

Then replace all `DateTime.convert_date(...)` and `DateTime.convert_time(...)` calls. In `convert_output` method (around line 63-67):

```python
# Before:
if isinstance(value, datetime.datetime):
    return DateTime.convert_date(value, result_format="timestamp")
if isinstance(value, datetime.timedelta):
    return DateTime.convert_time(value, result_format="timer")

# After:
if isinstance(value, datetime.datetime):
    return value.isoformat()
if isinstance(value, datetime.timedelta):
    return str(value)
```

- [ ] **Step 6: Run mypy to verify no broken imports**

```bash
bin/mypy
```

Expected: no new errors related to the changed files.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: remove robot.libraries imports from helpers"
```

---

## Task 4: Create unit test conftest and Harness

**Files:**
- Create: `test/conftest.py`
- Create: `test/appdaemon_unit_test/conftest.py`
- Create: `test/appdaemon_unit_test/helpers/timing.py`

**Interfaces:**
- Consumes: Task 1 (renamed dirs), Task 3 (fixed helpers)
- Produces:
  - `harness` fixture (indirect-parametrizable): `Harness` object with methods `step()`, `advance_time(timedelta)`, `advance_time_to(datetime)`, `get_state(entity, attribute=None)`, `set_state(entity, value, **attributes)`, `turn_on(entity)`, `turn_off(entity)`, `create_app(module, class_name, name, **kwargs)`, `get_app(name)`, `schedule_call_in(timedelta, func, *args, **kwargs)`, `schedule_call_at(time, func, *args, **kwargs)`, `schedule_call_at_datetime(datetime, func, *args, **kwargs)`, `call_on_app(app, method, *args, **kwargs)`, `datetime` property, `interval` property, `date_from_time(timedelta, future) -> datetime`, `wait_for_state_change(entity, timeout=None, deadline=None, deadline_datetime=None, old=None, new=None)`
  - `timing` fixture: `Timing` object with methods `state_should_change_at(entity, value, timedelta)`, `state_should_change_in(entity, value, timedelta)`, `state_should_change_at_datetime(entity, value, datetime)`, `state_should_not_change_for(entity, timedelta)`, `state_should_not_change_until(entity, datetime)`
  - `global_mutex_graph` module-scoped fixture (dict, asserts no cycle at teardown)

- [ ] **Step 1: Create test/conftest.py (empty)**

Write `test/conftest.py`:

```python
```

- [ ] **Step 2: Create helpers/timing.py**

Write `test/appdaemon_unit_test/helpers/timing.py`:

```python
from __future__ import annotations
from datetime import datetime, timedelta, time


class Timing:
    def __init__(self, harness):
        self._h = harness

    def state_should_change_at(self, entity: str, value, target_time: time | timedelta):
        target = self._h.date_from_time(target_time, future=True)
        self.state_should_change_at_datetime(entity, value, target)

    def state_should_change_at_datetime(self, entity: str, value, target: datetime):
        deadline = target - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_until(entity, deadline)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_change_in(self, entity: str, value, duration: timedelta):
        timeout = duration - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_for(entity, timeout)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_not_change_for(self, entity: str, duration: timedelta):
        old = self._h.get_state(entity)
        before = self._h.datetime
        self._h.wait_for_state_change(entity, timeout=duration)
        assert self._h.get_state(entity) == old
        assert self._h.datetime - before == duration

    def state_should_not_change_until(self, entity: str, target: datetime):
        old = self._h.get_state(entity)
        self._h.wait_for_state_change(entity, deadline_datetime=target)
        assert self._h.get_state(entity) == old
        assert self._h.datetime == target
```

- [ ] **Step 3: Create conftest.py with Harness class and fixtures**

Write `test/appdaemon_unit_test/conftest.py`:

```python
from __future__ import annotations
import os
import shutil
from datetime import datetime, timedelta, time, date
from typing import Any
import pytest
from helpers.config import create_app_manager
from helpers.timing import Timing
from apps.hass import AppManager, Hass
from apps.mutex_graph import find_cycle, append_graph


class Harness:
    def __init__(
        self,
        start_date: date,
        start_time: time,
        interval: timedelta,
        log_path: str,
        global_mutex_graph: dict,
    ):
        start_datetime = datetime.combine(start_date, start_time)
        self._manager = create_app_manager(start_datetime, log_path)
        self._interval = interval
        self._global_mutex_graph = global_mutex_graph
        self.locker = self.create_app("locker", "Locker", "locker", enable_logging=True)
        self.test_app = self.create_app("test_app", "TestApp", "test_app")

    @property
    def datetime(self) -> datetime:
        return self._manager.datetime()

    @property
    def interval(self) -> timedelta:
        return self._interval

    @property
    def app_manager(self) -> AppManager:
        return self._manager

    def step(self):
        self._manager.step(self._interval)

    def advance_time(self, amount: timedelta):
        self._manager.advance_time(amount, self._interval)

    def advance_time_to(self, target_time: time):
        target = self.date_from_time(target_time, future=True)
        self.advance_time_to_datetime(target)

    def advance_time_to_datetime(self, target: datetime):
        self._manager.advance_time_to(target, self._interval)

    def get_state(self, entity_id: str, attribute: str | None = None):
        return self.test_app.get_state_as(entity_id, attribute=attribute)

    def set_state(self, entity_id: str, value, **attributes):
        self.test_app.set_state(entity_id, value, attributes)

    def turn_on(self, entity_id: str):
        self.set_state(entity_id, "on")

    def turn_off(self, entity_id: str):
        self.set_state(entity_id, "off")

    def create_app(self, module: str, class_name: str, name: str, **kwargs) -> Hass:
        return self._call_and_check(self._manager.create_app, module, class_name, name, **kwargs)

    def get_app(self, name: str) -> Hass | None:
        return self._manager.get_app(name)

    def schedule_call_in(self, delay: timedelta, func_name: str, *args, **kwargs):
        self._call_and_check(self.test_app.schedule_call_in, delay, func_name, *args, **kwargs)

    def schedule_call_at(self, target_time: time, func_name: str, *args, **kwargs):
        target = self.date_from_time(target_time, future=True)
        self._call_and_check(self.test_app.schedule_call_at, target, func_name, *args, **kwargs)

    def schedule_call_at_datetime(self, target: datetime, func_name: str, *args, **kwargs):
        self._call_and_check(self.test_app.schedule_call_at, target, func_name, *args, **kwargs)

    def call_on_app(self, app, method: str, *args, **kwargs):
        return self._call_and_check(self.test_app.call_on_app, app, method, *args, **kwargs)

    def date_from_time(self, time_of_day: time | timedelta, future: bool) -> datetime:
        if isinstance(time_of_day, time):
            td = timedelta(
                hours=time_of_day.hour,
                minutes=time_of_day.minute,
                seconds=time_of_day.second,
                microseconds=time_of_day.microsecond,
            )
        else:
            td = time_of_day
        return self.test_app.get_next_time_of_day(td, future)

    def wait_for_state_change(
        self,
        entity: str,
        timeout: timedelta | None = None,
        deadline: time | timedelta | None = None,
        deadline_datetime: datetime | None = None,
        old: str | None = None,
        new: str | None = None,
    ):
        actual_deadline = deadline_datetime
        if timeout is not None:
            actual_deadline = self.datetime + timeout
        elif deadline is not None:
            actual_deadline = self.date_from_time(deadline, future=True)
        self._manager.wait_for_state_change(entity, actual_deadline, self._interval, old=old, new=new)

    def _call_and_check(self, func, *args, **kwargs):
        result = func(*args, **kwargs)
        self._manager.call_pending_callbacks()
        assert not self._manager.has_error()
        return result

    def cleanup(self):
        mutex_graph = self.locker.get_global_graph()
        append_graph(self._global_mutex_graph, mutex_graph)
        assert not find_cycle(self._global_mutex_graph)
        self._manager.remove_all_apps()
        assert not self._manager.has_error()


@pytest.fixture(scope="session")
def base_output_directory():
    return os.path.join(os.path.dirname(__file__), "output")


@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory):
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)


@pytest.fixture(scope="module", autouse=True)
def global_mutex_graph():
    graph: dict = {}
    yield graph
    assert not find_cycle(graph)


@pytest.fixture
def harness(request, base_output_directory, global_mutex_graph):
    params = getattr(request, "param", {})
    start_date = params.get("start_date", date(2018, 1, 1))
    start_time = params.get("start_time", time(0, 0, 0))
    interval = params.get("interval", timedelta(seconds=10))
    safe_name = request.node.name.replace("[", "_").replace("]", "")
    log_dir = os.path.join(base_output_directory, "logs", request.module.__name__)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{safe_name}.log")
    h = Harness(start_date, start_time, interval, log_path, global_mutex_graph)
    yield h
    h.cleanup()


@pytest.fixture
def timing(harness):
    return Timing(harness)
```

- [ ] **Step 4: Verify pytest can collect (no tests yet, just conftest)**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps:${PWD}/helpers" python -c "from conftest import Harness, Timing; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add pytest conftest and Harness for unit tests"
```

---

## Task 5: Migrate 00_infrastructure_tests

**Files:**
- Create: `test/appdaemon_unit_test/00_infrastructure_tests/test_mutex_graph.py`
- Create: `test/appdaemon_unit_test/00_infrastructure_tests/test_type_util.py`
- Create: `test/appdaemon_unit_test/00_infrastructure_tests/test_date_time_util.py`
- Create: `test/appdaemon_unit_test/00_infrastructure_tests/test_history_util.py`
- Create: `test/appdaemon_unit_test/00_infrastructure_tests/test_test_harness.py`
- Delete: all `*.robot` in `00_infrastructure_tests/`

**Interfaces:**
- Consumes: Task 4 (Harness, timing fixtures)
- Produces: infrastructure tests passing under pytest

- [ ] **Step 1: Write test_mutex_graph.py**

```python
import pytest
from apps.mutex_graph import find_cycle, append_graph


@pytest.mark.parametrize("graph_dict, expected", [
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3')]}, False),
    ({'': {('a', 'e1'), ('b', 'e2')}, 'a': {('b', 'e3')}}, False),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5')]}, False),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('', 'e3')]}, True),
    ({'': {('a', 'e1'), ('b', 'e2')}, 'a': {('', 'e3')}}, True),
    ({'': [('a', 'e1'), ('b', 'e2')], 'b': [('', 'e3')]}, True),
    ({'': [('a', 'e1')], 'a': [('b', 'e2')], 'b': [('', 'e3')]}, True),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5'), ('a', 'e6')]}, True),
    ({'': [('a', 'e1')], 'a': [('a', 'e2')]}, True),
])
def test_find_cycle(graph_dict, expected):
    assert find_cycle(graph_dict) == expected


@pytest.mark.parametrize("expected, g1, g2", [
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': {('a', 'e1'), ('b', 'e2')}},
     {'': {('a', 'e1'), ('b', 'e3')}}),
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': [('a', 'e1'), ('b', 'e2')]},
     {'': [('a', 'e1'), ('b', 'e3')]}),
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': [['a', 'e1'], ['b', 'e2']]},
     {'': [['a', 'e1'], ['b', 'e3']]}),
    ({'': {('a', 'e1'), ('c', 'e3')}, 'a': {('b', 'e2')}, 'c': {('b', 'e4')}},
     {'': {('a', 'e1')}, 'a': {('b', 'e2')}},
     {'': {('c', 'e3')}, 'c': {('b', 'e4')}}),
])
def test_append_graph(expected, g1, g2):
    append_graph(g1, g2)
    assert g1 == expected
```

- [ ] **Step 2: Write test_type_util.py**

```python
from helpers.type_util import extract_from_dictionary, repeat_item


def test_extract_existing_item_from_dictionary():
    d = {"key1": "value1", "key2": "value2"}
    result = extract_from_dictionary(d, "key1")
    assert result == "value1"
    assert d == {"key2": "value2"}


def test_extract_nonexisting_item_from_dictionary():
    d = {"key1": "value1", "key2": "value2"}
    result = extract_from_dictionary(d, "key3")
    assert result is None
    assert d == {"key1": "value1", "key2": "value2"}


def test_repeat_item():
    result = repeat_item("foobar", 3)
    assert result == ["foobar", "foobar", "foobar"]
```

- [ ] **Step 3: Write test_date_time_util.py**

```python
from datetime import datetime
from helpers.date_time_util import to_time, find_time, add_times


def test_to_time():
    result = to_time("10:15:30")
    assert result.hour == 10
    assert result.minute == 15
    assert result.second == 30


def test_find_time_on_same_day():
    result = find_time("2018-01-01 12:00:00", "13:15:30")
    assert result == datetime(2018, 1, 1, 13, 15, 30)


def test_find_time_on_next_day():
    result = find_time("2018-01-01 12:00:00", "10:32:40")
    assert result == datetime(2018, 1, 2, 10, 32, 40)


def test_add_times():
    from datetime import timedelta
    result = add_times(
        timedelta(seconds=10),
        timedelta(minutes=32, seconds=5),
        timedelta(hours=2, minutes=5, seconds=24),
    )
    assert result == timedelta(hours=2, minutes=37, seconds=39)
```

- [ ] **Step 4: Write test_history_util.py**

```python
from datetime import datetime
from helpers.history_util import convert_history_input, convert_history_output


def test_convert_history_input():
    expected = [
        ("2019-01-01 00:00:00", 3),
        ("2019-02-03 01:21:04", 50),
        ("2019-01-10 12:05:00", -1),
    ]
    result = convert_history_input([
        "2019-01-01", 3,
        "20190203T012104", 50,
        "2019-01-10 12:05:00.123", -1,
    ])
    assert result == expected


def test_convert_history_output():
    expected = [
        ("2019-01-01 00:00:00", 3),
        ("2019-02-03 01:21:04", 50),
        ("2019-01-10 12:05:00", -1),
    ]
    result = convert_history_output([
        (datetime(2019, 1, 1), 3.0),
        (datetime(2019, 2, 3, 1, 21, 4), 50.01),
        (datetime(2019, 1, 10, 12, 5, 0, 123000), -1.0),
    ])
    assert result == expected
```

- [ ] **Step 5: Write test_test_harness.py**

This tests the Harness/Timing helpers themselves. Port from `TestHarnessTest.robot`:

```python
from datetime import datetime, timedelta, time
import pytest


@pytest.fixture
def setup_harness(harness):
    """Default harness with test_sensor set."""
    harness.set_state("sensor.test_sensor", "sensor state")
    return harness


def test_start_time(setup_harness):
    assert setup_harness.datetime.time() == time(1, 0, 0)


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0)}], indirect=True)
def test_different_start_time(harness):
    assert harness.datetime.time() == time(21, 30, 0)


def test_set_state(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_set_attribute(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "foobar", a="attr1", b="attr2")
    assert setup_harness.get_state("sensor.test_sensor") == "foobar"
    assert setup_harness.get_state("sensor.test_sensor", attribute="a") == "attr1"
    assert setup_harness.get_state("sensor.test_sensor", attribute="b") == "attr2"


def test_step(setup_harness):
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 10)
    setup_harness.step()
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_advance_time(setup_harness):
    setup_harness.advance_time(timedelta(minutes=2))
    assert setup_harness.datetime.time() == time(1, 2, 0)
    setup_harness.advance_time(timedelta(minutes=5))
    assert setup_harness.datetime.time() == time(1, 7, 0)


def test_advance_time_to(setup_harness):
    setup_harness.advance_time_to(time(1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)
    setup_harness.advance_time_to(time(1, 10, 0))
    assert setup_harness.datetime.time() == time(1, 10, 0)


def test_advance_time_to_datetime(setup_harness):
    setup_harness.advance_time_to_datetime(datetime(2018, 1, 1, 1, 5, 0))
    assert setup_harness.datetime.time() == time(1, 5, 0)


def test_schedule_state_change_in_some_time(setup_harness):
    setup_harness.schedule_call_in(timedelta(minutes=2), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time(timedelta(minutes=1, seconds=50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_some_time(setup_harness):
    setup_harness.schedule_call_at(time(1, 10, 0), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_schedule_state_change_at_exact_time(setup_harness):
    setup_harness.schedule_call_at_datetime(
        datetime(2018, 1, 1, 1, 10, 0),
        "set_state", "sensor.test_sensor", "new sensor state",
    )
    setup_harness.advance_time_to(time(1, 9, 50))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    setup_harness.step()
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_wait_for_state_change(setup_harness):
    change_time = time(1, 2, 10)
    setup_harness.schedule_call_at(change_time, "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == change_time


def test_wait_for_later_state_change(setup_harness):
    setup_harness.schedule_call_at(time(1, 1, 10), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.schedule_call_at(time(1, 1, 30), "set_state", "sensor.test_sensor2", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor2")
    assert setup_harness.get_state("sensor.test_sensor2") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 30)


def test_wait_for_state_change_with_timeout(setup_harness):
    setup_harness.schedule_call_in(timedelta(minutes=1, seconds=50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", timeout=timedelta(minutes=1))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_deadline(setup_harness):
    setup_harness.schedule_call_at(time(1, 1, 50), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 1, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 0)
    setup_harness.wait_for_state_change("sensor.test_sensor", deadline=time(1, 2, 0))
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 1, 50)


def test_wait_for_state_change_with_new_state(setup_harness):
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", new="new sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 40)


def test_wait_for_state_change_with_old_state(setup_harness):
    setup_harness.schedule_call_at(time(1, 0, 20), "set_state", "sensor.test_sensor", "intermediate sensor state")
    setup_harness.schedule_call_at(time(1, 0, 40), "set_state", "sensor.test_sensor", "new sensor state")
    setup_harness.wait_for_state_change("sensor.test_sensor", old="intermediate sensor state")
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"


def test_state_should_not_change_for_some_time(setup_harness, timing):
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_for("sensor.test_sensor", timedelta(seconds=20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_not_change_until_some_time(setup_harness, timing):
    setup_harness.schedule_call_in(timedelta(seconds=30), "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_not_change_until("sensor.test_sensor", datetime(2018, 1, 1, 1, 0, 20))
    assert setup_harness.datetime.time() == time(1, 0, 20)


def test_state_should_change_in_some_time(setup_harness, timing):
    duration = timedelta(seconds=30)
    setup_harness.schedule_call_in(duration, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_in("sensor.test_sensor", "new sensor state", duration)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == time(1, 0, 30)


def test_state_should_change_at_some_time(setup_harness, timing):
    target = time(1, 1, 0)
    setup_harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert setup_harness.get_state("sensor.test_sensor") == "new sensor state"
    assert setup_harness.datetime.time() == target


@pytest.mark.parametrize("harness", [{"start_time": time(21, 30, 0), "interval": timedelta(minutes=10)}], indirect=True)
def test_state_should_change_next_day(harness):
    harness.set_state("sensor.test_sensor", "sensor state")
    target = time(1, 0, 0)
    harness.schedule_call_at(target, "set_state", "sensor.test_sensor", "new sensor state")
    from helpers.timing import Timing
    timing = Timing(harness)
    timing.state_should_change_at("sensor.test_sensor", "new sensor state", target)
    assert harness.get_state("sensor.test_sensor") == "new sensor state"
    assert harness.datetime == datetime(2018, 1, 2, 1, 0, 0)


def test_converted_state_expectations(setup_harness):
    setup_harness.set_state("sensor.test_sensor", "12")
    assert setup_harness.get_state("sensor.test_sensor", type="int") == 12
```

- [ ] **Step 6: Run infrastructure tests**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps" pytest 00_infrastructure_tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Delete old .robot files in 00_infrastructure_tests/**

```bash
rm test/appdaemon_unit_test/00_infrastructure_tests/*.robot
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "test: migrate 00_infrastructure_tests to pytest"
```

---

## Task 6: Migrate unit AppDaemon tests (part 1: simple suites)

**Files:**
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_temperature_basic.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_enabled_switch.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_expression.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_expression_enabler.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_enabler.py`
- Delete: corresponding `.robot` files

**Interfaces:**
- Consumes: Task 4 (Harness, timing fixtures), Task 5 (infrastructure tests validate harness)

This task ports the 5 simpler AppDaemon suites. Each suite follows the pattern: `harness` fixture for setup/teardown, `timing` fixture for timing assertions, bare `assert` for state checks, local helper functions for `Initialize` keywords, `@parametrize` for `[Template]` tests.

Due to the length of these suites, each file is a direct port of the corresponding `.robot` file. The conversion rules are:
- `Set State ${e} ${v}` → `harness.set_state("${e}", "${v}")`
- `State Should Be ${e} ${v}` → `assert harness.get_state("${e}") == "${v}"`
- `State Should Be As ${e} ${type} ${v}` → `assert harness.get_state("${e}", type="${type}") == ${v}`
- `Turn On ${e}` → `harness.turn_on("${e}")`
- `Turn Off ${e}` → `harness.turn_off("${e}")`
- `Create App ${module} ${class} ${name} ...args` → `harness.create_app("${module}", "${class}", "${name}", **args)`
- `Call On App ${app} ${method} ...args` → `harness.call_on_app(${app}, "${method}", ...args)`
- `Schedule Call At ${time} set_state ${e} ${v}` → `harness.schedule_call_at(${time_as_timedelta}, "set_state", "${e}", "${v}")`
- `Schedule Call At ${time} call_on_app ${app} ${method}` → `harness.schedule_call_at(${time_as_timedelta}, "call_on_app", ${app}, "${method}")`
- `State Should Change At ${e} ${v} ${time}` → `timing.state_should_change_at("${e}", "${v}", ${time_as_timedelta})`
- `State Should Not Change Until ${e} ${time}` → `timing.state_should_not_change_until("${e}", ${datetime})`
- `Advance Time ${amount}` → `harness.advance_time(${amount_as_timedelta})`
- `Advance Time To ${time}` → `harness.advance_time_to(${time_as_time})`
- `Step` → `harness.step()`
- `Get Current Time` → `harness.datetime`
- `[Template]` → `@pytest.mark.parametrize`
- `[Setup] Create Test Harness` → `harness` fixture (default or indirect parametrize)
- `[Teardown] Cleanup Test Harness` → harness fixture teardown (automatic)
- `Set Test Variable ${x} ${v}` → local Python variable `x = v`
- `&{dict} = Create Dictionary k=v` → `dict = {"k": "v"}`
- `@{list} = Create List a b` → `list_ = ["a", "b"]`

- [ ] **Step 1: Write test_temperature_basic.py**

Port `TemperatureBasicTest.robot` directly using the conversion rules above. The test has one test case "Basic" with no template, using default harness.

- [ ] **Step 2: Write test_enabled_switch.py**

Port `EnabledSwitchTest.robot`. The `[Setup] Initialize` keyword creates harness + sets states. Convert to local helper `_initialize(harness)` called at test start.

- [ ] **Step 3: Write test_expression.py**

Port `ExpressionTest.robot`. Multiple tests use `[Setup] Initialize ...` with different expression strings. Convert each to a function that takes `harness` and calls a local `_initialize(harness, expression, **initial_values)`.

- [ ] **Step 4: Write test_expression_enabler.py**

Port `ExpressionEnablerTest.robot`. The `[Template]` tests become `@parametrize`. The `Changes` test uses default harness.

- [ ] **Step 5: Write test_enabler.py**

Port `EnablerTest.robot`. This is the largest of the 5 — multiple `[Template]` tests (Script Enabler, Value Enabler, Date Enabler, Multi Enabler) and several non-templated tests with custom harness params.

- [ ] **Step 6: Run tests**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps" pytest appdaemon_tests/test_temperature_basic.py appdaemon_tests/test_enabled_switch.py appdaemon_tests/test_expression.py appdaemon_tests/test_expression_enabler.py appdaemon_tests/test_enabler.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Delete corresponding .robot files**

```bash
rm test/appdaemon_unit_test/appdaemon_tests/TemperatureBasicTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/EnabledSwitchTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/ExpressionTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/ExpressionEnablerTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/EnablerTest.robot
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "test: migrate simple unit AppDaemon suites to pytest"
```

---

## Task 7: Migrate unit AppDaemon tests (part 2: complex suites)

**Files:**
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_alert.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_auto_switch.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_cover.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_history_manager.py`
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_timer_switch.py`
- Delete: corresponding `.robot` files

**Interfaces:**
- Consumes: Task 6 (simple suites migrated, patterns established)

Same conversion rules as Task 6. These are the larger suites (AlertTest 184 lines, AutoSwitchTest 203 lines, CoverTest 237 lines, HistoryManagerTest 507 lines, TimerSwitchTest 547 lines). Key differences:

- **AlertTest**: `Alarm Text Should Be` keyword → helper that asserts state attribute "text" equals joined lines. `State Should Cycle At` keyword → helper that checks on, waits, steps, checks history, checks on.
- **AutoSwitchTest**: Heavy `[Template]` usage. `Initialize` keyword creates harness + sets up switch/enabler. Convert to `@parametrize` with indirect harness.
- **CoverTest**: `Initialize` / `Initialize With Delay` keywords. `Basic State Check` is a `[Template]`.
- **HistoryManagerTest**: Uses `history_util` helpers, `race_test_helper`, `ChangeTracker`, `HistoryEnabler`, `AggregatedValue`. `History Should Be` keyword → helper using `convert_history_input`/`convert_history_output`.
- **TimerSwitchTest**: Largest suite. Many tests call `Create Timer Switch` / `Create Timer Sequence` keywords with different args. `History Should Be` used in multi-timer-sequence tests with datetime values.

- [ ] **Step 1: Write test_alert.py**
- [ ] **Step 2: Write test_auto_switch.py**
- [ ] **Step 3: Write test_cover.py**
- [ ] **Step 4: Write test_history_manager.py**
- [ ] **Step 5: Write test_timer_switch.py**
- [ ] **Step 6: Run all unit AppDaemon tests**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps" pytest appdaemon_tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Delete corresponding .robot files**

```bash
rm test/appdaemon_unit_test/appdaemon_tests/AlertTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/AutoSwitchTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/CoverTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/HistoryManagerTest.robot
rm test/appdaemon_unit_test/appdaemon_tests/TimerSwitchTest.robot
```

- [ ] **Step 8: Delete old resources and __init__.robot**

```bash
rm test/appdaemon_unit_test/__init__.robot
rm -r test/appdaemon_unit_test/resources/
```

- [ ] **Step 9: Run full unit test suite**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps" pytest -v
```

Expected: all tests pass.

- [ ] **Step 10: Run mypy**

```bash
bin/mypy
```

Expected: no new errors.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "test: migrate complex unit AppDaemon suites to pytest"
```

---

## Task 8: Create integration test conftest and client classes

**Files:**
- Create: `test/appdaemon_integration_test/conftest.py`
- Create: `test/appdaemon_integration_test/helpers/hass_client.py`
- Create: `test/appdaemon_integration_test/helpers/appdaemon_client.py`
- Create: `test/appdaemon_integration_test/helpers/history_watcher.py`

**Interfaces:**
- Consumes: Task 1 (renamed dirs), Task 3 (fixed helpers)
- Produces:
  - `hass_client` session fixture: `HassClient` with `get_state(entity)`, `get_states()`, `clean_state(entity)`, `clean_states()`, `clean_history()`, `clean_states_and_history()`
  - `appdaemon_client` session fixture: `AppDaemonClient` with `call_function(function, *args, **kwargs)`, `get_state(entity, **kwargs)`, `set_state(entity, value, **attributes)`, `turn_on(entity)`, `turn_off(entity)`, `select_option(entity, value)`, `call_service(service, **kwargs)`, `call_on_app(app_name, function, *args, **kwargs)`, `wait_for_state(entity, expected, timeout=10)`, `load_apps(*configs)`, `unload_apps()`, `initialize_states(**states)`, `log(message)`
  - `history_watcher` function fixture: `HistoryWatcher` with `get_history()`, `check_history(*expected)`, `wait_for_history(*expected)`

- [ ] **Step 1: Write helpers/hass_client.py**

```python
from __future__ import annotations
import requests

HASS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkY2U3MDgwNDIwYmI0Mjg3OWIyYjQ1MjQ4OTQzNjI4YiIsImlhdCI6MTU0NjI1MDYyNiwiZXhwIjoxODYxNjEwNjI2fQ.1YmZVaw3EH2bu0jExU2Q6mIyrD1Qf0cPPJmt877mNC0"


class HassClient:
    def __init__(self, host: str):
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {HASS_TOKEN}"
        self._session.headers["Connection"] = "keep-alive"
        self._host = host

    def get_state(self, entity_id: str) -> str | None:
        r = self._session.get(f"http://{self._host}/api/states/{entity_id}")
        r.raise_for_status()
        return r.json()["state"]

    def get_states(self) -> list:
        r = self._session.get(f"http://{self._host}/api/states")
        r.raise_for_status()
        return r.json()

    def clean_state(self, entity_id: str) -> None:
        if entity_id.startswith("input_boolean.") or entity_id.startswith("switch."):
            self._session.post(
                f"http://{self._host}/api/services/homeassistant/turn_off",
                json={"entity_id": entity_id},
            )
        else:
            self._session.delete(f"http://{self._host}/api/states/{entity_id}")

    def clean_states(self) -> None:
        for entity in self.get_states():
            self.clean_state(entity["entity_id"])

    def clean_history(self) -> None:
        self._session.post(
            f"http://{self._host}/api/services/recorder/purge",
            json={"keep_days": 0},
        )

    def clean_states_and_history(self) -> None:
        self.clean_states()
        self.clean_history()
```

- [ ] **Step 2: Write helpers/appdaemon_client.py**

```python
from __future__ import annotations
import os
import time
import requests
from helpers.app_daemon import create_appdaemon_apps_config
from helpers.mutex_graph import append_graph, find_cycle


class AppDaemonClient:
    def __init__(self, host: str, appdaemon_dir: str):
        self._session = requests.Session()
        self._host = host
        self._dir = appdaemon_dir
        self._loaded_apps: list[str] = []

    def call_function(self, function: str, *args, **kwargs):
        result_type = kwargs.pop("result_type", None)
        arg_types = kwargs.pop("arg_types", [])
        kwarg_types = kwargs.pop("kwarg_types", {})
        content = {
            "function": function,
            "result_type": result_type,
            "arg_types": arg_types,
            "kwarg_types": kwarg_types,
            "args": list(args),
            "kwargs": kwargs,
        }
        r = self._session.post(f"http://{self._host}/api/appdaemon/TestApp", json=content)
        r.raise_for_status()
        return r.json()

    def get_state(self, entity_id: str, **kwargs):
        return self.call_function("get_state", entity_id, **kwargs)

    def set_state(self, entity_id: str, value, **attributes):
        self.call_function("set_state", entity_id, state=value, attributes=attributes)

    def turn_on(self, entity_id: str):
        self.call_function("turn_on", entity_id)

    def turn_off(self, entity_id: str):
        self.call_function("turn_off", entity_id)

    def select_option(self, entity_id: str, value: str):
        self.call_function("select_option", entity_id, value)

    def set_value(self, entity_id: str, value):
        self.call_function("set_value", entity_id, value)

    def call_service(self, service: str, **kwargs):
        self.call_function("call_service", service, **kwargs)

    def call_on_app(self, app_name: str, function: str, *args, **kwargs):
        return self.call_function("call_on_app", app_name, function, *args, **kwargs)

    def log(self, message: str):
        self.call_function("log", message)

    def wait_for_state(self, entity_id: str, expected, timeout: int = 10) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.get_state(entity_id) == expected:
                return
            time.sleep(0.1)
        assert self.get_state(entity_id) == expected

    def load_apps(self, *configs: str) -> None:
        self._loaded_apps = create_appdaemon_apps_config(self._dir, "TestApp", *configs)
        self._wait_until_loaded(*self._loaded_apps, timeout=30)

    def unload_apps(self) -> None:
        if not self._loaded_apps:
            return
        create_appdaemon_apps_config(self._dir, "TestApp")
        self._wait_until_unloaded(*self._loaded_apps, timeout=30)
        self._loaded_apps = []

    def initialize_states(self, **states):
        for entity, state in states.items():
            self.call_function("set_state", entity, state=state, attributes={})

    def check_mutex_graph(self, global_mutex_graph: dict) -> None:
        graph = self.call_on_app("locker", "get_global_graph")
        append_graph(global_mutex_graph, graph)
        assert not find_cycle(global_mutex_graph)

    def _wait_until_loaded(self, *apps: str, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.call_function("is_all_apps_loaded", list(apps)):
                return
            time.sleep(0.1)
        assert self.call_function("is_all_apps_loaded", list(apps))

    def _wait_until_unloaded(self, *apps: str, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.call_function("is_all_apps_unloaded", list(apps)):
                return
            time.sleep(0.1)
        assert self.call_function("is_all_apps_unloaded", list(apps))
```

- [ ] **Step 3: Write helpers/history_watcher.py**

```python
from __future__ import annotations
import time
from typing import Any


class HistoryWatcher:
    def __init__(self, appdaemon_client: Any):
        self._ad = appdaemon_client

    def get_history(self) -> list:
        return self._ad.call_on_app("history_watcher", "get_state_history")

    def check_history(self, *expected: Any) -> None:
        expected_pairs = [[expected[i], expected[i + 1]] for i in range(0, len(expected), 2)]
        actual = self.get_history()
        assert actual == expected_pairs

    def wait_for_history(self, *expected: Any) -> None:
        expected_pairs = [[expected[i], expected[i + 1]] for i in range(0, len(expected), 2)]
        deadline = time.time() + 30
        while time.time() < deadline:
            if self._ad.call_on_app("history_watcher", "has_history", expected_pairs):
                return
            time.sleep(0.2)
        assert self._ad.call_on_app("history_watcher", "has_history", expected_pairs)
```

- [ ] **Step 4: Write conftest.py**

```python
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
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/api/")
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
```

- [ ] **Step 5: Verify conftest imports work**

```bash
source test/.venv/bin/activate
cd test/appdaemon_integration_test
PYTHONPATH="${PWD}:${PWD}/helpers" python -c "from conftest import *; from helpers.hass_client import HassClient; from helpers.appdaemon_client import AppDaemonClient; from helpers.history_watcher import HistoryWatcher; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add pytest conftest and client classes for integration tests"
```

---

## Task 9: Migrate integration test suites

**Files:**
- Create: `test/appdaemon_integration_test/appdaemon_tests/test_cover.py`
- Create: `test/appdaemon_integration_test/appdaemon_tests/test_enabled_switch.py`
- Create: `test/appdaemon_integration_test/appdaemon_tests/test_history_manager.py`
- Create: `test/appdaemon_integration_test/appdaemon_tests/test_timer_switch.py`
- Delete: corresponding `.robot` files + `__init__.robot`
- Delete: `test/appdaemon_integration_test/resources/`

**Interfaces:**
- Consumes: Task 8 (conftest, client fixtures)

Conversion rules (integration-specific):
- `Set State ${e} ${v}` → `appdaemon_client.set_state("${e}", "${v}")`
- `State Should Be ${e} ${v}` → `assert appdaemon_client.get_state("${e}") == "${v}"`
- `Wait For State ${e} ${v}` → `appdaemon_client.wait_for_state("${e}", "${v}")`
- `Select Option ${e} ${v}` → `appdaemon_client.select_option("${e}", "${v}")`
- `Turn On ${e}` → `appdaemon_client.turn_on("${e}")`
- `Turn Off ${e}` → `appdaemon_client.turn_off("${e}")`
- `Call Service ${service} ...kwargs` → `appdaemon_client.call_service("${service}", **kwargs)`
- `Load Apps Configs @{configs}` → `appdaemon_client.load_apps(*configs)`
- `Check History @{expected}` → `history_watcher.check_history(*expected)`
- `Wait For History @{expected}` → `history_watcher.wait_for_history(*expected)`
- `Initialize States &{states}` → `appdaemon_client.initialize_states(**states)`
- `Call Function call_on_app ${app} ${method}` → `appdaemon_client.call_on_app("${app}", "${method}")`
- `Initialize Apps Configs @{configs}` → `appdaemon_client.load_apps(*configs)` (after `initialize_states`)
- `Cleanup Apps Configs` → autouse `cleanup_apps` fixture (automatic)
- `Sleep ${seconds}` → `time.sleep(seconds)`

- [ ] **Step 1: Write test_cover.py**

Port `CoverTest.robot`. Uses `appdaemon_client`, `history_watcher`. `Initialize` keyword sets states + loads apps.

- [ ] **Step 2: Write test_enabled_switch.py**

Port `EnabledSwitchTest.robot`. Has `[Template] Test Reload` with 25 parametrized rows. Convert to `@parametrize`. Uses `history_watcher.check_history`.

- [ ] **Step 3: Write test_history_manager.py**

Port `HistoryManagerTest.robot`. Uses HASS history API (via `hass_client` for `wait_for_history_size`). `History Should Be` uses `convert_history_output` from `helpers/history_util.py`.

- [ ] **Step 4: Write test_timer_switch.py**

Port `TimerSwitchTest.robot`. Uses `history_watcher`. `Start Control` keyword → helper function.

- [ ] **Step 5: Run integration tests**

```bash
source test/.venv/bin/activate
cd test/appdaemon_integration_test
APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" PYTHONPATH="${PWD}:${PWD}/helpers" pytest appdaemon_tests/ -v
```

Expected: all tests pass (may be slow — these are integration tests).

- [ ] **Step 6: Delete old .robot files and resources**

```bash
rm test/appdaemon_integration_test/appdaemon_tests/*.robot
rm -r test/appdaemon_integration_test/resources/
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "test: migrate integration test suites to pytest"
```

---

## Task 10: Remove run-test scripts and update CI, docs, gitignore

**Files:**
- Delete: `test/appdaemon_unit_test/run-test`
- Delete: `test/appdaemon_integration_test/run-test`
- Modify: `.circleci/config.yml`
- Modify: `test/.gitignore`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: Tasks 5-9 (all tests migrated)

- [ ] **Step 1: Delete run-test scripts**

```bash
rm test/appdaemon_unit_test/run-test
rm test/appdaemon_integration_test/run-test
```

- [ ] **Step 2: Update test/.gitignore**

Write `test/.gitignore`:

```
output/
.HA_VERSION
.pytest_cache/
```

- [ ] **Step 3: Update .circleci/config.yml**

Replace the `robot` command and both jobs:

```yaml
version: 2.1
commands:
  pytest:
    parameters:
      directory:
        type: string
    steps:
      - run:
          name: run tests
          command: |
            /test/bin/pytest <<parameters.directory>> -v \
                --tb=short
      - store_artifacts:
          path: <<parameters.directory>>/output
          when: on_fail

jobs:
  appdaemon-unit-test:
    docker:
      - image: kangirigungi/home-assistant-config-test:4
    environment:
      - TEST_PYTHON: /test/bin/python
    steps:
      - checkout
      - pytest:
          directory: test/appdaemon_unit_test

  appdaemon-integration-test:
    docker:
      - image: kangirigungi/home-assistant-config-test:4
    environment:
      - HASS_PATH: /homeassistant
      - APPDAEMON_PATH: /appdaemon
    steps:
      - checkout
      - run:
          command: git submodule update --init --recursive
      - pytest:
          directory: test/appdaemon_integration_test

workflows:
  version: 2
  test:
    jobs:
      - appdaemon-unit-test
      - appdaemon-integration-test
```

- [ ] **Step 4: Update AGENTS.md**

In the "Running the tests" section, replace Robot commands with:

```sh
# Unit tests
source test/.venv/bin/activate
pytest test/appdaemon_unit_test/ [-k <test>]

# Integration tests
source test/.venv/bin/activate
APPDAEMON_PATH=test/appdaemon_integration_test/.appdaemon \
HASS_PATH=test/appdaemon_integration_test/.hass \
pytest test/appdaemon_integration_test/ [-k <test>]
```

In "Interpreting the output" section, replace Robot output descriptions:

- `output/` dir still holds logs.
- Unit: `output/logs/<module_name>/<test_name>[_param_ids].log` per test.
- Integration: `output/hass/` (homeassistant.log, .stdout, .stderr), `output/appdaemon/` (appdaemon.stdout, appdaemon.stderr, error.log, appdaemon.log).
- pytest terminal output: pass/fail summary with tracebacks.
- `report.html` / `log.html` / `output.xml` no longer generated.

In "Setting up virtual environment": `./test/setup_virtualenv.sh test|hass|appdaemon|all`

In "Upgrading dependencies": replace `test/dependencies/robot/` with `test/dependencies/test/`.

In Verification section, replace run-test commands with pytest commands.

- [ ] **Step 5: Run full unit test suite one final time**

```bash
source test/.venv/bin/activate
cd test/appdaemon_unit_test
PYTHONPATH="${PWD}:${PWD}/apps" pytest -v
```

Expected: all pass.

- [ ] **Step 6: Run mypy**

```bash
bin/mypy
```

Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove run-test scripts, update CI and docs for pytest"
```

---

## Task 11: Run integration tests and final verification

**Files:** none (verification only)

- [ ] **Step 1: Run full integration test suite**

```sh
source test/.venv/bin/activate
cd test/appdaemon_integration_test
APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" PYTHONPATH="${PWD}:${PWD}/helpers" pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify no .robot files remain**

```bash
find test/ -name "*.robot" -not -path "*/.venv/*" -not -path "*/.hass/*" -not -path "*/.appdaemon/*"
```

Expected: no output (all .robot files removed).

- [ ] **Step 3: Verify no run-test scripts remain**

```bash
find test/ -name "run-test" -not -path "*/.venv/*"
```

Expected: no output.

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git status
git add -A
git commit -m "chore: final cleanup after pytest migration"
```
