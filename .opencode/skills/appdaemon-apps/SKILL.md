---
name: appdaemon-apps
description: Use when writing or modifying AppDaemon apps under home/.homeassistant/appdaemon/apps/*.py. Records the project's conventions: derive from the local hass.Hass base, mutex locking discipline, unit testing, callback registration/cleanup pairing, and appdaemon API usage. Trigger on "appdaemon app", editing apps/*.py, adding a new app, or writing appdaemon tests.
---

# AppDaemon app conventions

Applies to all code under `home/.homeassistant/appdaemon/apps/` and tests under `test/AppDaemonUnitTest/apps/` (unit) and `test/AppDaemonIntegrationTest/` (integration).

## Base class

- Derive every app from the **local** `hass.Hass` (`from apps import hass` in tests, `import hass` in production), NOT from `appdaemon.plugins.hass.hassapi.Hass` directly.

  ```python
  import hass

  class MyThing(hass.Hass):
      def initialize(self) -> None: ...
  ```

- The local `Hass` (`home/.homeassistant/appdaemon/apps/hass.py:13`) extends AppDaemon's class with REST helpers (`load_history`, `load_states`) and declares the `add_callback`/`remove_callback` abstract contract. The unit-test harness mocks the local class — bypassing it means tests can't drive your app.

## Mutex discipline

Acquire mutexes from `locker`:

```python
import locker
locker_app = self.get_app("locker")
assert isinstance(locker_app, locker.Locker)
self.mutex = locker_app.get_mutex("MyThing")
```

`locker.get_mutex()` runs graph/DFS deadlock detection during tests (`mutex_graph.py`); always go through it, never raw `threading.Lock()`.

Rules (verified across existing apps):

- **Any local state mutation after `initialize()` must be guarded by `self.mutex`.** Reads of mutable state shared across threads belong inside the lock too.
- **Public methods are called from an unlocked state and acquire the lock themselves.**

  ```python
  def handle_change(self, value: bool) -> None:   # public — locks
      with self.mutex.lock("handle_change"):
          self._handle_change(value)
  ```

- **Private methods (leading underscore) are called already locked and do NOT lock again.**

  ```python
  def _handle_change(self, value: bool) -> None:  # private — caller holds lock
      self.value = value
      # do something
  ```

- **Corollary: callbacks call public methods.** An AppDaemon state/timer callback is invoked unlocked, so it should call a public method (which locks) rather than a private one (which assumes the lock is held). Pattern from `alert.py:39` / `alert.py:69`.

- Lock-name string passed to `self.mutex.lock("<name>")` is used in deadlock-cycle reporting; keep it descriptive and unique per call site (typically `"function_name"`).

## Callbacks registration / cleanup pairing

- Any callback-registration API you expose on an app MUST have a matching removal API. See `hass.py:14` (`add_callback`) / `hass.py:17` (`remove_callback`), `enabler.py:80`/`enabler.py:88`, `history.py:57`/`history.py:64`.
- When you register callbacks in OTHER apps, always unregister them in `terminate()`:

  ```python
  def initialize(self) -> None:
      enabler_app = self.get_app(enabler_name)
      assert isinstance(enabler_app, enabler_mod.Enabler)
      self.enabler: enabler.Enabler = enabler_app
      self.enabler_id: int = enabler_app.add_callback(self._on_change)

  def terminate(self) -> None:
      self.enabler.remove_callback(self.enabler_id)
  ```

- Registering callbacks in our own app doesn't require explicit cleanup. They are cleaned up automatically by AppDaemon.
- Also cancel timers (`cancel_timer`) and clean up `ExpressionEvaluator`s (`cleanup()`) in `terminate()`. Examples: `enabler.py:28`, `cover.py:71`, `timer_switch.py:178`, `expression.py:58`.

## `initialize()` and arguments

- Read all config from `self.args` inside `initialize()` and save to instance attributes. Never touch `self.args` after `initialize()` returns.
- Typed conversions happen at read time:

  ```python
  self.target: str = self.args["target"]
  delay = self.args.get("delay")
  self.delay: datetime.timedelta | None = (
      datetime.timedelta(**delay) if delay is not None else None
  )
  ```

- `get_app("locker")` and mutex setup happen in `initialize()` (deferred `import locker` inside the method is the established pattern so AppDaemon's dynamic loader sees dependencies).
- Declare app config in `apps.yaml` with `module:`, `class:`, and `dependencies:` listing any other apps used (needed because modules load dynamically).

## Datetime

- Do NOT use Python's date/time query functions (`datetime.datetime.now()`, `time.time()`, etc.). Call AppDaemon's time helpers so the test harness can inject simulated time:
  - `self.datetime()` — current simulated datetime.
  - `self.date()` — current simulated date.
- `datetime.timedelta` construction for offsets is fine; only the *current time source* must go through AppDaemon. See `history.py:102`, `expression.py:86`.

## Unit tests

- Always write unit tests for new/changed behavior. Tests live in `test/AppDaemonUnitTest/AppDaemonSuite/AppNameTest.robot` (for `app_name.py`).
- The app source is symlinked in `test/AppDaemonUnitTest/apps`.
- Other, non-symlink, files in `test/AppDaemonUnitTest/apps` are used in the test harness.
  - `hass.py`: Mocked version of the production `hass.py`. Provides the same interface but doesn't use real AppDaemon.
  - `test_app.py`: Basic test harness app. Contains methods the tests use to interact with the mocked AppDaemon.
  - `test_cover.py`: Mocked version of a real Home Assistant Cover (gate, window blind, etc.). Used to test the `Cover` app.
- Tests use the mocked AppDaemon harness in `test/AppDaemonUnitTest/`; they are fast and deterministic and assert exact timing and edge cases.
- Run affected suites mid-task, full suite before hand-off:
  ```sh
  source test/.venv/bin/activate && cd test/AppDaemonUnitTest && rm -rf output && ./run-test -LTRACE [-s <suite> | -t <test>]
  ```
- Unit tests must exist for any new/changed behavior. Integration tests (below) run only at the end of a task, once unit tests and `bin/mypy` are green.

## Integration tests

Integration tests use real Home Assistant + AppDaemon instances (started by the test harness), so they exercise AppDaemon's actual lifecycle, state-change dispatch, and app reloading — behavior the unit-test mock can't reproduce. They are slow and nondeterministic; **not needed for every app**, but add them for more complex functionality, especially cross-app interactions.

Architecture (rooted at `test/AppDaemonIntegrationTest/`):

- **Suites**: `AppDaemonSuite/<AppName>Test.robot` — one file per app or interaction under test. Per-test `Test Setup  Initialize Apps Configs <config>...` loads the specific app config snippets; `Test Teardown  Cleanup Apps Configs` unloads them (see `resourcourcces/Config.robot`).
- **Suite init**: `AppDaemonSuite/__init__.robot` runs once per suite: initializes variables, starts Home Assistant, starts AppDaemon, and after all tests runs `Check Global Mutex Graph` to confirm no deadlocks were introduced.
- **Real processes**:
  - `./hass` wrapper launches `${HASS_PATH}/bin/hass`; `./appdaemon` wrapper launches `${APPDAEMON_PATH}/bin/appdaemon`. Both venvs must be installed first (see AGENTS.md "Setting up virtual environment").
  - `resources/HomeAssistant.robot` drives HASS via its REST API (`/api/states`, service calls) to set inputs, poll outputs, clean states and purge history between tests.
  - `resources/AppDaemon.robot` drives AppDaemon via its REST admin API (`POST /api/appdaemon/TestApp`) through the `TestApp` module to call methods (`get_state`, `set_state`, `select_option`, `turn_on/off`, `call_service`) on the running apps.
- **Test app modules** under `config/appdaemon/apps/` (symlinked into the per-run `apps/` dir by `libraries/app_daemon.py`):
  - `test_app.py`: same role as the unit-test `test_app.py` — a `hass.Hass` subclass exposing test-driver methods (`schedule_call_in`, `call_on_app`, `get_state_as`, `get_next_time_of_day`), but reachable over HTTP so Robot can invoke methods on any running app.
  - `dummy.py`, `history_watcher.py`: helpers for side-effect-free targets / change observation.
  - Add new helpers here when a test needs a stand-in entity or a thin observer app.
- **App configs** under `config/appdaemon/configs/<Name>.yaml` are small `apps.yaml` fragments (one app each, or a few cooperating apps) that get merged into the run-time `apps.yaml` for the test. Example `Cover1.yaml`:
  ```yaml
  test_cover:
    class: CoverController
    module: cover
    target: cover.test_cover
    mode_switch: input_select.test_cover_mode
    expr: v.sensor.test_cover_position1
    dependencies:
      - locker
  ```
  Add a new `<Feature>.yaml` for each integration test scenario; declare cooperating apps and `dependencies:` exactly as in production `apps.yaml`.
- **Outputs** (in `output/`): `hass/homeassistant.log`, `appdaemon/appdaemon.log`, `appdaemon/error.log` (errors here usually indicate a real failure), `log.html`, `report.html`, `output.xml`.

Run (full or scoped):
```sh
source test/.venv/bin/activate && cd test/AppDaemonIntegrationTest && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" ./run-test -LTRACE --removekeywords WUKS [-s <suite> | -t <test>]
```
Scope with `-s <suite>` / `-t <test>` when a change is contained to one app; otherwise run the full suite. Exact timing is not asserted — use `Wait Until Keyword Succeeds` / `Wait For State` for nondeterministic waits.

## AppDaemon API reference (short)

Use these through `self.` on the local `Hass`. Descriptions:

- `get_app(name)` — returns another running app instance by its `apps.yaml` key; used to reach `locker` and dependencies.
- `get_state(entity_id=None, attribute=None, ...)` — read an entity's state (string) or, with `attribute="all"`, the full `{state, attributes}` dict. Returns `None` if unavailable.
- `set_state(entity_id, state=None, attributes=None, ...)` — push a state/attributes update to Home Assistant (used to publish derived sensors and alert binary_sensors).
- `listen_state(callback, entity_id=None, ...)` — register a state-change callback `callback(entity, attribute, old, new, **kwargs)`. Pair with lifecycle.
- `listen_event(callback, event=None, ...)` — register an event callback.
- `run_in(callback, delay, *args, **kwargs)` — schedule `callback(kwargs)` after `delay` seconds (int/float). Returns a timer handle; cancel with `cancel_timer`.
- `run_at(callback, time, *args, **kwargs)` — schedule at a `datetime.time` or `datetime.datetime`.
- `run_daily(callback, time, *args, **kwargs)` — schedule a recurring daily callback at a `datetime.time`.
- `cancel_timer(handle)` — cancel a previously scheduled timer; check for `None` before calling (apps store handles as `str | None`).
- `datetime()` — AppDaemon's simulated current datetime. Use this instead of `datetime.datetime.now()`.
- `date()` — AppDaemon's simulated current date. Use this instead of `datetime.date.today()`.
- `log(msg)` — info log. `error(msg)` — error log. Prefer over raw `print`.

Prefer expression/history/enabler composition over ad-hoc listeners where the behavior fits an existing primitive (see AGENTS.md "Production apps").

## Checklist before handing off

- [ ] Derives from local `hass.Hass`.
- [ ] Mutex acquired from `locker.get_mutex()`; all post-`initialize()` state mutations guarded.
- [ ] Public methods lock; private methods assume locked; callbacks route through public methods.
- [ ] Callback-registration APIs paired with removal; `terminate()` unregisters everything and cancels timers.
- [ ] `self.args` consumed only in `initialize()`, saved to instance attrs.
- [ ] Current time via `self.datetime()`/`self.date()`, not Python's `now()`/`today()`.
- [ ] Unit tests written; `./run-test -LTRACE` green for affected suites.
- [ ] `bin/mypy` clean.
- [ ] Integration tests added/scoped for complex or cross-app behavior; full integration suite green before hand-off.
