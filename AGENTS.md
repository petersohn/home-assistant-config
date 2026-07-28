# Home Assistant Config

This repo contains a configuration for Home Assistant. It consists of the following parts:

- A set of AppDaemon apps and the corresponding config file.
- Home Assistant config files.

## Project structure

The project is structured so that it can be installed by Homeshick into the home directory of the Home Assistant server.

- `home/`: The root of the remote home. Anything here is visible to Home Assitant.
  - `.homeassistant/`
    - `configuration.yaml`: the entry point of the Home Assistant configuration.
    - `ui-lovelace.yaml`: the main Home Assistant dashboard.
    - `*.yaml`: Other config files included from `configuration.yaml`.
    - `appdaemon/apps/`: AppDaemon configuration.
      - `hass.py`: Base class for all apps, extending AppDaemon's `Hass`.
      - `apps/`: The AppDaemon app modules (`.py` files).
      - `configs/`: AppDaemon app configuration files (`.yaml`). AppDaemon globs every `*.yaml`/`*.toml` under `appdaemon/apps/` recursively and merges them, so the app definitions are split across multiple files by functionality.
  - `.local/bin/`: script used from inside Home Assistant.
- `test/`
  - `setup_virtualenv.sh`: A script to set up virtualenv for local testing (CI has python packages pre-built in the container).
  - `appdaemon_unit_test/`: Unit tests for AppDaemon apps.
  - `appdaemon_integration_test/`: Integration tests for AppDaemon apps.
  - `docker/`: Docker configuration for CI.

## Home Assistant configuration

Some items in Home Assistant are configured from the UI. Those are not visible from this repo. Items that are configurable through YAML are here.

## AppDaemon

Each app is a reusable code snippet that are pulled in dynamically by AppDaemon. Dependency management is manual. The format of an app configuration:

```yaml
app_name:
  module: <module_name>
  class: <class_name>
  dependencies: <other apps used by the app>
  ...arguments
```

Because the Python modules are loaded dynamically, only modules loaded before the app is reachable. For this reason, dependencies need to be specified.

### Type narrowing

Prefer `assert isinstance(...)` over `cast(...)` for runtime type narrowing. `cast` lies to the type checker without verification; `assert isinstance` narrows the type and validates at runtime. Use `cast` only when the target type is structurally incompatible with the source (e.g. cross-module class identity mismatches where `isinstance` cannot hold), and document why.

### Production apps

Modules under `home/.homeassistant/appdaemon/apps/apps/` (configured via the `*.yaml` files in `home/.homeassistant/appdaemon/apps/configs/`, split by functionality):

- `hass.py` (`Hass`): Base class for all apps. Extends AppDaemon's `Hass` with REST API helpers (`load_history`, `load_states`) and the abstract `add_callback`/`remove_callback` contract used by enablers and history.
- `locker.py` (`Locker`): Provides named mutexes with deadlock detection via `mutex_graph`. Nearly every app grabs a mutex from here for thread-safe state updates.
- `mutex_graph.py`: Graph/DFS utilities used by `locker.py` to detect lock-acquisition cycles and refuse deadlock-prone lock orders.
- `expression.py` (`ExpressionEvaluator`): Evaluates Python expressions against live entity state, auto-tracks referenced entities/attributes, and fires a callback on change. Core primitive under `enabler`, `cover`, `alert`, and `timer_switch`.
- `enabler.py` (`Enabler` and subclasses): Boolean conditions with optional debounce delay and change callbacks. Variants: `ValueEnabler` (entity in a value set), `RangeEnabler` (min/max), `DateEnabler` (date range, wraps yearly), `HistoryEnabler` (history aggregate bounds), `MultiEnabler` (logical AND of enablers), `ExpressionEnabler` (expression-based), `ScriptEnabler` (manual enable/disable). Used to gate lights, switches, and covers.
- `auto_switch.py` (`AutoSwitch`, `MultiSwitcher`): Wraps a switch entity and keeps an `input_select` mode select in sync with its on/off state. Modes: `on`/`off` (always on/off, manual override), `auto` (switched programatically). Foundation that `EnabledSwitch` and `timer_switch` drive.
- `enabled_switch.py` (`EnabledSwitch`): Turns one or more target `AutoSwitch`es on/off based on an `Enabler`, with optional `on_guard`/`off_guard` enablers that must agree before switching on or off.
- `timer_switch.py` (`TimerSwitch`, `TimerSequence`):
  - `TimerSwitch` turns targets on when a sensor/expression triggers and off after a duration (motion lights, vehicle/person-detected lights). Timer starts at input release (1s input hold + 1m timer = 61s total time).
  - `TimerSequence` runs a possibly multi-step timed sequence of targets (gate opening, sprinkler schedule, arrival lights). Timer starts at input trigger (1s input hold + 1m timer = 1m total time, can shut off while input is still active). Rising and falling edge support.
- `cover.py` (`CoverController`): Drives a cover/blind position from an expression with `auto`/`manual`/`stable` modes selected via a `mode_switch` `input_select` and an optional settle `delay`. Modes:
  - `auto`: set to target position, then settle in `stable`.
  - `stable`: don't move automatically, target position change sets to `auto`.
  - `manual`: complete manual override, don't try to set position.
- `alert.py` (`AlertAggregator`): Aggregates many source entities into one alert `binary_sensor`, using per-source `trigger_expr`/`text_expr` and an optional `timeout` before firing. Powers availability, window, freeze, and air-quality alerts.
- `history.py` (`HistoryManager`, `ChangeTracker`, `AggregatedValue`, `Aggregator`):
  - `HistoryManager` buffers an entity's recent samples (persisted/restored across restarts).
  - `ChangeTracker` records state-change timestamps.
  - `AggregatedValue` publishes a derived sensor (aggregators: `mean`, `max`, `sum`, `Integral`, `Anglemean`, `DecaySum`) over a rolling interval.
  - `Aggregator` feeds `HistoryEnabler`.
- `temperature_basic.py` (`TemperatureBasic`): Controls a switch (e.g. heating pump) based on the difference between an outflow and inflow temperature sensor, with min/max outside bounds, a target difference, and hysteresis tolerance.
- `wind_direction.py` (`WindDirection`): Updates the mdi arrow icon on a wind-direction sensor based on its bearing.
- `custom_icon.py` (`CustomIcon`): Intended to swap mdi icons on entities based on on/off state; currently inactive (callbacks are stubbed out).

### Testing

There are two levels of testing:

- **Unit tests**: These use a mocked version of AppDaemon. Fast and deterministic. These test the functionality of the apps, along with exact timing and edge cases.
- **Integration tests**: These use a real Home Assistant and AppDaemon. Slow and nondeterministic. These test that the apps work in realistic conditions. No exact timing is tested. Basic functionality is tested, plus behavior that rely on AppDaemon's inner logic, such as reloading apps when the configuration changes. Integration tests are not necessary for every app, but should be added for more complex functionality, especially cross-app interactions.

#### Setting up virtual environment

To set up the virtual environment to run the tests, use this command:

```sh
./test/setup_virtualenv.sh
```

This command removes the venv if it exists, then reinstalls it using `uv`.

The venv is installed at `test/.venv` (Python 3.12). It contains test deps, AppDaemon, mypy, and basedpyright.

Requires `uv` to be installed: <https://docs.astral.sh/uv/getting-started/installation/>.

Requires Docker to be installed for integration tests: <https://docs.docker.com/get-docker/>.

#### Upgrading dependencies

The test environment is a uv project under `test/dependencies/appdaemon/` with a `pyproject.toml` (direct dependencies) and a `uv.lock` (pinned transitives).

To upgrade all dependencies to their latest compatible versions:

```sh
cd test/dependencies/appdaemon
uv lock --upgrade
```

To upgrade a single package:

```sh
cd test/dependencies/appdaemon
uv lock --upgrade-package <name>
```

To add or remove a dependency, edit `dependencies` in `pyproject.toml` and run `uv lock`. Then commit the updated `uv.lock` (and `pyproject.toml` if it changed).

#### Running the tests

To run the unit tests, first make sure that the venv is installed. Then run:

```sh
# Unit tests
source test/.venv/bin/activate
pytest test/appdaemon_unit_test/ [-k <test>]
```

To run the integration tests, first make sure that the venv is installed and Docker is running. Then run:

```sh
# Integration tests
source test/.venv/bin/activate
pytest test/appdaemon_integration_test/ [-k <test>]
```

Integration tests start Home Assistant and AppDaemon as Docker containers via `docker compose`. The full integration test suite takes longer time to finish. Give it 5 minutes timeout.

Interpreting the output:

The test produces outputs in the `output` directory.

**Outputs common to all tests:**

- `output/` dir holds the logs generated during the run.
- pytest terminal output: pass/fail summary with tracebacks for failures.

**Outputs specific to unit tests:**

- `output/logs/<module_name>/<test_name>[_param_ids].log`: logs generated by one test.

**Outputs specific to integration tests:**

- `output/hass/`: Home Assistant configuration and logs.
  - `home-assistant.log`: output generated by Home Assistant.
- `output/appdaemon/`: AppDaemon configuration and logs.
  - `error.log`: error level logs generated by AppDaemon. Logs here usually indicate some problems during test execution.
  - `appdaemon.log`: lower level logs generated by AppDaemon. It has important information about the test run.

## Verification

Run these checks before claiming work complete. They are mandatory, not optional.

### After every change

- Type check (both mypy and basedpyright):

  ```sh
  bin/mypy
  bin/basedpyright
  ```

- Unit tests. Only the suites affected by the change are needed mid-task; run the full suite before handing off:

  ```sh
  source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v
  ```

Fix any failures and rerun before continuing. Do not leave the tree in a state where `bin/mypy`, `bin/basedpyright`, or the unit tests are red.

### At the end of a task or project

Run the integration tests once the full unit test suite is green and types are clean:

```sh
source test/.venv/bin/activate && cd test/appdaemon_integration_test && rm -rf output && pytest -v
```

Integration tests are slow and nondeterministic, so save them for the end. If a change is contained to one app, scope the run with `-k <test>`; otherwise run the full suite.
