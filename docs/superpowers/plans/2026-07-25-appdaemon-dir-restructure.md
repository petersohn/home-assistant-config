# AppDaemon Directory Restructure & mypy Auto-Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the prod AppDaemon `apps/` dir (separate code/config), remove symlink farms in both test dirs, delete the Robot Framework submodule, and configure mypy to auto-discover all project `.py` files with no project source excluded.

**Architecture:** Prod `app_dir` gains `apps/` (14 `.py` modules) and `configs/` (17 `.yaml`) subdirs; `hass.py` stays at root. Unit tests: delete `apps/` symlink farm, move mock `hass.py` + test apps into renamed `test_helpers/` (from `unit_helpers/`), add `__init__.py` to test packages so mypy namespaces them (`appdaemon_unit_test.*`). Integration tests: delete symlink farm, move 3 test-helper apps to `test_apps/`, rewrite runtime assembly to symlink prod `hass.py` + `apps/` + `test_apps/` into the runtime dir. mypy: `mypy_path = ["test"]`, `files = [app_dir, "."]`, minimal `exclude`.

**Tech Stack:** AppDaemon 4.x (legacy path mode), pytest (`--import-mode=importlib`), mypy (explicit_package_bases), git submodules.

## Global Constraints

- **No `__init__.py` in prod** (`home/.homeassistant/appdaemon/apps/`, `apps/`, `configs/`). Only tests get `__init__.py`.
- **No `__init__.py` in `test/`** — it's the mypy_path root, not a package.
- **No prod `.py` import statements change** — all stay bare (`import hass`, `import locker`).
- **No project `.py` file excluded from mypy** — only venvs, output dirs, `.mypy_cache`.
- Test imports use `from appdaemon_unit_test...` / `from appdaemon_integration_test...` (no `test.` prefix — `test/` is the mypy_path root).
- Verification commands: `bin/mypy` (type check), unit tests `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v`, integration tests `source test/.venv/bin/activate && cd test/appdaemon_integration_test && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" pytest -v` (5 min timeout).

---

## File Structure

**Prod (moved, no new files):**
- `home/.homeassistant/appdaemon/apps/hass.py` — stays at root
- `home/.homeassistant/appdaemon/apps/apps/*.py` — 14 modules move here (git mv)
- `home/.homeassistant/appdaemon/apps/configs/*.yaml` — 17 configs move here (git mv)

**Unit tests (restructured):**
- `test/appdaemon_unit_test/__init__.py` — NEW
- `test/appdaemon_unit_test/00_infrastructure_tests/__init__.py` — NEW
- `test/appdaemon_unit_test/conftest.py` — edited (sys.path + imports)
- `test/appdaemon_unit_test/test_helpers/` — renamed from `unit_helpers/` (has `__init__.py`)
  - `hass.py` — moves from `apps/hass.py` (mock, ~600 lines)
  - `test_app.py` — moves from `apps/test_app.py` (import edited)
  - `test_cover.py` — moves from `apps/test_cover.py` (import edited)
  - `config.py`, `timing.py`, `history_util.py`, `type_util.py`, `date_time_util.py`, `race_test_helper.py` — moves from `unit_helpers/` (imports edited)
- `test/appdaemon_unit_test/apps/` — DELETED
- 28 unit test files — import edits

**Integration tests (restructured):**
- `test/appdaemon_integration_test/__init__.py` — NEW
- `test/appdaemon_integration_test/test_apps/` — NEW dir
  - `__init__.py` — NEW
  - `dummy.py`, `history_watcher.py`, `test_app.py` — move from `config/appdaemon/apps/`
- `test/appdaemon_integration_test/config/appdaemon/apps/` — DELETED
- `test/appdaemon_integration_test/conftest.py` — imports edited
- `test/appdaemon_integration_test/helpers/app_daemon.py` — runtime assembly rewritten
- `test/appdaemon_integration_test/helpers/directories.py` — add prod app_dir path
- `test/appdaemon_integration_test/helpers/appdaemon_client.py` — imports edited
- `test/appdaemon_integration_test/helpers/history_watcher.py` — imports edited
- `test/appdaemon_integration_test/helpers/home_assistant.py` — imports edited
- `test/appdaemon_integration_test/helpers/error_log.py` — imports edited
- `test/appdaemon_integration_test/integration_tests/*.py` — imports edited (4 files)

**Config / docs:**
- `pyproject.toml` — mypy config rewritten
- `AGENTS.md` — robot refs deleted, prod layout updated
- `.gitmodules` — robotframework entry deleted
- `robotframework-httplibrary/` — submodule removed
- `test/appdaemon_integration_test/helpers/type_util.py` — docstring edited
- 5 unit test files — robot comment parentheticals deleted

---

### Task 1: Move prod `.py` modules into `apps/` subdir

**Files:**
- Move (git mv): `home/.homeassistant/appdaemon/apps/{alert,auto_switch,cover,custom_icon,enabled_switch,enabler,expression,history,locker,mutex_graph,temperature_basic,timer_switch,wind_direction}.py` → `home/.homeassistant/appdaemon/apps/apps/`

**Interfaces:**
- Produces: prod modules at `home/.homeassistant/appdaemon/apps/apps/*.py`. `hass.py` stays at `home/.homeassistant/appdaemon/apps/hass.py`. No import statements change.

- [ ] **Step 1: Create the `apps/` subdir and move the 13 `.py` files**

```bash
cd home/.homeassistant/appdaemon/apps
mkdir apps
git mv alert.py auto_switch.py cover.py custom_icon.py enabled_switch.py enabler.py expression.py history.py locker.py mutex_graph.py temperature_basic.py timer_switch.py wind_direction.py apps/
```

- [ ] **Step 2: Verify `hass.py` remains at root and `apps/` has the 13 files**

Run: `ls home/.homeassistant/appdaemon/apps/hass.py && ls home/.homeassistant/appdaemon/apps/apps/ | wc -l`
Expected: `hass.py` path prints, and `apps/` count is 13.

- [ ] **Step 3: Verify no prod import statements reference the old paths**

Run: `grep -rnE "^(import|from) " home/.homeassistant/appdaemon/apps/apps/*.py home/.homeassistant/appdaemon/apps/hass.py | grep -vE "(import|from) (hass|locker|expression|alert|enabler|auto_switch|cover|enabled_switch|timer_switch|history|mutex_graph|temperature_basic|custom_icon|wind_direction|appdaemon|datetime|http|json|dateutil|typing|urllib|os|copy|inspect|traceback|itertools|__future__)" | head`
Expected: no output (all imports are bare module names or stdlib/third-party — unchanged).

- [ ] **Step 4: Commit**

```bash
git add -A home/.homeassistant/appdaemon/apps/
git commit -m "refactor: move prod app modules into apps/ subdir"
```

---

### Task 2: Move prod `.yaml` configs into `configs/` subdir

**Files:**
- Move (git mv): 17 `.yaml` files → `home/.homeassistant/appdaemon/apps/configs/`

**Interfaces:**
- Produces: configs at `home/.homeassistant/appdaemon/apps/configs/*.yaml`. AppDaemon discovers them recursively.

- [ ] **Step 1: Create `configs/` and move all `.yaml` files**

```bash
cd home/.homeassistant/appdaemon/apps
mkdir configs
git mv alerts.yaml base_enablers.yaml christmas_lights.yaml christmas_tree.yaml climate.yaml heating.yaml hot_water_pump.yaml icons.yaml locker.yaml motion_lights.yaml outside_lights.yaml sprinkler.yaml water_heater.yaml weather.yaml window_blinds.yaml wind.yaml configs/
```

- [ ] **Step 2: Verify only `hass.py`, `apps/`, `configs/` remain at root**

Run: `ls home/.homeassistant/appdaemon/apps/`
Expected: `apps  configs  hass.py` (and maybe `__pycache__`).

- [ ] **Step 3: Verify all 17 yaml moved**

Run: `ls home/.homeassistant/appdaemon/apps/configs/*.yaml | wc -l`
Expected: `17`.

- [ ] **Step 4: Commit**

```bash
git add -A home/.homeassistant/appdaemon/apps/
git commit -m "refactor: move prod yaml configs into configs/ subdir"
```

---

### Task 3: Delete Robot Framework submodule and references

**Files:**
- Remove: `robotframework-httplibrary/` (git submodule gitlink)
- Modify: `.gitmodules` (delete the `[submodule "robotframework-httplibrary"]` block)
- Modify: `AGENTS.md:21` (delete the robotframework-httplibrary line)
- Modify: `AGENTS.md:161` (delete the report.html/log.html line)
- Modify: `test/appdaemon_integration_test/helpers/type_util.py:20-26` (rewrite docstring)
- Modify: 5 unit test files (delete robot comment parentheticals)

**Interfaces:**
- Produces: no more `robotframework-httplibrary/` dir, no robot refs in tracked files.

- [ ] **Step 1: Remove the git submodule**

```bash
git rm robotframework-httplibrary
```

- [ ] **Step 2: Delete the `.gitmodules` entry**

In `.gitmodules`, delete the 3-line block:
```
[submodule "robotframework-httplibrary"]
	path = robotframework-httplibrary
	url = ../robotframework-httplibrary.git
```
If `.gitmodules` becomes empty, delete the file.

- [ ] **Step 3: Delete the two AGENTS.md robot lines**

Delete line 21: `- \`robotframework-httplibrary/\`: Third party testing library. Don't modify this.`

Delete line 161 (now shifted; the line containing): `- \`report.html\` / \`log.html\` / \`output.xml\` are no longer generated (Robot Framework outputs).`

- [ ] **Step 4: Rewrite the `type_util.py` docstring**

In `test/appdaemon_integration_test/helpers/type_util.py`, replace the `values_equal` docstring (lines 20-26):

```python
    """Compare two values with numeric coercion.

    If both values can be converted to floats, compare them numerically so
    that a state string like ``"0"`` equals the expected float ``0.0``.
    Otherwise fall back to a direct equality check.
    """
```

- [ ] **Step 5: Delete the "(matching the original Robot harness)" parentheticals in 5 test files**

In each of these files, replace the comment:
- `test/appdaemon_unit_test/appdaemon_tests/test_alert.py:14`: `# Use 00:00:00 (matching the original Robot harness) so that absolute-time` → `# Use 00:00:00 so that absolute-time`
- `test/appdaemon_unit_test/appdaemon_tests/test_auto_switch.py:9`: `# Use 00:00:00 (matching the original Robot harness).` → `# Use 00:00:00.`
- `test/appdaemon_unit_test/appdaemon_tests/test_cover.py:8`: `# Use 00:00:00 (matching the original Robot harness).` → `# Use 00:00:00.`
- `test/appdaemon_unit_test/appdaemon_tests/test_history_manager.py:11`: `# Use 00:00:00 (matching the original Robot harness) so absolute-time` → `# Use 00:00:00 so absolute-time`
- `test/appdaemon_unit_test/appdaemon_tests/test_timer_switch.py:9`: `# Use 00:00:00 (matching the original Robot harness) so the absolute` → `# Use 00:00:00 so the absolute`

- [ ] **Step 6: Verify no robot refs remain in tracked files**

Run: `git grep -liE "robot" -- . ':(exclude)docs/' ':(exclude).opencode/'`
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove dead Robot Framework submodule and references"
```

---

### Task 4: Restructure unit test directory — move files, add `__init__.py`

**Files:**
- Delete: `test/appdaemon_unit_test/apps/` (symlinks + real files)
- Rename: `test/appdaemon_unit_test/unit_helpers/` → `test/appdaemon_unit_test/test_helpers/`
- Move: `apps/hass.py`, `apps/test_app.py`, `apps/test_cover.py` → `test_helpers/`
- Create: `test/appdaemon_unit_test/__init__.py`, `test/appdaemon_unit_test/00_infrastructure_tests/__init__.py`

**Interfaces:**
- Produces: `test/appdaemon_unit_test/test_helpers/` with mock `hass.py`, `test_app.py`, `test_cover.py`, and the renamed helper modules. `apps/` gone. `__init__.py` added for package namespacing. File contents (imports) not yet edited — that's Task 5.

- [ ] **Step 1: Rename `unit_helpers/` to `test_helpers/`**

```bash
git mv test/appdaemon_unit_test/unit_helpers test/appdaemon_unit_test/test_helpers
```

- [ ] **Step 2: Move the 3 real files from `apps/` into `test_helpers/`**

```bash
git mv test/appdaemon_unit_test/apps/hass.py test/appdaemon_unit_test/test_helpers/hass.py
git mv test/appdaemon_unit_test/apps/test_app.py test/appdaemon_unit_test/test_helpers/test_app.py
git mv test/appdaemon_unit_test/apps/test_cover.py test/appdaemon_unit_test/test_helpers/test_cover.py
```

- [ ] **Step 3: Delete the `apps/` dir (now only symlinks + `__init__.py`)**

```bash
git rm test/appdaemon_unit_test/apps/__init__.py
# Remove the remaining symlinks (git rm handles tracked symlinks)
git rm test/appdaemon_unit_test/apps/*.py 2>/dev/null || true
rm -rf test/appdaemon_unit_test/apps
```

- [ ] **Step 4: Add `__init__.py` files**

```bash
touch test/appdaemon_unit_test/__init__.py
touch test/appdaemon_unit_test/00_infrastructure_tests/__init__.py
```

Note: `test/appdaemon_unit_test/appdaemon_tests/__init__.py` already exists. `test/appdaemon_unit_test/test_helpers/__init__.py` already exists (renamed from `unit_helpers/__init__.py`).

- [ ] **Step 5: Verify structure**

Run: `find test/appdaemon_unit_test -name "__init__.py" | sort && echo "---" && ls test/appdaemon_unit_test/test_helpers/hass.py test/appdaemon_unit_test/test_helpers/test_app.py test/appdaemon_unit_test/test_helpers/test_cover.py && echo "---" && ls test/appdaemon_unit_test/apps 2>&1`
Expected: `__init__.py` files in `appdaemon_unit_test/`, `appdaemon_tests/`, `00_infrastructure_tests/`, `test_helpers/`; the 3 moved files exist; `apps/` does not exist.

- [ ] **Step 6: Commit**

```bash
git add -A test/appdaemon_unit_test/
git commit -m "refactor: restructure unit test dir (rename unit_helpers, move mock apps, add __init__.py)"
```

---

### Task 5: Rewrite unit test imports for new package structure

**Files:**
- Modify: `test/appdaemon_unit_test/conftest.py`
- Modify: `test/appdaemon_unit_test/test_helpers/config.py`
- Modify: `test/appdaemon_unit_test/test_helpers/race_test_helper.py`
- Modify: `test/appdaemon_unit_test/test_helpers/test_app.py`
- Modify: `test/appdaemon_unit_test/test_helpers/test_cover.py`
- Modify: 13 `test/appdaemon_unit_test/appdaemon_tests/test_*.py` files
- Modify: 4 `test/appdaemon_unit_test/00_infrastructure_tests/test_*.py` files

**Interfaces:**
- Produces: all unit test imports use `from appdaemon_unit_test...` (fully-qualified for test helpers/mock) or bare (`from hass import`, `from locker import`, `from test_app import`) for prod/modules on sys.path.

**Import rewrite rules (apply across all files):**
| Old | New | Files |
|-----|-----|-------|
| `from conftest import Harness` | `from appdaemon_unit_test.conftest import Harness` | 11 files |
| `from apps.hass import Hass` | `from hass import Hass` | 4 files |
| `from apps.hass import AppManager, Hass` | `from appdaemon_unit_test.test_helpers.hass import AppManager, Hass` | conftest.py |
| `from apps.locker import Locker` | `from locker import Locker` | conftest.py |
| `from apps.mutex_graph import find_cycle, append_graph` | `from mutex_graph import find_cycle, append_graph` | conftest.py, test_mutex_graph.py |
| `from apps.test_app import TestApp` | `from test_app import TestApp` | conftest.py |
| `from unit_helpers.config import create_app_manager` | `from appdaemon_unit_test.test_helpers.config import create_app_manager` | conftest.py |
| `from unit_helpers.timing import Timing` | `from appdaemon_unit_test.test_helpers.timing import Timing` | conftest.py + 6 test files |
| `from unit_helpers.history_util import ...` | `from appdaemon_unit_test.test_helpers.history_util import ...` | 4 files |
| `from unit_helpers.race_test_helper import patch_load_history` | `from appdaemon_unit_test.test_helpers.race_test_helper import patch_load_history` | test_history_manager.py |
| `from unit_helpers.type_util import ...` | `from appdaemon_unit_test.test_helpers.type_util import ...` | test_type_util.py |
| `from unit_helpers.date_time_util import ...` | `from appdaemon_unit_test.test_helpers.date_time_util import ...` | test_date_time_util.py |
| `from apps import hass` (in `config.py`) | `from appdaemon_unit_test.test_helpers import hass` | test_helpers/config.py |
| `from apps import hass` (in `test_app.py`) | `from appdaemon_unit_test.test_helpers.hass import Hass` + change `class TestApp(hass.Hass)` → `class TestApp(Hass)` | test_helpers/test_app.py |
| `from apps import hass` (in `test_cover.py`) | `from appdaemon_unit_test.test_helpers.hass import Hass` + change `class TestCover(hass.Hass)` → `class TestCover(Hass)` | test_helpers/test_cover.py |
| `from apps import hass as hass_module` (TYPE_CHECKING in `race_test_helper.py`) | `from appdaemon_unit_test.test_helpers import hass as hass_module` | test_helpers/race_test_helper.py |

- [ ] **Step 1: Rewrite `conftest.py`**

In `test/appdaemon_unit_test/conftest.py`, replace lines 8-18:

```python
_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "apps"))

import pytest
from unit_helpers.config import create_app_manager
from unit_helpers.timing import Timing
from apps.hass import AppManager, Hass
from apps.locker import Locker
from apps.mutex_graph import find_cycle, append_graph
from apps.test_app import TestApp
```

with:

```python
_HERE = os.path.dirname(__file__)
_APP_DIR = os.path.normpath(
    os.path.join(_HERE, "..", "..", "home", ".homeassistant", "appdaemon", "apps")
)
sys.path.insert(0, os.path.join(_HERE, "test_helpers"))
sys.path.insert(1, os.path.join(_APP_DIR, "apps"))

import pytest
from appdaemon_unit_test.test_helpers.config import create_app_manager
from appdaemon_unit_test.test_helpers.timing import Timing
from appdaemon_unit_test.test_helpers.hass import AppManager, Hass
from locker import Locker
from mutex_graph import find_cycle, append_graph
from test_app import TestApp
```

- [ ] **Step 2: Rewrite `test_helpers/config.py`**

In `test/appdaemon_unit_test/test_helpers/config.py`, replace line 2:
```python
from apps import hass
```
with:
```python
from appdaemon_unit_test.test_helpers import hass
```

- [ ] **Step 3: Rewrite `test_helpers/race_test_helper.py`**

In `test/appdaemon_unit_test/test_helpers/race_test_helper.py`, replace lines 9-12:
```python
if TYPE_CHECKING:
    from apps import hass as hass_module
else:
    hass_module = sys.modules.get("hass") or __import__("hass")
```
with:
```python
if TYPE_CHECKING:
    from appdaemon_unit_test.test_helpers import hass as hass_module
else:
    hass_module = sys.modules.get("hass") or __import__("hass")
```

- [ ] **Step 4: Rewrite `test_helpers/test_app.py`**

In `test/appdaemon_unit_test/test_helpers/test_app.py`, replace line 1:
```python
from apps import hass
```
with:
```python
from appdaemon_unit_test.test_helpers.hass import Hass
```
And replace line 21:
```python
class TestApp(hass.Hass):
```
with:
```python
class TestApp(Hass):
```

- [ ] **Step 5: Rewrite `test_helpers/test_cover.py`**

In `test/appdaemon_unit_test/test_helpers/test_cover.py`, replace line 2:
```python
from apps import hass
```
with:
```python
from appdaemon_unit_test.test_helpers.hass import Hass
```
And replace line 6:
```python
class TestCover(hass.Hass):
```
with:
```python
class TestCover(Hass):
```

- [ ] **Step 6: Rewrite the 13 `appdaemon_tests/test_*.py` files**

Apply the import rewrites per the table above. For each file, use the `edit` tool with `replaceAll` for the pattern `from conftest import Harness` → `from appdaemon_unit_test.conftest import Harness` across all files, then handle file-specific imports:

Files and their import changes:
- `test_alert.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from apps.hass import Hass`→`from hass import Hass`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`; `from unit_helpers.history_util import (`→`from appdaemon_unit_test.test_helpers.history_util import (`
- `test_auto_switch.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from apps.hass import Hass`→`from hass import Hass`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`
- `test_cover.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`
- `test_enabled_switch.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`
- `test_enabler.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`
- `test_expression_enabler.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`
- `test_expression.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`
- `test_history_manager.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from apps.hass import Hass`→`from hass import Hass`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`; `from unit_helpers.history_util import convert_history_input, convert_history_output`→`from appdaemon_unit_test.test_helpers.history_util import convert_history_input, convert_history_output`; `from unit_helpers.race_test_helper import patch_load_history`→`from appdaemon_unit_test.test_helpers.race_test_helper import patch_load_history`
- `test_temperature_basic.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`
- `test_timer_switch.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from apps.hass import Hass`→`from hass import Hass`; `from unit_helpers.history_util import convert_history_input, convert_history_output`→`from appdaemon_unit_test.test_helpers.history_util import convert_history_input, convert_history_output`

- [ ] **Step 7: Rewrite the 4 `00_infrastructure_tests/test_*.py` files**

- `test_date_time_util.py`: `from unit_helpers.date_time_util import to_time, find_time, add_times`→`from appdaemon_unit_test.test_helpers.date_time_util import to_time, find_time, add_times`
- `test_history_util.py`: `from unit_helpers.history_util import convert_history_input, convert_history_output`→`from appdaemon_unit_test.test_helpers.history_util import convert_history_input, convert_history_output`
- `test_mutex_graph.py`: `from apps.mutex_graph import find_cycle, append_graph`→`from mutex_graph import find_cycle, append_graph`
- `test_test_harness.py`: `from conftest import Harness`→`from appdaemon_unit_test.conftest import Harness`; `from unit_helpers.timing import Timing`→`from appdaemon_unit_test.test_helpers.timing import Timing`
- `test_type_util.py`: `from unit_helpers.type_util import extract_from_dictionary, repeat_item`→`from appdaemon_unit_test.test_helpers.type_util import extract_from_dictionary, repeat_item`

- [ ] **Step 8: Verify no old-style imports remain**

Run: `grep -rnE "from (conftest|apps|unit_helpers) import|from apps\." test/appdaemon_unit_test --include="*.py"`
Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add -A test/appdaemon_unit_test/
git commit -m "refactor: rewrite unit test imports for new package structure"
```

---

### Task 6: Run unit tests and mypy, fix issues

**Files:**
- Modify: any file with mypy/test failures (fix in place)

**Interfaces:**
- Produces: unit tests green, mypy clean (before mypy config rewrite in Task 9 — this is a checkpoint; mypy may still use old config but tests must pass).

- [ ] **Step 1: Run unit tests**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v 2>&1 | tail -30`
Expected: all tests pass (288 tests). If failures, fix the import issues in the failing files.

- [ ] **Step 2: If tests fail, debug and fix**

Common issues:
- `ModuleNotFoundError: No module named 'test_app'` → verify `test_helpers/` is on `sys.path` (conftest Step 1).
- `ModuleNotFoundError: No module named 'alert'` → verify `app_dir/apps` is on `sys.path` (conftest Step 1).
- `ImportError: cannot import name 'Harness'` → verify `from appdaemon_unit_test.conftest import Harness`.

Fix and rerun until green.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A test/appdaemon_unit_test/
git commit -m "fix: unit test import issues after restructure"
```

Only commit if there were fixes. If all green on first run, skip this step.

---

### Task 7: Restructure integration test directory — move test helper apps

**Files:**
- Delete: `test/appdaemon_integration_test/config/appdaemon/apps/` (symlink farm + 3 files)
- Create: `test/appdaemon_integration_test/test_apps/` with `__init__.py`
- Move: `dummy.py`, `history_watcher.py`, `test_app.py` → `test_apps/`
- Create: `test/appdaemon_integration_test/__init__.py`

**Interfaces:**
- Produces: `test_apps/` with the 3 real test-helper app files. `config/appdaemon/apps/` gone. `__init__.py` for package namespacing.

- [ ] **Step 1: Create `test_apps/` and move the 3 real files**

```bash
mkdir -p test/appdaemon_integration_test/test_apps
touch test/appdaemon_integration_test/test_apps/__init__.py
git mv test/appdaemon_integration_test/config/appdaemon/apps/dummy.py test/appdaemon_integration_test/test_apps/dummy.py
git mv test/appdaemon_integration_test/config/appdaemon/apps/history_watcher.py test/appdaemon_integration_test/test_apps/history_watcher.py
git mv test/appdaemon_integration_test/config/appdaemon/apps/test_app.py test/appdaemon_integration_test/test_apps/test_app.py
```

- [ ] **Step 2: Delete the `config/appdaemon/apps/` dir (now only symlinks)**

```bash
git rm test/appdaemon_integration_test/config/appdaemon/apps/*.py 2>/dev/null || true
rm -rf test/appdaemon_integration_test/config/appdaemon/apps
```

- [ ] **Step 3: Add `__init__.py` to the integration test package**

```bash
touch test/appdaemon_integration_test/__init__.py
```

Note: `test/appdaemon_integration_test/helpers/__init__.py` already exists.

- [ ] **Step 4: Verify structure**

Run: `ls test/appdaemon_integration_test/test_apps/ && echo "---" && ls test/appdaemon_integration_test/config/appdaemon/apps 2>&1 && echo "---" && ls test/appdaemon_integration_test/__init__.py`
Expected: `test_apps/` has `__init__.py`, `dummy.py`, `history_watcher.py`, `test_app.py`; `config/appdaemon/apps` does not exist; `__init__.py` exists.

- [ ] **Step 5: Commit**

```bash
git add -A test/appdaemon_integration_test/
git commit -m "refactor: move integration test helper apps to test_apps/, delete symlink farm"
```

---

### Task 8: Rewrite integration test runtime assembly and imports

**Files:**
- Modify: `test/appdaemon_integration_test/helpers/directories.py`
- Modify: `test/appdaemon_integration_test/helpers/app_daemon.py`
- Modify: `test/appdaemon_integration_test/conftest.py`
- Modify: `test/appdaemon_integration_test/helpers/appdaemon_client.py`
- Modify: `test/appdaemon_integration_test/helpers/history_watcher.py`
- Modify: `test/appdaemon_integration_test/helpers/home_assistant.py`
- Modify: `test/appdaemon_integration_test/helpers/error_log.py`
- Modify: `test/appdaemon_integration_test/integration_tests/test_cover.py`
- Modify: `test/appdaemon_integration_test/integration_tests/test_enabled_switch.py`
- Modify: `test/appdaemon_integration_test/integration_tests/test_history_manager.py`
- Modify: `test/appdaemon_integration_test/integration_tests/test_timer_switch.py`

**Interfaces:**
- Produces: `directories.py` gains `prod_app_dir` path. `app_daemon.py:create_appdaemon_apps_config` builds runtime `apps/` with `hass.py` (symlink prod), `apps/` (symlink prod modules), `configs/` (yaml), `test_apps/` (symlink test helpers). All `helpers.X` imports → `appdaemon_integration_test.helpers.X`.

- [ ] **Step 1: Add paths to `directories.py`**

In `test/appdaemon_integration_test/helpers/directories.py`, append two new paths. Full file becomes:

```python
import os

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_path, "config")
hass_config_path = os.path.join(config_path, "hass")
appdaemon_config_path = os.path.join(config_path, "appdaemon")
prod_app_dir = os.path.normpath(
    os.path.join(
        base_path, "..", "..", "home", ".homeassistant", "appdaemon", "apps"
    )
)
test_apps_path = os.path.join(base_path, "test_apps")
```

- [ ] **Step 2: Rewrite `app_daemon.py:create_appdaemon_apps_config`**

Replace the entire `create_appdaemon_apps_config` function (lines 34-72) with:

```python
def create_appdaemon_apps_config(
    target_directory: str, *app_configs: str
) -> list[str]:
    apps_dir = os.path.join(target_directory, "apps")
    apps_yaml = os.path.join(apps_dir, "apps.yaml")

    os.makedirs(apps_dir, exist_ok=True)

    content: dict[str, Any] = {}
    for config in app_configs:
        source_file = os.path.join(
            directories.appdaemon_config_path, "configs", config + ".yaml"
        )
        with open(source_file, "r") as source:
            content.update(yaml.safe_load(source))

    # hass.py at the root of the runtime apps dir (symlink to prod)
    hass_link = os.path.join(apps_dir, "hass.py")
    if os.path.exists(hass_link):
        os.remove(hass_link)
    os.symlink(os.path.join(directories.prod_app_dir, "hass.py"), hass_link)

    # apps/ subdir — symlink each prod .py module
    apps_subdir = os.path.join(apps_dir, "apps")
    os.makedirs(apps_subdir, exist_ok=True)
    prod_apps_subdir = os.path.join(directories.prod_app_dir, "apps")
    for file_name in os.listdir(prod_apps_subdir):
        if not file_name.endswith(".py"):
            continue
        target_file = os.path.join(apps_subdir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(os.path.join(prod_apps_subdir, file_name), target_file)

    # configs/ subdir — symlink yaml configs from the integration test config
    configs_subdir = os.path.join(apps_dir, "configs")
    os.makedirs(configs_subdir, exist_ok=True)
    source_configs = os.path.join(directories.appdaemon_config_path, "configs")
    for file_name in os.listdir(source_configs):
        if not file_name.endswith(".yaml"):
            continue
        target_file = os.path.join(configs_subdir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(os.path.join(source_configs, file_name), target_file)

    # test_apps/ subdir — symlink the test helper apps
    test_apps_subdir = os.path.join(apps_dir, "test_apps")
    os.makedirs(test_apps_subdir, exist_ok=True)
    for file_name in os.listdir(directories.test_apps_path):
        if not file_name.endswith(".py") or file_name == "__init__.py":
            continue
        target_file = os.path.join(test_apps_subdir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(
            os.path.join(directories.test_apps_path, file_name), target_file
        )

    all_apps = [
        name
        for name in content.keys()
        if name not in ["test", "locker"]
    ]

    fd, tmp = tempfile.mkstemp(
        dir=apps_dir, prefix=".apps.", suffix=".yaml"
    )
    with os.fdopen(fd, "w") as target:
        yaml.dump(content, target)
    os.replace(tmp, apps_yaml)

    return all_apps
```

- [ ] **Step 3: Rewrite `app_daemon.py` import**

In `test/appdaemon_integration_test/helpers/app_daemon.py`, replace line 4:
```python
from helpers import directories
```
with:
```python
from appdaemon_integration_test.helpers import directories
```

- [ ] **Step 4: Rewrite `conftest.py` imports**

In `test/appdaemon_integration_test/conftest.py`, replace lines 13-19:
```python
from helpers.home_assistant import create_home_assistant_configuration
from helpers.app_daemon import create_appdaemon_configuration
from helpers.process_check import find_processes_matching_cmdline
from helpers.hass_client import HassClient
from helpers.appdaemon_client import AppDaemonClient
from helpers.history_watcher import HistoryWatcher
from helpers.error_log import ErrorLogChecker
```
with:
```python
from appdaemon_integration_test.helpers.home_assistant import create_home_assistant_configuration
from appdaemon_integration_test.helpers.app_daemon import create_appdaemon_configuration
from appdaemon_integration_test.helpers.process_check import find_processes_matching_cmdline
from appdaemon_integration_test.helpers.hass_client import HassClient
from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.history_watcher import HistoryWatcher
from appdaemon_integration_test.helpers.error_log import ErrorLogChecker
```

Also replace line 92:
```python
    from helpers.app_daemon import create_appdaemon_apps_config
```
with:
```python
    from appdaemon_integration_test.helpers.app_daemon import create_appdaemon_apps_config
```

- [ ] **Step 5: Rewrite `appdaemon_client.py` imports**

In `test/appdaemon_integration_test/helpers/appdaemon_client.py`, replace lines 5-7:
```python
from helpers.app_daemon import create_appdaemon_apps_config
from helpers.mutex_graph import append_graph, find_cycle
from helpers.type_util import values_equal
```
with:
```python
from appdaemon_integration_test.helpers.app_daemon import create_appdaemon_apps_config
from appdaemon_integration_test.helpers.mutex_graph import append_graph, find_cycle
from appdaemon_integration_test.helpers.type_util import values_equal
```

- [ ] **Step 6: Rewrite `history_watcher.py` import**

In `test/appdaemon_integration_test/helpers/history_watcher.py`, replace line 5:
```python
from helpers.type_util import values_equal
```
with:
```python
from appdaemon_integration_test.helpers.type_util import values_equal
```

- [ ] **Step 7: Rewrite `home_assistant.py` import**

In `test/appdaemon_integration_test/helpers/home_assistant.py`, replace line 4:
```python
from helpers import directories
```
with:
```python
from appdaemon_integration_test.helpers import directories
```

- [ ] **Step 8: Verify `error_log.py` imports**

Run: `head -5 test/appdaemon_integration_test/helpers/error_log.py`
If it imports `from helpers...`, rewrite to `from appdaemon_integration_test.helpers...`. If it has no such imports, skip.

- [ ] **Step 9: Rewrite the 4 `integration_tests/test_*.py` files**

For each file, replace `from helpers.X import` → `from appdaemon_integration_test.helpers.X import`:
- `test_cover.py`: `from helpers.appdaemon_client import AppDaemonClient`→`from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient`; `from helpers.history_watcher import HistoryWatcher`→`from appdaemon_integration_test.helpers.history_watcher import HistoryWatcher`
- `test_enabled_switch.py`: same pattern for `appdaemon_client` and `history_watcher`
- `test_history_manager.py`: `from helpers.appdaemon_client import AppDaemonClient`→`from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient`; `from helpers.hass_client import HassClient`→`from appdaemon_integration_test.helpers.hass_client import HassClient`; `from helpers.history_util import convert_history_output`→`from appdaemon_integration_test.helpers.history_util import convert_history_output`; `from helpers.type_util import values_equal`→`from appdaemon_integration_test.helpers.type_util import values_equal`
- `test_timer_switch.py`: same pattern for `appdaemon_client` and `history_watcher`

- [ ] **Step 10: Verify no old-style `from helpers` imports remain**

Run: `grep -rnE "^from helpers" test/appdaemon_integration_test --include="*.py"`
Expected: no output.

- [ ] **Step 11: Commit**

```bash
git add -A test/appdaemon_integration_test/
git commit -m "refactor: rewrite integration test runtime assembly and imports"
```

---

### Task 9: Rewrite mypy config in `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: mypy auto-discovers all project `.py` via `files = [app_dir, "."]` with `mypy_path = ["test"]`, minimal `exclude`, no project source excluded.

- [ ] **Step 1: Replace the `[tool.mypy]` section and overrides**

In `pyproject.toml`, replace the entire `[tool.mypy]` section through the `[[tool.mypy.overrides]]` blocks (lines 5-41) with:

```toml
[tool.mypy]
warn_no_return = true
disallow_untyped_defs = true
disallow_untyped_calls = true
explicit_package_bases = true
mypy_path = [
    "test",
]
files = [
    "home/.homeassistant/appdaemon/apps",
    ".",
]
exclude = [
    "test/appdaemon_integration_test/.appdaemon/",
    "test/appdaemon_integration_test/.hass/",
    "test/appdaemon_integration_test/output/",
    "test/.venv/",
    "\\.mypy_cache/",
]

[[tool.mypy.overrides]]
module = "appdaemon_unit_test.test_helpers.hass"
disable_error_code = ["valid-type"]

[[tool.mypy.overrides]]
module = "appdaemon_unit_test.conftest"
disable_error_code = ["valid-type"]
```

Note: The `valid-type` overrides may need adjustment after running mypy. The old overrides were for `apps.hass` (now `appdaemon_unit_test.test_helpers.hass`) and `conftest.*` (now `appdaemon_unit_test.conftest`).

- [ ] **Step 2: Run mypy**

Run: `bin/mypy 2>&1 | tail -20`
Expected: no errors, or only `[valid-type]` errors that the overrides should catch. If other errors appear, fix them.

- [ ] **Step 3: If mypy has `[valid-type]` errors in the mock `hass.py`, adjust the override**

If errors persist in `appdaemon_unit_test.test_helpers.hass`, the override module name may need wildcards. Try `module = "appdaemon_unit_test.test_helpers.hass"` first; if the mock triggers errors in submodules, expand as needed.

- [ ] **Step 4: Fix any other mypy errors**

Common issues:
- `[import-not-found]` for `import hass` in test files → verify `app_dir` is in `files` (it is, as a `files` entry — mypy treats it as a package root).
- `[attr-defined]` for mock-only methods on `Hass`-typed vars → these should use `Any` typing; if not, fix the test file to use `Any`.
- Duplicate module errors → verify no `__init__.py` in `test/` (it's the mypy_path root, not a package).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "refactor: simplify mypy config for auto-discovery, no project files excluded"
```

---

### Task 10: Update AGENTS.md for new prod layout

**Files:**
- Modify: `AGENTS.md:17` (the `appdaemon/apps/` structure description)
- Modify: `AGENTS.md:48` (the modules path reference)

**Interfaces:**
- Produces: AGENTS.md reflects the new `apps/`, `configs/` subdirs.

- [ ] **Step 1: Update the appdaemon apps structure description**

In `AGENTS.md`, replace lines 17-18:
```
    - `appdaemon/apps/`: AppDaemon configuration.
      - `*.py`: The AppDaemon apps.
      - `*.yaml`: AppDaemon app configuration files. AppDaemon globs every `*.yaml`/`*.toml` in this directory and merges them, so the app definitions are split across multiple files by functionality.
```
with:
```
    - `appdaemon/apps/`: AppDaemon configuration.
      - `hass.py`: Base class for all apps, extending AppDaemon's `Hass`.
      - `apps/`: The AppDaemon app modules (`.py` files).
      - `configs/`: AppDaemon app configuration files (`.yaml`). AppDaemon globs every `*.yaml`/`*.toml` under `appdaemon/apps/` recursively and merges them, so the app definitions are split across multiple files by functionality.
```

- [ ] **Step 2: Update the modules path reference**

In `AGENTS.md`, replace line 48:
```
Modules under `home/.homeassistant/appdaemon/apps/` (configured via the `*.yaml` files in that directory, split by functionality):
```
with:
```
Modules under `home/.homeassistant/appdaemon/apps/apps/` (configured via the `*.yaml` files in `home/.homeassistant/appdaemon/apps/configs/`, split by functionality):
```

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for new appdaemon dir structure"
```

---

### Task 11: Final verification — unit tests, mypy, integration tests

**Files:**
- None (verification only)

- [ ] **Step 1: Run mypy**

Run: `bin/mypy 2>&1 | tail -5`
Expected: `Success: no issues found in N source files` with no project files excluded.

- [ ] **Step 2: Run unit tests**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v 2>&1 | tail -15`
Expected: all 288 tests pass, no errors.

- [ ] **Step 3: Run integration tests (5 min timeout)**

Run: `source test/.venv/bin/activate && cd test/appdaemon_integration_test && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" pytest -v 2>&1 | tail -30`
Expected: all integration tests pass. This validates the new layout works with real AppDaemon.

- [ ] **Step 4: If integration tests fail, debug**

Common issues:
- AppDaemon can't find modules → check the runtime `apps/` dir structure (`apps/hass.py`, `apps/apps/*.py`, `apps/test_apps/*.py`).
- `import hass` fails → verify `hass.py` symlink exists in runtime `apps/`.
- Config not loaded → verify `configs/` symlinks exist in runtime `apps/configs/`.

Inspect the runtime dir: `ls -la output/appdaemon/apps/` and `ls -la output/appdaemon/apps/apps/` and `ls -la output/appdaemon/apps/test_apps/`.

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "fix: integration test issues after restructure"
```

Only if there were fixes.