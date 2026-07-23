# Migrate Tests from Robot Framework to pytest

## Goal

Migrate all AppDaemon test suites from Robot Framework to pytest. Keep the current
project structure (same directories, same apps, same configs). Remove `run-test`
shell wrappers — all glue code lives in Python. Keep the existing shell-script-based
wrapping of HASS and AppDaemon in integration tests. Remove the need to manually
delete the `output/` folder before runs.

## Decisions

| Decision | Choice |
|----------|--------|
| Integration wrapping | Keep `./hass` and `./appdaemon` shell scripts; Python fixtures spawn them via `subprocess` |
| Test file layout | In-place: replace `*.robot` with `test_*.py` in same dirs |
| Unit harness shape | Native pytest: bare `assert` for state checks; thin `Timing` helper object for composite timing assertions |
| Template/parametrized tests | `@pytest.mark.parametrize` |
| Output dir | Session fixture clears `output/` at start |
| Robot deps | Drop all (`robotframework`, `robotframework-pabot`, `robotframework-httplibrary`, `six`) |
| Integration HTTP client | `requests` |
| Integration client split | Separate `HassClient` + `AppDaemonClient` + `HistoryWatcher` classes, each with its own fixture |
| Time constants | Native `datetime` types (`timedelta`, `datetime`, `date`, `time`) — no string-parsing helpers |
| Harness creation | No maker/factory fixture; all mid-test `Create Test Harness` calls converted to `indirect` parametrize or local setup helpers |
| Naming | snake_case directory names; `libraries/` → `helpers/`; remove "Suite" from suite dir names; `robot` venv/env → `test` |

## Architecture

### Directory layout

```
test/
  conftest.py                              # empty or minimal
  dependencies/
    test/                                  # was robot/
      pyproject.toml                       # pytest + requests + pyyaml + python-dateutil + psutil
      uv.lock                              # regenerated
    appdaemon/                             # unchanged
    homeassistant/                         # unchanged
  setup_virtualenv.sh                      # robot) → test), dependencies/robot → dependencies/test
  docker/
    Dockerfile                             # /robot venv → /test, paths updated
  appdaemon_unit_test/                     # was AppDaemonUnitTest/
    conftest.py                            # NEW: session output clear, harness fixture, module mutex-graph check
    helpers/                               # was libraries/
      __init__.py
      config.py                            # unchanged
      date_time_util.py                    # unchanged
      history_util.py                      # unchanged
      type_util.py                         # unchanged
      race_test_helper.py                  # unchanged
      timing.py                            # NEW: Timing helper object (B2)
    apps/                                  # unchanged (mocked hass.py, test_app.py, symlinked prod apps)
    00_infrastructure_tests/               # was 00InfrastructureSuite/
      test_date_time_util.py
      test_history_util.py
      test_mutex_graph.py
      test_test_harness.py                 # exercises helpers/timing.py
      test_type_util.py
    appdaemon_tests/                       # was AppDaemonSuite/
      test_alert.py
      test_auto_switch.py
      test_cover.py
      test_enabled_switch.py
      test_enabler.py
      test_expression_enabler.py
      test_expression.py
      test_history_manager.py
      test_temperature_basic.py
      test_timer_switch.py
  appdaemon_integration_test/              # was AppDaemonIntegrationTest/
    conftest.py                            # NEW: session fixtures for HASS+AppDaemon subprocess lifecycle
    helpers/                               # was libraries/
      __init__.py
      app_daemon.py                        # unchanged (config generation)
      home_assistant.py                    # unchanged (config generation)
      directories.py                       # unchanged
      mutex_graph.py                       # unchanged
      process_check.py                     # unchanged
      type_util.py                         # unchanged
      history_util.py                      # unchanged
      hass_client.py                       # NEW: HassClient (requests.Session → HASS REST API)
      appdaemon_client.py                  # NEW: AppDaemonClient (requests.Session → TestApp HTTP endpoint)
      history_watcher.py                   # NEW: HistoryWatcher (wraps AppDaemonClient for history checks)
    appdaemon                              # shell script (unchanged)
    hass                                   # shell script (unchanged)
    config/                                # unchanged (hass + appdaemon configs, configs/*.yaml, symlinked apps)
    .hass/                                 # venv (gitignored)
    .appdaemon/                            # venv (gitignored)
    appdaemon_tests/                       # was AppDaemonSuite/
      test_cover.py
      test_enabled_switch.py
      test_history_manager.py
      test_timer_switch.py
```

### Files removed

- `test/AppDaemonUnitTest/run-test`
- `test/AppDaemonIntegrationTest/run-test`
- All `*.robot` files (32 files total):
  - Unit: `__init__.robot`, 5 `resources/*.robot`, 5 `00InfrastructureSuite/*.robot`, 10 `AppDaemonSuite/*.robot`
  - Integration: `AppDaemonSuite/__init__.robot`, 4 `AppDaemonSuite/*.robot`, 7 `resources/*.robot`

### Files renamed

| From | To |
|------|-----|
| `test/AppDaemonUnitTest/` | `test/appdaemon_unit_test/` |
| `test/AppDaemonIntegrationTest/` | `test/appdaemon_integration_test/` |
| `test/AppDaemonUnitTest/00InfrastructureSuite/` | `test/appdaemon_unit_test/00_infrastructure_tests/` |
| `test/AppDaemonUnitTest/AppDaemonSuite/` | `test/appdaemon_unit_test/appdaemon_tests/` |
| `test/AppDaemonIntegrationTest/AppDaemonSuite/` | `test/appdaemon_integration_test/appdaemon_tests/` |
| `test/AppDaemonUnitTest/libraries/` | `test/appdaemon_unit_test/helpers/` |
| `test/AppDaemonIntegrationTest/libraries/` | `test/appdaemon_integration_test/helpers/` |
| `test/dependencies/robot/` | `test/dependencies/test/` |

### Files added

- `test/conftest.py`
- `test/appdaemon_unit_test/conftest.py`
- `test/appdaemon_unit_test/helpers/timing.py`
- `test/appdaemon_integration_test/conftest.py`
- `test/appdaemon_integration_test/helpers/hass_client.py`
- `test/appdaemon_integration_test/helpers/appdaemon_client.py`
- `test/appdaemon_integration_test/helpers/history_watcher.py`
- All `test_*.py` files replacing `.robot` files

## Unit test harness

### `test/conftest.py`

Empty or minimal — no shared fixtures. Each test dir owns its own `base_output_directory`.

### `test/appdaemon_unit_test/conftest.py`

Defines `base_output_directory` locally (resolves to `test/appdaemon_unit_test/output`):

```python
@pytest.fixture(scope="session")
def base_output_directory():
    return os.path.join(os.path.dirname(__file__), "output")
```

Three concerns:

**1. Session fixture — clear `output/`:**

```python
@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory):
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)
```

No manual `rm -rf output` needed.

**2. Module-scoped mutex-graph invariant (replaces `__init__.robot` Suite Teardown):**

```python
@pytest.fixture(scope="module", autouse=True)
def global_mutex_graph():
    graph: dict = {}
    yield graph
    assert not find_cycle(graph)  # Check Global Mutex Graph
```

Each test's harness cleanup appends its locker's mutex graph into this dict.
The module fixture asserts no deadlock at teardown.

**3. Per-test harness fixture (replaces `Create Test Harness` / `Cleanup Test Harness`):**

```python
@pytest.fixture
def harness(request, base_output_directory, global_mutex_graph):
    params = getattr(request, "param", {})
    start_date = params.get("start_date", date(2018, 1, 1))
    start_time = params.get("start_time", time(0, 0, 0))
    interval = params.get("interval", timedelta(seconds=10))
    safe_name = request.node.name.replace("[", "_").replace("]", "")
    log_path = f"{base_output_directory}/logs/{request.module.__name__}/{safe_name}.log"
    h = Harness(start_date, start_time, interval, log_path, global_mutex_graph)
    yield h
    h.cleanup()  # append_and_check_mutex_graph, remove_all_apps, check_error
```

Tests needing custom start/interval parametrize the fixture:

```python
@pytest.mark.parametrize("harness", [{"start_time": time(23, 59, 30), "interval": timedelta(seconds=1)}], indirect=True)
def test_date_enabler_exact_change_time(harness, timing):
    ...
```

The `suffix` parameter from Robot is eliminated — pytest's `request.node.name`
(which includes parametrize IDs) generates unique log paths automatically.
Log path format: `output/logs/<module_name>/<test_name>[_param_ids].log`
(e.g. `output/logs/test_enabler/test_value_enabler_on-True-value_on.log`).

### `Harness` class

Thin wrapper over `AppManager` + `TestApp` + `Locker`. Exposes primitives only
(no assertions — those are bare `assert` in tests or in `Timing`):

- `step()`
- `advance_time(duration: timedelta)`
- `advance_time_to(target: datetime)`
- `advance_time_to_datetime(target: datetime)`
- `get_state(entity_id, attribute=None)`
- `set_state(entity_id, value, **attributes)`
- `turn_on(entity_id)` / `turn_off(entity_id)`
- `get_current_time() -> datetime`
- `create_app(module, class_name, name, **kwargs)`
- `get_app(name)`
- `schedule_call_in(delay: timedelta, func, *args, **kwargs)`
- `schedule_call_at(target_time: time, func, *args, **kwargs)`
- `schedule_call_at_datetime(target: datetime, func, *args, **kwargs)`
- `call_on_app(app, method, *args, **kwargs)`
- `check_error()`
- `datetime` (property)
- `interval` (property)
- `date_from_time(timedelta, future) -> datetime`
- `wait_for_state_change(entity, timeout=None, deadline=None, deadline_datetime=None, old=None, new=None)`

### `helpers/timing.py` — `Timing` class (B2)

Composite timing assertions using plain `assert` internally (pytest AST rewriting
applies to helper modules, so failures show actual vs expected values):

```python
class Timing:
    def __init__(self, harness):
        self._h = harness

    def state_should_change_at(self, entity, value, target_time):
        target = self._h.date_from_time(target_time, future=True)
        deadline = target - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_until(entity, deadline)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_not_change_for(self, entity, duration):
        old = self._h.get_state(entity)
        before = self._h.datetime
        self._h.wait_for_state_change(entity, timeout=duration)
        assert self._h.get_state(entity) == old
        assert self._h.datetime - before == duration

    def state_should_not_change_until(self, entity, target):
        old = self._h.get_state(entity)
        self._h.wait_for_state_change(entity, deadline=target)
        assert self._h.get_state(entity) == old
        assert self._h.datetime == target

    def state_should_change_in(self, entity, value, duration):
        timeout = duration - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_for(entity, timeout)
        self._h.step()
        assert self._h.get_state(entity) == value

    def state_should_change_at_datetime(self, entity, value, target):
        deadline = target - self._h.interval
        assert self._h.get_state(entity) != value
        self.state_should_not_change_until(entity, deadline)
        self._h.step()
        assert self._h.get_state(entity) == value
```

Fixture:

```python
@pytest.fixture
def timing(harness):
    return Timing(harness)
```

### Test patterns

**Suite-level setup (default harness):**

```python
def test_turn_alert_on_and_off(harness, timing):
    harness.set_state("binary_sensor.error1", "off")
    alert = harness.create_app("alert", "AlertAggregator", "alert", sources=[...], target=..., ...)
    assert harness.get_state("binary_sensor.alert_sensor") == "off"
    harness.schedule_call_at(timedelta(minutes=1), "set_state", "binary_sensor.error1", "on")
    timing.state_should_change_at("binary_sensor.alert_sensor", "on", timedelta(minutes=1))
```

**`[Template]` keyword → `@parametrize`:**

```python
@pytest.mark.parametrize("harness, cls, entity_value, expected, args", [
    ({"start_time": time(0, 0, 0)}, "ValueEnabler", "off", False, {"value": "on"}),
    ({"start_time": time(0, 0, 0)}, "ValueEnabler", "on", True, {"value": "on"}),
    ...
], indirect=["harness"])
def test_value_enabler(harness, cls, entity_value, expected, args):
    harness.set_state("sensor.test_input", entity_value)
    enabler = harness.create_app("enabler", cls, "enabler", entity="sensor.test_input", **args)
    assert enabler.is_enabled() == expected
```

**`Initialize` keyword → local helper function:**

```python
def _initialize_auto_switch(harness, type_, initial_switch="auto", initial_target="off"):
    harness.set_state("input_boolean.test_switch", initial_target)
    harness.set_state("input_select.test_auto_switch_switch", initial_switch)
    args = {"target": "input_boolean.test_switch"}
    if "Switched" in type_:
        args["switch"] = "input_select.test_auto_switch_switch"
    if "Reentrant" in type_:
        args["reentrant"] = True
    if "Enabled" in type_:
        harness.create_app("enabler", "ScriptEnabler", "switch_enabler")
        args["enabler"] = "switch_enabler"
    auto_switch = harness.create_app("auto_switch", "AutoSwitch", "test_auto_switch", **args)
    harness.step()
    return auto_switch
```

Local helpers take `harness` as first arg — no harness creation, no factory fixture.

## Integration test harness

### `test/appdaemon_integration_test/conftest.py`

Defines `base_output_directory` locally (resolves to `test/appdaemon_integration_test/output`):

```python
@pytest.fixture(scope="session")
def base_output_directory():
    return os.path.join(os.path.dirname(__file__), "output")
```

Session-scoped subprocess management for HASS and AppDaemon:

```python
@pytest.fixture(scope="session")
def global_mutex_graph():
    graph: dict = {}
    yield graph

@pytest.fixture(scope="session", autouse=True)
def clear_output_dir(base_output_directory):
    shutil.rmtree(base_output_directory, ignore_errors=True)
    os.makedirs(base_output_directory, exist_ok=True)

@pytest.fixture(scope="session")
def home_assistant(base_output_directory):
    port = 18000
    hass_path = f"{base_output_directory}/hass"
    check_for_leftover_process("hass", rf"hass .*{hass_path}")
    shutil.rmtree(hass_path, ignore_errors=True)
    create_home_assistant_configuration(hass_path, port)
    shutil.copy(hass_auth_path, f"{hass_path}/.storage/auth")
    proc = subprocess.Popen(
        ["./hass", "--verbose", "--config", hass_path, "--log-file", f"{hass_path}/homeassistant.log"],
        stdout=open(f"{hass_path}/homeassistant.stdout", "w"),
        stderr=open(f"{hass_path}/homeassistant.stderr", "w"),
    )
    _wait_for_hass_start("127.0.0.1", port, timeout=120)
    yield {"process": proc, "host": f"127.0.0.1:{port}", "port": port}
    proc.terminate()
    proc.wait(timeout=30)
    assert proc.poll() is not None

@pytest.fixture(scope="session")
def appdaemon(home_assistant, base_output_directory):
    port = home_assistant["port"] + 1
    appdaemon_dir = f"{base_output_directory}/appdaemon"
    os.makedirs(appdaemon_dir, exist_ok=True)
    create_appdaemon_configuration(appdaemon_dir, home_assistant["host"], port)
    create_appdaemon_apps_config(appdaemon_dir, "TestApp")
    proc = subprocess.Popen(
        ["./appdaemon", "--config", appdaemon_dir],
        stdout=open(f"{appdaemon_dir}/appdaemon.stdout", "w"),
        stderr=open(f"{appdaemon_dir}/appdaemon.stderr", "w"),
    )
    _wait_for_appdaemon_start("127.0.0.1", port, timeout=30)
    yield {"process": proc, "host": f"127.0.0.1:{port}", "dir": appdaemon_dir}
    proc.terminate()
    proc.wait(timeout=10)
    assert proc.poll() is not None
    # Cleanup AppDaemon invariants: stderr and error.log must be empty
    assert os.path.getsize(f"{appdaemon_dir}/appdaemon.stderr") == 0
    assert os.path.getsize(f"{appdaemon_dir}/error.log") == 0
```

### `helpers/hass_client.py` — `HassClient`

Direct REST API access to Home Assistant via `requests`:

```python
class HassClient:
    def __init__(self, host):
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {HASS_TOKEN}"
        self._session.headers["Connection"] = "keep-alive"
        self._host = host

    def get_state(self, entity_id) -> str | None: ...
    def get_states(self) -> list: ...
    def clean_state(self, entity_id) -> None: ...
    def clean_states(self) -> None: ...
    def clean_history(self) -> None: ...
    def clean_states_and_history(self) -> None: ...
```

Fixture (session-scoped):

```python
@pytest.fixture(scope="session")
def hass_client(home_assistant):
    return HassClient(home_assistant["host"])
```

### `helpers/appdaemon_client.py` — `AppDaemonClient`

Calls the TestApp HTTP endpoint on AppDaemon:

```python
class AppDaemonClient:
    def __init__(self, host, appdaemon_dir):
        self._session = requests.Session()
        self._host = host
        self._dir = appdaemon_dir
        self._loaded_apps = []

    def call_function(self, function, *args, **kwargs): ...
    def get_state(self, entity_id, **kwargs): ...
    def set_state(self, entity_id, value, **attributes): ...
    def turn_on(self, entity_id): ...
    def turn_off(self, entity_id): ...
    def select_option(self, entity_id, value): ...
    def set_value(self, entity_id, value): ...
    def call_service(self, service, **kwargs): ...
    def call_on_app(self, app_name, function, *args, **kwargs): ...
    def log(self, message): ...
    def wait_for_state(self, entity_id, expected, timeout=10): ...
    def load_apps(self, *configs): ...       # creates apps config, waits for load
    def unload_apps(self): ...                # resets to TestApp-only, waits for unload
    def initialize_states(self, **states): ...
```

Fixture (session-scoped):

```python
@pytest.fixture(scope="session")
def appdaemon_client(appdaemon, global_mutex_graph):
    client = AppDaemonClient(appdaemon["host"], appdaemon["dir"])
    yield client
    # Append And Check Mutex Graph (runs before appdaemon fixture stops the process)
    graph = client.call_on_app("locker", "get_global_graph")
    append_graph(global_mutex_graph, graph)
    assert not find_cycle(global_mutex_graph)
```

The `global_mutex_graph` is a session-scoped dict fixture (same pattern as unit tests).
Fixture teardown order ensures the mutex check runs before `appdaemon` teardown
stops the process (dependent fixtures tear down first).

### `helpers/history_watcher.py` — `HistoryWatcher`

Wraps `AppDaemonClient` for history-specific checks:

```python
class HistoryWatcher:
    def __init__(self, appdaemon_client):
        self._ad = appdaemon_client

    def get_history(self): ...
    def check_history(self, *expected): ...    # entity/value pairs → assert actual == expected
    def wait_for_history(self, *expected): ... # polls has_history until True
```

Fixture (function-scoped, since apps reload per test):

```python
@pytest.fixture
def history_watcher(appdaemon_client):
    return HistoryWatcher(appdaemon_client)
```

### Per-test apps lifecycle

```python
@pytest.fixture(autouse=True)
def cleanup_apps(appdaemon_client):
    """Unloads extra apps after each test (replaces Cleanup Apps Configs)."""
    yield
    appdaemon_client.unload_apps()
```

Tests call `appdaemon_client.load_apps(...)` explicitly (matching Robot's
`Initialize Apps Configs`). The autouse fixture handles teardown.

### Test pattern

```python
def test_simple_state_changes(appdaemon_client, history_watcher):
    appdaemon_client.initialize_states(
        sensor_test_cover_position1=0, sensor_test_cover_position2=0,
        input_number_cover_position=0, sensor_cover_available="on",
        input_select_test_cover_mode="stable",
    )
    appdaemon_client.call_service("cover/close_cover", entity_id="cover.test_cover")
    appdaemon_client.select_option("input_select.test_cover_mode", "stable")
    appdaemon_client.wait_for_state("input_number.cover_position", 0.0)
    appdaemon_client.wait_for_state("cover.test_cover", "closed")
    appdaemon_client.load_apps("HistoryWatcher", "Cover1")
    history_watcher.wait_for_history("input_select.test_cover_mode", "auto",
                                     "input_select.test_cover_mode", "stable")
    history_watcher.check_history("input_select.test_cover_mode", "auto",
                                  "input_number.cover_position", 50.0,
                                  "input_select.test_cover_mode", "stable")

    appdaemon_client.set_state("sensor.test_cover_position1", 50)
    history_watcher.wait_for_history("input_select.test_cover_mode", "auto",
                                     "input_select.test_cover_mode", "stable")
    history_watcher.check_history("input_select.test_cover_mode", "auto",
                                  "input_number.cover_position", 50.0,
                                  "input_select.test_cover_mode", "stable")
```

### What stays unchanged

- `./hass` and `./appdaemon` shell scripts
- `config/` directory (hass + appdaemon configs, `configs/*.yaml`, symlinked apps)
- `helpers/app_daemon.py`, `helpers/home_assistant.py`, `helpers/directories.py`,
  `helpers/mutex_graph.py`, `helpers/process_check.py`, `helpers/type_util.py`,
  `helpers/history_util.py` — called from conftest and client classes instead of Robot keywords

### `config/appdaemon/apps/test_app.py` fix

The integration `test_app.py` imports `from robot.libraries import DateTime`.
After dropping Robot deps, replace with stdlib `datetime`:

```python
# Before:
from robot.libraries import DateTime
# ...
DateTime.convert_date(value, result_format="timestamp")  # → ISO timestamp string
DateTime.convert_time(value, result_format="timer")       # → timer string like "1:00:00"

# After:
# No import needed — use datetime/timedelta methods directly:
value.isoformat()              # for datetime → ISO timestamp
str(value)                     # for timedelta → "1:00:00" format
```

## Dependencies

### `test/dependencies/test/pyproject.toml` (was `robot/`)

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

Removed: `robotframework`, `robotframework-pabot`, `robotframework-httplibrary`, `six`.
Added: `pytest`, `requests`.
Kept: `pyyaml` (config generation), `python-dateutil` (helpers), `psutil` (process checking).

`uv.lock` regenerated via `uv lock` in `test/dependencies/test/`.

### `test/setup_virtualenv.sh`

- `robot)` case → `test)`
- `robot=1` → `test=1`
- `setup_sync python3.12 .venv dependencies/robot` → `setup_sync python3.12 .venv dependencies/test`

### `test/docker/Dockerfile`

```dockerfile
# Test env (Python 3.12 venv) — was "Robot framework env"
RUN uv venv /test --python 3.12
WORKDIR /deps/test
COPY --from=deps test/dependencies/test/ ./
RUN VIRTUAL_ENV=/test uv sync --frozen --no-install-project --active
```

Venv path `/robot` → `/test`. The `/homeassistant` and `/appdaemon` venvs are unchanged.

## Invocation

### Unit tests

```sh
source test/.venv/bin/activate
pytest test/appdaemon_unit_test/ [-k <test>] [-v]
```

### Integration tests

```sh
source test/.venv/bin/activate
APPDAEMON_PATH=test/appdaemon_integration_test/.appdaemon \
HASS_PATH=test/appdaemon_integration_test/.hass \
pytest test/appdaemon_integration_test/ [-k <test>] [-v]
```

No `run-test` scripts. No `rm -rf output` (session fixture handles it).
Scoping with `-k <name>` replaces Robot's `-s <suite>` / `-t <test>`.

### `bin/mypy`

Path update (parent dir renamed):

```sh
exec "$(cd "$(dirname "$0")/.." && pwd)/test/appdaemon_integration_test/.appdaemon/bin/mypy" "$@"
```

## CI (`.circleci/config.yml`)

### Unit test job

Before: uses `ppodgorsek/robot-framework:latest` image.
After: use the same `kangirigungi/home-assistant-config-test` image (has all venvs).

```yaml
appdaemon-unit-test:
  docker:
    - image: kangirigungi/home-assistant-config-test:4
  environment:
    - TEST_PYTHON: /test/bin/python
  steps:
    - checkout
    - run:
        name: run tests
        command: /test/bin/pytest test/appdaemon_unit_test/ -v
    - store_artifacts:
        path: test/appdaemon_unit_test/output
        when: on_fail
    - store_test_results:
        path: test/appdaemon_unit_test/output
```

### Integration test job

```yaml
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
    - run:
        name: run tests
        command: |
          /test/bin/pytest test/appdaemon_integration_test/ -v
    - store_artifacts:
        path: test/appdaemon_integration_test/output
        when: on_fail
```

The `robot` command template, `--xunit=robot.xml`, `--removekeywords WUKS`, and
pabot cleanup steps are removed.

## `test/.gitignore`

Before:
```
output/
.HA_VERSION
.pabotsuitenames
log.html
output.xml
report.html
```

After:
```
output/
.HA_VERSION
.pytest_cache/
```

Removed: `.pabotsuitenames`, `log.html`, `output.xml`, `report.html` (Robot artifacts).
Added: `.pytest_cache/`.

## `AGENTS.md` updates

### "Running the tests" section

Replace Robot commands with:

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

### "Interpreting the output" section

- `output/` dir still holds logs.
- Unit: `output/logs/<module_name>/<test_name>[_param_ids].log` per test (e.g. `output/logs/test_enabler/test_value_enabler_on-True-value_on.log`).
- Integration: `output/hass/` (homeassistant.log, .stdout, .stderr), `output/appdaemon/` (appdaemon.stdout, appdaemon.stderr, error.log, appdaemon.log).
- pytest terminal output: pass/fail summary, `--tb=short` for tracebacks.
- `report.html` / `log.html` / `output.xml` no longer generated.

### Other AGENTS.md sections

- "Setting up virtual environment": `./test/setup_virtualenv.sh test|hass|appdaemon|all`
- "Upgrading dependencies": `test/dependencies/test/` instead of `test/dependencies/robot/`
- "Building the CI Docker image": update paths
- Verification section: `pytest` commands instead of `run-test`
