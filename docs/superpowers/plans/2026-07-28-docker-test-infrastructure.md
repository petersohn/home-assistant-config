# Docker-Based Test Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three separate venvs (test, hass, appdaemon) with a single venv plus Docker containers for Home Assistant and AppDaemon, running integration tests on CircleCI's machine executor.

**Architecture:** Single Python venv on the VM host contains test deps, AppDaemon, and type checkers. Home Assistant and AppDaemon run as Docker containers managed via `docker compose`. pytest fixtures generate configs into a shared `output/` directory, volume-mounted into containers, then start/stop containers on demand. CI uses `machine` executor with Docker layer caching and venv caching.

**Tech Stack:** Python 3.12, uv, pytest, Docker Compose, CircleCI machine executor, Home Assistant (container), AppDaemon (container), mypy, basedpyright.

---

### Task 1: Merge test deps into appdaemon pyproject.toml

**Files:**
- Modify: `test/dependencies/appdaemon/pyproject.toml`
- Delete: `test/dependencies/test/`

- [ ] **Step 1: Add test deps to appdaemon pyproject.toml**

Modify `test/dependencies/appdaemon/pyproject.toml`:

```toml
[project]
name = "appdaemon-test-env"
version = "0.1.0"
description = "AppDaemon integration test environment"
requires-python = ">=3.12,<3.14"
dependencies = [
    "appdaemon @ git+https://github.com/petersohn/appdaemon@fix-unload-bug",
    "basedpyright",
    "mypy",
    "pytest",
    "requests",
    "pyyaml",
    "python-dateutil",
    "psutil",
    "types-psutil",
    "types-pyyaml",
    "types-python-dateutil",
    "types-requests",
]
```

- [ ] **Step 2: Regenerate uv.lock**

Run:
```sh
cd test/dependencies/appdaemon && uv lock
```

Expected: `uv.lock` updated with new deps.

- [ ] **Step 3: Delete test dependencies directory**

Run:
```sh
rm -rf test/dependencies/test/
```

- [ ] **Step 4: Verify venv syncs with merged deps**

Run:
```sh
rm -rf test/appdaemon_integration_test/.appdaemon
./test/setup_virtualenv.sh appdaemon
source test/appdaemon_integration_test/.appdaemon/bin/activate
python -c "import requests, yaml, dateutil, psutil, appdaemon, mypy, pyright; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 5: Commit**

```sh
git add test/dependencies/appdaemon/pyproject.toml test/dependencies/appdaemon/uv.lock
git rm -r test/dependencies/test/
git commit -m "deps: merge test deps into appdaemon pyproject.toml"
```

### Task 2: Simplify setup_virtualenv.sh

**Files:**
- Modify: `test/setup_virtualenv.sh`

- [ ] **Step 1: Rewrite setup_virtualenv.sh to single-env mode**

Replace entire contents of `test/setup_virtualenv.sh`:

```bash
#!/bin/bash

set -e
script_dir=$(readlink -e "$(dirname "$0")")
cd "$script_dir"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

venv_path="appdaemon_integration_test/.appdaemon"
rm -rf "$venv_path"
uv venv --python python3.12 "$venv_path"
(
    cd dependencies/appdaemon
    VIRTUAL_ENV="$script_dir/$venv_path" uv sync --frozen --no-install-project --active
)
```

- [ ] **Step 2: Verify it works**

Run:
```sh
rm -rf test/appdaemon_integration_test/.appdaemon
./test/setup_virtualenv.sh
source test/appdaemon_integration_test/.appdaemon/bin/activate
python -c "import requests, yaml, appdaemon; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```sh
git add test/setup_virtualenv.sh
git commit -m "test: simplify setup_virtualenv.sh to single venv"
```

### Task 3: Create docker-compose.yml

**Files:**
- Create: `test/docker/compose.yml`

- [ ] **Step 1: Create compose.yml**

Create `test/docker/compose.yml`:

```yaml
services:
  hass:
    image: ghcr.io/home-assistant/home-assistant:stable
    ports:
      - "18000:8123"
    volumes:
      - ../appdaemon_integration_test/output/hass:/config

  appdaemon:
    image: kangirigungi/appdaemon:latest
    ports:
      - "18001:18001"
    volumes:
      - ../appdaemon_integration_test/output/appdaemon:/conf
```

Notes:
- HASS listens on 8123 internally, mapped to host 18000.
- AppDaemon listens on 18001 (set via `http.url` in appdaemon.yaml, which binds to `0.0.0.0`).
- The appdaemon image entrypoint (`/start.sh`) runs `appdaemon -c /conf "$@"`, so no `command:` override needed.
- Config dirs volume-mounted from `output/` so fixtures write configs before starting.

- [ ] **Step 2: Commit**

```sh
git add test/docker/compose.yml
git commit -m "test: add docker-compose.yml for hass+appdaemon"
```

### Task 4: Fix appdaemon config for container networking

**Files:**
- Modify: `test/appdaemon_integration_test/config/appdaemon/appdaemon.yaml`
- Modify: `test/appdaemon_integration_test/helpers/app_daemon.py`
- Modify: `test/appdaemon_integration_test/helpers/home_assistant.py`

The `http.url` in appdaemon.yaml must bind `0.0.0.0` (not `127.0.0.1`) so the port is accessible from the host via Docker port mapping. The HASS URL must use the compose service name `hass:8123` (internal port) instead of `127.0.0.1:18000`, because inside the appdaemon container `127.0.0.1` refers to the container's own loopback.

- [ ] **Step 1: Change http.url to bind 0.0.0.0 in appdaemon.yaml**

Modify `test/appdaemon_integration_test/config/appdaemon/appdaemon.yaml` line 13:

```yaml
    url: http://0.0.0.0:18001
```

- [ ] **Step 2: Change HASS URL to use compose service name**

The `create_appdaemon_configuration` function in `app_daemon.py` generates `secrets.yaml` with `"url": "http://" + hass_host`. The `hass_host` is passed from the `home_assistant` fixture as `127.0.0.1:18000`. Inside the appdaemon container, this won't reach the hass container.

The fix: the `home_assistant` fixture should pass the compose-internal hostname (`hass:8123`) to `create_appdaemon_configuration`, while tests connect to hass via `127.0.0.1:18000` (host-mapped port).

Modify `test/appdaemon_integration_test/helpers/app_daemon.py`, `create_appdaemon_configuration` — no change needed to the function itself; it already takes `hass_host` as a parameter. The caller will pass the correct value.

- [ ] **Step 3: Verify config files are correct**

Run:
```sh
cat test/appdaemon_integration_test/config/appdaemon/appdaemon.yaml
```

Expected: `http.url: http://0.0.0.0:18001` on line 13.

- [ ] **Step 4: Commit**

```sh
git add test/appdaemon_integration_test/config/appdaemon/appdaemon.yaml
git commit -m "test: bind appdaemon http to 0.0.0.0 for container access"
```

### Task 5: Change symlinks to copies in config generation

**Files:**
- Modify: `test/appdaemon_integration_test/helpers/app_daemon.py`

Symlinks to host paths don't resolve inside containers. Change all `os.symlink` to `shutil.copy2`.

- [ ] **Step 1: Add shutil import and replace symlinks with copies**

Modify `test/appdaemon_integration_test/helpers/app_daemon.py`:

Add `import shutil` at the top (after existing imports).

In `create_appdaemon_configuration` (line 20), replace:
```python
    os.symlink(source_appdaemon_yaml, appdaemon_yaml)
```
with:
```python
    shutil.copy2(source_appdaemon_yaml, appdaemon_yaml)
```

In `create_appdaemon_apps_config`, replace all three `os.symlink` blocks:

Top-level modules (lines ~57-61):
```python
        shutil.copy2(
            os.path.join(directories.prod_app_dir, file_name), target_file
        )
```

apps/ subdir (lines ~71-73):
```python
        shutil.copy2(os.path.join(prod_apps_subdir, file_name), target_file)
```

test_apps/ subdir (lines ~84-86):
```python
        shutil.copy2(
            os.path.join(directories.test_apps_path, file_name), target_file
        )
```

Keep the existing `if os.path.exists(target_file): os.remove(target_file)` guards before each copy — they're harmless and defensive. Only change `os.symlink` to `shutil.copy2` in each block.

- [ ] **Step 2: Verify unit tests still pass**

Run:
```sh
source test/appdaemon_integration_test/.appdaemon/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v
```

Expected: all unit tests pass.

- [ ] **Step 3: Commit**

```sh
git add test/appdaemon_integration_test/helpers/app_daemon.py
git commit -m "test: use copy instead of symlink for container compatibility"
```

### Task 6: Rewrite start_stop.py fixtures for Docker

**Files:**
- Modify: `test/appdaemon_integration_test/helpers/start_stop.py`
- Delete: `test/appdaemon_integration_test/hass`
- Delete: `test/appdaemon_integration_test/appdaemon`

- [ ] **Step 1: Rewrite start_stop.py**

Replace entire contents of `test/appdaemon_integration_test/helpers/start_stop.py`:

```python
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

import pytest

COMPOSE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "docker", "compose.yml"
)
COMPOSE_FILE = os.path.normpath(COMPOSE_FILE)

HASS_PORT = 18000
APPDAEMON_PORT = 18001


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-f", COMPOSE_FILE, *args]


@pytest.fixture(scope="session")
def home_assistant(clear_output_dir: Any, base_output_directory: str) -> Any:
    hass_path = os.path.join(base_output_directory, "hass")
    shutil.rmtree(hass_path, ignore_errors=True)
    create_home_assistant_configuration(hass_path, HASS_PORT)
    # Copy auth file
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "hass")
    os.makedirs(os.path.join(hass_path, ".storage"), exist_ok=True)
    shutil.copy(
        os.path.join(config_dir, "auth"),
        os.path.join(hass_path, ".storage", "auth"),
    )
    subprocess.run(_compose("up", "-d", "hass"), check=True)
    # Wait for HASS to start
    import requests
    from appdaemon_integration_test.helpers.hass_client import HASS_TOKEN
    headers = {"Authorization": f"Bearer {HASS_TOKEN}"}
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{HASS_PORT}/api/", headers=headers)
            if r.status_code == 200 and r.json().get("message") == "API running.":
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        raise RuntimeError("Home Assistant failed to start")
    yield {"host": f"127.0.0.1:{HASS_PORT}", "port": HASS_PORT}
    subprocess.run(_compose("stop", "hass"), check=True)


@pytest.fixture(scope="session")
def appdaemon(home_assistant: Any, base_output_directory: str) -> Any:
    appdaemon_dir = os.path.join(base_output_directory, "appdaemon")
    os.makedirs(appdaemon_dir, exist_ok=True)
    create_appdaemon_configuration(appdaemon_dir, "hass:8123", APPDAEMON_PORT)
    create_appdaemon_apps_config(appdaemon_dir, "TestApp")
    subprocess.run(_compose("up", "-d", "appdaemon"), check=True)
    # Wait for AppDaemon to start
    import requests
    test_arg = "This is a test"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.post(
                f"http://127.0.0.1:{APPDAEMON_PORT}/api/appdaemon/TestApp",
                json={"function": "test", "result_type": None, "arg_types": [], "kwarg_types": {}, "args": [test_arg], "kwargs": {}},
            )
            if r.status_code == 200 and r.json() == test_arg:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError("AppDaemon failed to start")
    yield {"host": f"127.0.0.1:{APPDAEMON_PORT}", "dir": appdaemon_dir}
    subprocess.run(_compose("stop", "appdaemon"), check=True)
    assert os.path.getsize(f"{appdaemon_dir}/appdaemon.stderr") == 0
```

Key changes from the original:
- `_compose()` helper builds `docker compose -f <compose.yml> ...` commands.
- `home_assistant` fixture: generates config, runs `docker compose up -d hass`, polls same endpoint, teardown `docker compose stop hass`.
- `appdaemon` fixture: generates config (passing `hass:8123` as HASS host for compose networking), runs `docker compose up -d appdaemon`, polls same endpoint, teardown `docker compose stop appdaemon`.
- Removed `_check_leftover_process` — Docker container management replaces process checking.
- Removed `process` key from yielded dict (no subprocess). `host` and `port` remain.
- The `appdaemon.stderr` assertion: the appdaemon container's stderr is captured in `appdaemon.stderr` via the entrypoint. Note: the container's stdout/stderr go to Docker logs, not to a file. The `appdaemon.stderr` file was written by the old `subprocess.Popen` redirect. In the container setup, logs go to appdaemon.log/error.log via appdaemon config. The stderr assertion may need adjustment — see Task 7.

- [ ] **Step 2: Delete wrapper scripts**

Run:
```sh
git rm test/appdaemon_integration_test/hass test/appdaemon_integration_test/appdaemon
```

- [ ] **Step 3: Commit**

```sh
git add test/appdaemon_integration_test/helpers/start_stop.py
git commit -m "test: rewrite fixtures to use docker compose for hass+appdaemon"
```

### Task 7: Handle appdaemon stderr assertion

**Files:**
- Modify: `test/appdaemon_integration_test/helpers/start_stop.py`

The old fixture asserted `os.path.getsize(f"{appdaemon_dir}/appdaemon.stderr") == 0` because stderr was redirected to a file by `subprocess.Popen`. With Docker, stdout/stderr go to Docker container logs, not to a file. AppDaemon's own logging writes to `appdaemon.log` and `error.log` (configured in appdaemon.yaml). The `error.log` is already checked by `ErrorLogChecker` fixture.

- [ ] **Step 1: Remove the stderr assertion**

In `test/appdaemon_integration_test/helpers/start_stop.py`, remove this line from the `appdaemon` fixture teardown:

```python
    assert os.path.getsize(f"{appdaemon_dir}/appdaemon.stderr") == 0
```

The `ErrorLogChecker` fixture (in conftest.py) already checks `error.log` for unexpected errors per-test, which is the real validation.

- [ ] **Step 2: Commit**

```sh
git add test/appdaemon_integration_test/helpers/start_stop.py
git commit -m "test: remove appdaemon stderr assertion (container logs go to docker)"
```

### Task 8: Set HASS server_port to 8123 for container

**Files:**
- Modify: `test/appdaemon_integration_test/helpers/start_stop.py`

The HASS container listens on 8123 internally. The compose port mapping `18000:8123` maps host 18000 to container 8123. The generated `configuration.yaml` sets `http.server_port`. Currently it's set to `18000` (the old host port). Inside the container, HASS must listen on 8123 to match the port mapping.

The `create_home_assistant_configuration` function takes a `port` parameter and sets `http.server_port` to it. The fixture currently passes `HASS_PORT` (18000). It should pass `8123` (the container internal port). The `HASS_PORT` constant (18000) is still used for host-facing connections.

- [ ] **Step 1: Update the fixture call in start_stop.py**

In `test/appdaemon_integration_test/helpers/start_stop.py`, in the `home_assistant` fixture, change:

```python
    create_home_assistant_configuration(hass_path, HASS_PORT)
```
to:
```python
    create_home_assistant_configuration(hass_path, 8123)
```

No change to `home_assistant.py` itself — it already uses the `port` parameter for `server_port`.

- [ ] **Step 2: Commit**

```sh
git add test/appdaemon_integration_test/helpers/start_stop.py
git commit -m "test: set HASS server_port to 8123 for container"
```

### Task 9: Update pyproject.toml type checker exclusions

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove deleted venv paths from mypy and basedpyright excludes**

In `pyproject.toml`, in the `[tool.mypy]` section, remove these lines from `exclude`:

```
    "test/appdaemon_integration_test/.hass/",
    "test/.venv/",
```

In the `[tool.basedpyright]` section, remove:
```
    "test/appdaemon_integration_test/.hass/",
    "test/dependencies/",
    "test/.venv/",
```

Keep `test/appdaemon_integration_test/.appdaemon/` (the venv still exists there) and other excludes.

- [ ] **Step 2: Verify type checkers pass**

Run:
```sh
bin/mypy
bin/basedpyright
```

Expected: both pass (no new errors).

- [ ] **Step 3: Commit**

```sh
git add pyproject.toml
git commit -m "config: remove deleted venv paths from type checker excludes"
```

### Task 10: Delete test/docker/Dockerfile and homeassistant deps

**Files:**
- Delete: `test/docker/Dockerfile`
- Delete: `test/dependencies/homeassistant/`

- [ ] **Step 1: Delete Dockerfile and homeassistant deps**

Run:
```sh
git rm test/docker/Dockerfile
git rm -r test/dependencies/homeassistant/
```

- [ ] **Step 2: Commit**

```sh
git commit -m "test: remove custom Dockerfile and homeassistant deps (using containers now)"
```

### Task 11: Rewrite CircleCI config

**Files:**
- Modify: `.circleci/config.yml`

- [ ] **Step 1: Replace config.yml with machine executor setup**

Replace entire contents of `.circleci/config.yml`:

```yaml
version: 2.1
commands:
  pytest:
    parameters:
      directory:
        type: string
      logs_only:
        type: boolean
        default: false
    steps:
      - run:
          name: run tests
          command: |
            source test/appdaemon_integration_test/.appdaemon/bin/activate
            pytest <<parameters.directory>> -v --tb=short
      - when:
          condition: <<parameters.logs_only>>
          steps:
            - run:
                name: collect log files
                command: |
                  mkdir -p <<parameters.directory>>/output_logs
                  find <<parameters.directory>>/output -type f \
                    \( -name '*.log*' -o -name '*.stdout' \
                    -o -name '*.stderr' \) \
                    -exec cp --parents {} <<parameters.directory>>/output_logs \;
                when: on_fail
            - store_artifacts:
                path: <<parameters.directory>>/output_logs
                when: on_fail
      - unless:
          condition: <<parameters.logs_only>>
          steps:
            - store_artifacts:
                path: <<parameters.directory>>/output
                when: on_fail

jobs:
  test:
    machine:
      image: ubuntu-2404:current
    docker_layer_caching: true
    steps:
      - checkout
      - restore_cache:
          keys:
            - venv-{{ checksum "test/dependencies/appdaemon/uv.lock" }}
      - run:
          name: setup venv
          command: |
            curl -LsSf https://astral.sh/uv/install.sh | sh
            source ~/.bashrc
            ./test/setup_virtualenv.sh
      - save_cache:
          paths:
            - test/appdaemon_integration_test/.appdaemon
          key: venv-{{ checksum "test/dependencies/appdaemon/uv.lock" }}
          when: on_success
      - run:
          name: mypy
          command: bin/mypy
      - run:
          name: basedpyright
          command: bin/basedpyright
      - pytest:
          directory: test/appdaemon_unit_test
      - pytest:
          directory: test/appdaemon_integration_test
          logs_only: true

workflows:
  version: 2
  test:
    jobs:
      - test
```

- [ ] **Step 2: Commit**

```sh
git add .circleci/config.yml
git commit -m "ci: switch to machine executor with docker, venv caching, type checks"
```

### Task 12: Verify full local test run

**Files:** (none — verification only)

- [ ] **Step 1: Set up single venv**

Run:
```sh
rm -rf test/appdaemon_integration_test/.appdaemon test/.venv test/appdaemon_integration_test/.hass
./test/setup_virtualenv.sh
```

- [ ] **Step 2: Run type checks**

Run:
```sh
bin/mypy
bin/basedpyright
```

Expected: both pass.

- [ ] **Step 3: Run unit tests**

Run:
```sh
source test/appdaemon_integration_test/.appdaemon/bin/activate
cd test/appdaemon_unit_test && rm -rf output && pytest -v
```

Expected: all unit tests pass.

- [ ] **Step 4: Run integration tests**

Run:
```sh
source test/appdaemon_integration_test/.appdaemon/bin/activate
cd test/appdaemon_integration_test && rm -rf output && pytest -v
```

Expected: all integration tests pass (containers start, tests connect, teardown clean).

- [ ] **Step 5: Verify no leftover containers**

Run:
```sh
docker compose -f test/docker/compose.yml ps
```

Expected: no running containers (all stopped by fixtures).

- [ ] **Step 6: Clean up containers**

Run:
```sh
docker compose -f test/docker/compose.yml down
```

### Task 13: Update AGENTS.md documentation

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update testing section in AGENTS.md**

Update the "Setting up virtual environment" section to reflect single venv:

```markdown
#### Setting up virtual environment

To set up the virtual environment to run the tests, use this command:

```sh
./test/setup_virtualenv.sh
```

This command removes the venv if it exists, then reinstalls it using `uv`.

The venv is installed at `test/appdaemon_integration_test/.appdaemon` (Python 3.12). It contains test deps, AppDaemon, mypy, and basedpyright.

Requires `uv` to be installed: <https://docs.astral.sh/uv/getting-started/installation/>.

Requires Docker to be installed for integration tests: <https://docs.docker.com/get-docker/>.
```

Update "Running the tests" section — integration tests now use Docker:

```markdown
To run the integration tests, first make sure that the venv is installed and Docker is running. Then run:

```sh
# Integration tests
source test/appdaemon_integration_test/.appdaemon/bin/activate
pytest test/appdaemon_integration_test/ [-k <test>]
```

Integration tests start Home Assistant and AppDaemon as Docker containers via `docker compose`. The full integration test suite takes longer time to finish. Give it 5 minutes timeout.
```

Update "Upgrading dependencies" section — remove homeassistant env reference:

```markdown
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
```

Update "Building the CI Docker image" section — remove it entirely (no custom Docker image):

Delete the entire "#### Building the CI Docker image" subsection and the Dockerfile reference.

- [ ] **Step 2: Commit**

```sh
git add AGENTS.md
git commit -m "docs: update AGENTS.md for single venv + docker setup"
```