# AppDaemon Directory Restructure & mypy Auto-Discovery

Date: 2026-07-25

## Goal

Restructure the prod AppDaemon `apps/` directory to separate code from config, remove the symlink farms in both test directories, and configure mypy to auto-discover all project `.py` files via `files = [app_dir, "."]` with only genuine noise in `exclude` — no project source file excluded.

## Background

### Current state

**Prod** (`home/.homeassistant/appdaemon/apps/` = AppDaemon `app_dir`): 14 `.py` modules + 17 `.yaml` configs + `hass.py` (thin base class extending `appdaemon.plugins.hass.hassapi.Hass`) all mixed in one flat dir. No `__init__.py`. App modules import each other by bare name (`import hass`, `import locker`).

**Unit tests** (`test/appdaemon_unit_test/apps/`): a symlink farm — 14 symlinks to prod `.py` modules, plus real files: `hass.py` (a ~600-line in-memory mock `AppManager` test harness, completely different from prod), `test_app.py`, `test_cover.py`, `__init__.py`. `conftest.py` inserts `apps/` into `sys.path` so `import hass` inside the symlinked prod files resolves to the **mock** `hass.py`, not prod. Test files import `from apps.hass import Hass`, `from apps.locker import Locker`, `from conftest import Harness`, `from unit_helpers.timing import Timing`.

**Integration tests** (`test/appdaemon_integration_test/config/appdaemon/apps/`): another symlink farm — 14 symlinks to prod `.py` + 3 real test-helper apps (`dummy.py`, `history_watcher.py`, `test_app.py`). Runtime assembly (`helpers/app_daemon.py:create_appdaemon_apps_config`) symlinks all `.py` from this dir into a runtime `apps/` dir and writes a merged `apps.yaml`.

**mypy** (`pyproject.toml`): uses an explicit 12-entry `files` allowlist because (a) prod lives under a dot-dir (`home/.homeassistant/...`) that mypy's crawl skips, and (b) the symlink farms create duplicate top-level module names if included. `exclude` lists venvs, output, cache, robotframework, the integration symlink farm, and one `conftest.py` (to avoid a duplicate-module collision).

### Why change

The explicit `files` allowlist means new `.py` files aren't auto-discovered. The symlink farms are the root cause of the duplicate-module exclusions. Removing the symlinks and restructuring lets mypy crawl everything via `files = [app_dir, "."]` with a minimal `exclude`.

### AppDaemon path resolution (validated)

AppDaemon 4.x "legacy" path mode (the default) does:
1. Adds `app_dir` itself to `sys.path` (`app_management.py:1016`).
2. Walks `app_dir` recursively via `os.walk`, adding every non-hidden, non-`__pycache__` subdir to `sys.path` (`app_management.py:1072-1076`).
3. Discovers `.yaml`/`.toml` config files recursively via `recursive_get_files` (skips dot-dirs).

So a nested `apps/` subdir and `configs/` subdir inside `app_dir` are both supported: modules in `apps/` are importable by bare name, configs in `configs/` are discovered and merged.

## Design

### New prod layout

`app_dir` stays `home/.homeassistant/appdaemon/apps/` (AppDaemon's default `config_dir/apps`; prod `appdaemon.yaml` lives outside the repo).

```
home/.homeassistant/appdaemon/apps/   <- app_dir (NO __init__.py — prod stays clean)
├── hass.py                           <- stays at root
├── configs/                          <- NEW subdir
│   └── *.yaml                        <- 17 yaml configs move here (NO __init__.py)
└── apps/                             <- NEW subdir
    └── *.py                          <- 14 app modules move here (NO __init__.py)
```

Files moved (git mv):
- `alert.py auto_switch.py cover.py custom_icon.py enabled_switch.py enabler.py expression.py history.py locker.py mutex_graph.py temperature_basic.py timer_switch.py wind_direction.py` → `apps/`
- `alerts.yaml base_enablers.yaml christmas_lights.yaml christmas_tree.yaml climate.yaml heating.yaml hot_water_pump.yaml icons.yaml locker.yaml motion_lights.yaml outside_lights.yaml sprinkler.yaml water_heater.yaml weather.yaml window_blinds.yaml wind.yaml` → `configs/`
- `hass.py` stays.

No `__init__.py` added to prod (per requirement: only tests get `__init__.py`).

**No prod `.py` import statements change.** All stay bare (`import hass`, `import locker`, `from hass import EntityValue`). AppDaemon legacy mode adds `app_dir` and `app_dir/apps` to `sys.path`, so:
- `import hass` → `app_dir/hass.py`
- `import auto_switch` → `app_dir/apps/auto_switch.py`
- `module: auto_switch` in configs → resolves from `apps/` on `sys.path`
- `*.yaml` in `configs/` → discovered recursively, merged

### New unit test layout

`test/` is the mypy_path root (not a package — no `__init__.py` there). `appdaemon_unit_test` and `appdaemon_integration_test` become top-level packages, so imports use `from appdaemon_unit_test.conftest import Harness` (no `test.` prefix).

```
test/                                  <- NO __init__.py (mypy_path root)
├── conftest.py                        <- empty (exists)
├── appdaemon_unit_test/               <- __init__.py NEW
│   ├── conftest.py                    <- edited
│   ├── test_helpers/                  <- renamed from unit_helpers/ (already has __init__.py)
│   │   ├── __init__.py                <- exists
│   │   ├── hass.py                    <- mock moves here (from apps/hass.py)
│   │   ├── config.py                  <- moves (from unit_helpers/)
│   │   ├── timing.py                  <- moves
│   │   ├── history_util.py            <- moves
│   │   ├── type_util.py               <- moves
│   │   ├── date_time_util.py          <- moves
│   │   ├── race_test_helper.py        <- moves
│   │   ├── test_app.py                <- moves (from apps/test_app.py)
│   │   └── test_cover.py              <- moves (from apps/test_cover.py)
│   ├── appdaemon_tests/               <- __init__.py NEW
│   └── 00_infrastructure_tests/       <- __init__.py NEW
```

The `apps/` dir is deleted entirely (symlinks + all real files moved to `test_helpers/`).
`unit_helpers/` is renamed to `test_helpers/` (per requirement).

**`conftest.py` changes:**
- `sys.path.insert(0, test_helpers_dir)` — mock `hass.py` first, shadows prod
- `sys.path.insert(1, app_dir/apps)` — prod app modules
- Remove old `sys.path.insert(0, apps_dir)`
- Imports become fully-qualified (no `test.` prefix — `test/` is the mypy_path root):
  - `from appdaemon_unit_test.test_helpers.hass import AppManager, Hass`
  - `from appdaemon_unit_test.test_helpers.config import create_app_manager`
  - `from appdaemon_unit_test.test_helpers.timing import Timing`
  - `from test_app import TestApp` (bare, from `test_helpers/` on sys.path)

**Prod modules imported by test code** (bare, from `app_dir/apps/` on sys.path / top-level for mypy):
- `from mutex_graph import find_cycle, append_graph` (was `from apps.mutex_graph import ...`)
- `from locker import Locker` (was `from apps.locker import ...`)

These resolve at runtime because `app_dir/apps` is on `sys.path`; for mypy they're top-level modules from the `app_dir` files entry.

**`test_app.py` / `test_cover.py` imports:** These files subclass `hass.Hass` and call mock-only methods (`_register_service`). They must import the mock `Hass` for mypy:
- `from appdaemon_unit_test.test_helpers.hass import Hass` (fully-qualified mock)
- `class TestApp(Hass):` / `class TestCover(Hass):`

At runtime, these files are loaded via `__import__("test_app")` from `test_helpers/` on `sys.path`. The fully-qualified import works because `appdaemon_unit_test` is a package importable via the `test/` mypy_path/sys.path root. `TestApp` subclasses the package-imported mock `Hass`. Prod modules (e.g. `alert.py`) subclass bare-`hass`-mock `Hass` (different module object). No `isinstance`/`issubclass` checks cross the two (verified: no such checks in unit test code). Harmless.

**All other test file imports:**
- `from conftest import Harness` → `from appdaemon_unit_test.conftest import Harness` (11 files)
- `from apps.hass import Hass` → `from hass import Hass` (bare — resolves to mock at runtime via sys.path, to prod for mypy; works because test code types subclass-specific vars as `Any`, and `Hass`-typed vars don't call mock-only methods — verified)
- `from apps.locker import Locker` → `from locker import Locker` (bare prod module)
- `from apps.test_app import TestApp` → `from test_app import TestApp` (bare, from `test_helpers/` on sys.path)
- `from unit_helpers.X import` → `from appdaemon_unit_test.test_helpers.X import` (fully-qualified)
- `from apps import hass` (in `config.py`, `race_test_helper.py`) → `from appdaemon_unit_test.test_helpers import hass` (fully-qualified mock, because these files reference `AppManager` which is mock-only)

**`race_test_helper.py` special case:** Uses `hass_module.AppManager` and patches `hass_module.Hass.load_history`. Must use the mock for mypy. The `TYPE_CHECKING` block: `from appdaemon_unit_test.test_helpers import hass as hass_module`. The runtime block: `hass_module = sys.modules.get("hass") or __import__("hass")` (gets bare mock from sys.path). Typing annotations use the fully-qualified mock; runtime uses the bare mock. Both are the mock — consistent.

### New integration test layout

```
test/appdaemon_integration_test/      <- __init__.py NEW
├── conftest.py
├── helpers/                          <- __init__.py exists
├── test_apps/                        <- NEW dir (real test-helper app files)
│   ├── __init__.py                   <- NEW
│   ├── dummy.py                      <- moves (from config/appdaemon/apps/dummy.py)
│   ├── history_watcher.py            <- moves
│   └── test_app.py                   <- moves
└── config/
    └── appdaemon/
        ├── appdaemon.yaml            <- stays
        ├── configs/                  <- existing (per-test yaml configs)
        └── apps/                     <- DELETED (symlink farm + 3 files gone)
```

The 3 test-helper `.py` files move from `config/appdaemon/apps/` to `test_apps/` (with `__init__.py`). The symlink farm is deleted.

**Runtime assembly** (`helpers/app_daemon.py:create_appdaemon_apps_config`) changes to build the runtime `apps/` dir per the new structure:
- `apps/hass.py` → symlink to prod `app_dir/hass.py`
- `apps/apps/` → symlink each prod `.py` from `app_dir/apps/` into `apps/apps/` (or symlink the whole dir — but individual files are safer for AppDaemon's file watcher)
- `apps/configs/` → create dir, copy/symlink yaml configs from `config/appdaemon/configs/` (existing logic for merging `apps.yaml` stays)
- `apps/test_apps/` → symlink the 3 test-helper `.py` files from `test_apps/`

AppDaemon legacy mode then adds `apps/`, `apps/apps/`, `apps/configs/` (no `.py`, harmless), `apps/test_apps/` to `sys.path`. `import hass` → `apps/hass.py`. `import auto_switch` → `apps/apps/auto_switch.py`. `import dummy` → `apps/test_apps/dummy.py`. All resolve.

The `directories.py` helper gains a path to the prod `app_dir` (`home/.homeassistant/appdaemon/apps`) for symlinking.

### mypy config

After restructure, no symlink farms → no duplicate modules. The mock `hass` is `appdaemon_unit_test.test_helpers.hass` (namespaced via `__init__.py`), prod `hass` is top-level `hass` — no collision. The two `conftest.py` are `appdaemon_unit_test.conftest` and `appdaemon_integration_test.conftest` — no collision. The root `test/conftest.py` is bare `conftest` (the only one at the mypy_path root) — no collision.

```toml
[tool.mypy]
warn_no_return = true
disallow_untyped_defs = true
disallow_untyped_calls = true
explicit_package_bases = true
mypy_path = ["test"]
files = [
    "home/.homeassistant/appdaemon/apps",  # dot-dir, mypy crawl skips it
    ".",
]
exclude = [
    "test/appdaemon_integration_test/.appdaemon/",
    "test/appdaemon_integration_test/.hass/",
    "test/appdaemon_integration_test/output/",
    "test/.venv/",
    "\\.mypy_cache/",
]
```

- `mypy_path = ["test"]` — `test/` is the package root; `appdaemon_unit_test` and `appdaemon_integration_test` become top-level packages (imports use `from appdaemon_unit_test.conftest import Harness`, no `test.` prefix).
- No project source file excluded.
- The `robotframework-httplibrary/` exclude entry is gone — the submodule is deleted (see "Robot Framework cleanup" below).
- The `[[tool.mypy.overrides]] module = "apps.hass"` → removed (module name changes to `appdaemon_unit_test.test_helpers.hass`). The `valid-type` disable may need to move to the new module name if the mock still triggers it.
- The `[[tool.mypy.overrides]] module = "conftest.*"` → update to `module = "appdaemon_unit_test.conftest"` (or `appdaemon_*_test.conftest`).

### Runtime import resolution summary

**Unit tests (at runtime):**
- `sys.path = [test_helpers_dir, app_dir/apps, ...pytest defaults...]`
- `import hass` → `test_helpers/hass.py` (mock, shadows prod)
- `import alert` → `app_dir/apps/alert.py` (prod); inside `alert.py`, `import hass` → mock (already cached)
- `import test_app` → `test_helpers/test_app.py` (loaded by `AppManager.create_app`)
- `from appdaemon_unit_test.test_helpers.hass import Hass` → mock via package (for type annotations in test code)

**Integration tests (at runtime, under AppDaemon):**
- AppDaemon adds `runtime_apps/`, `runtime_apps/apps/`, `runtime_apps/test_apps/` to `sys.path`
- `import hass` → `runtime_apps/hass.py` (symlink to prod)
- `import alert` → `runtime_apps/apps/alert.py` (symlink to prod)
- `import dummy` → `runtime_apps/test_apps/dummy.py` (symlink to test helper)

### mypy import resolution summary

- `import hass` (in prod `alert.py`) → prod `hass` (top-level, from `app_dir` files entry)
- `import hass` (in unit test files that use bare import) → prod `hass` (only top-level `hass` mypy sees; mock is namespaced). Works because test code types subclass-specific vars as `Any`.
- `from appdaemon_unit_test.test_helpers.hass import Hass` (in test files needing mock types) → mock `Hass`
- `from appdaemon_unit_test.conftest import Harness` → `Harness` class
- `from locker import Locker` (in test files) → prod `locker` (top-level from `app_dir/apps/`)

## What changes

1. **Move prod files** (git mv): 14 `.py` → `app_dir/apps/`, 17 `.yaml` → `app_dir/configs/`. `hass.py` stays.
2. **Delete** `test/appdaemon_unit_test/apps/` (symlinks + files).
3. **Rename** `test/appdaemon_unit_test/unit_helpers/` → `test_helpers/`.
4. **Move** mock `hass.py`, `test_app.py`, `test_cover.py` → `test_helpers/`.
5. **Add `__init__.py`** to: `test/appdaemon_unit_test/`, `test/appdaemon_unit_test/appdaemon_tests/`, `test/appdaemon_unit_test/00_infrastructure_tests/`, `test/appdaemon_integration_test/`, `test/appdaemon_integration_test/test_apps/`. (NOT `test/` — it's the mypy_path root. `test_helpers/__init__.py` already exists.)
6. **Delete** `test/appdaemon_integration_test/config/appdaemon/apps/` (symlink farm + 3 files).
7. **Move** 3 test-helper `.py` → `test/appdaemon_integration_test/test_apps/`.
8. **Edit** `test/appdaemon_unit_test/conftest.py`: sys.path + imports.
9. **Edit** all 28 unit test files: import path changes.
10. **Edit** `test/appdaemon_integration_test/helpers/app_daemon.py`: new runtime assembly logic.
11. **Edit** `test/appdaemon_integration_test/helpers/directories.py`: add prod `app_dir` path.
12. **Edit** `pyproject.toml`: simplify `files`/`exclude`, add `mypy_path = ["test"]`, remove `robotframework-httplibrary/` exclude, update overrides.
13. **Robot Framework cleanup** (see below): remove submodule, `.gitmodules` entry, AGENTS.md references, comments/docstrings.
14. **No changes** to any prod `.py` imports.

## Risks & mitigations

- **AppDaemon path resolution**: Validated by reading `app_management.py` source (legacy mode walks subdirs). Integration tests are the real validation — must run them.
- **Mock/prod `hass` double module object at runtime**: The mock is imported both as bare `hass` (by prod modules via sys.path) and as `appdaemon_unit_test.test_helpers.hass` (by test code via package). Two module objects, same file. `isinstance`/`issubclass` across them would fail. Verified: no such checks in unit test code. Harmless.
- **mypy typing test code against prod `Hass`**: Test code that calls mock-only methods (e.g. `_register_service`) uses `Any`-typed variables (verified). `Hass`-typed variables don't call mock-only methods (verified). Files that reference mock-only types (`AppManager`) use fully-qualified mock imports. Validated empirically with a realistic repro.
- **`test_helpers/` on sys.path shadows everything**: `test_helpers/` contains `hass.py` (mock), `test_app.py`, `test_cover.py`, `config.py`, etc. Putting it first on sys.path means `import config` would resolve to `test_helpers/config.py` — but no prod module imports `config`. `import timing` → `test_helpers/timing.py` — no prod module imports `timing`. Safe (prod module names are distinct from test helper names).

## Robot Framework cleanup

The repo carries dead Robot Framework infrastructure. Delete all of it:

1. **`robotframework-httplibrary/`** — git submodule (gitlink in index + `.gitmodules` entry). Remove: `git rm robotframework-httplibrary` (removes gitlink), delete the `.gitmodules` entry.
2. **`pyproject.toml`** — remove the `"robotframework-httplibrary/"` line from `exclude`.
3. **`AGENTS.md`**:
   - Delete line 21: `` - `robotframework-httplibrary/`: Third party testing library. Don't modify this. ``
   - Delete line 161: `` - `report.html` / `log.html` / `output.xml` are no longer generated (Robot Framework outputs). ``
4. **`test/appdaemon_integration_test/helpers/type_util.py:22`** — rewrite the `values_equal` docstring to drop the Robot Framework reference; keep the semantic description ("if both values can be converted to floats, compare them numerically ...").
5. **5 unit test files** — drop the parenthetical "(matching the original Robot harness)" from the `00:00:00` comments:
   - `test/appdaemon_unit_test/appdaemon_tests/test_alert.py:14`
   - `test/appdaemon_unit_test/appdaemon_tests/test_auto_switch.py:9`
   - `test/appdaemon_unit_test/appdaemon_tests/test_cover.py:8`
   - `test/appdaemon_unit_test/appdaemon_tests/test_history_manager.py:11`
   - `test/appdaemon_unit_test/appdaemon_tests/test_timer_switch.py:9`

No functional code changes — comments/docstrings only, plus the submodule removal.

## Verification

1. `bin/mypy` — clean, no project files excluded.
2. Unit tests: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v`
3. Integration tests: `source test/.venv/bin/activate && cd test/appdaemon_integration_test && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" pytest -v` (5 min timeout — validates the new layout works with real AppDaemon).