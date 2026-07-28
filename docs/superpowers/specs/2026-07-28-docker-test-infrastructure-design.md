# Docker-Based Test Infrastructure

## Problem

The current test setup has three separate venvs with problematic characteristics:

- **test** (`test/.venv`): pytest + test deps. Python 3.12.
- **hass** (`test/appdaemon_integration_test/.hass`): Home Assistant, installed
  via `pip install --no-deps`. Python 3.11. Uses an old HASS version because
  Home Assistant no longer supports pip installations, so the test version
  diverges from production.
- **appdaemon** (`test/appdaemon_integration_test/.appdaemon`): AppDaemon +
  mypy + basedpyright + type stubs. Python 3.12. Used both to run AppDaemon
  (integration tests) and for type checking (mypy/basedpyright find
  AppDaemon sources here).

Additionally, the `machine` executor in CircleCI can run Docker, and
Home Assistant publishes official container images. Running HASS and
AppDaemon in containers eliminates the venv installation problem for both.

## Design

### Architecture

```
CI (machine executor, Ubuntu VM)
├── checkout repo
├── restore cache (venv, keyed by uv.lock hash)
├── uv sync (single venv: test deps + appdaemon + typecheckers)
├── bin/mypy, bin/basedpyright (on VM, from single venv)
├── docker compose up -d hass appdaemon (with DLC-cached images)
├── pytest (on VM, from single venv)
│   ├── unit tests (no containers needed)
│   └── integration tests
│       ├── fixtures generate configs into output/hass, output/appdaemon
│       ├── fixtures start/stop containers via docker compose
│       └── tests connect to hass:localhost:18000, appdaemon:localhost:18001
├── save cache (venv)
└── store artifacts (on fail)
```

Local development uses the same flow: single venv + Docker for
hass/appdaemon. Requires Docker installed locally.

### Components

#### 1. Single merged venv

Merge `test/dependencies/test/` deps into `test/dependencies/appdaemon/pyproject.toml`:

- Add: `requests`, `pyyaml`, `python-dateutil`, `psutil`.
- Already present: `appdaemon`, `basedpyright`, `mypy`, `pytest`,
  `types-psutil`, `types-pyyaml`, `types-python-dateutil`, `types-requests`.
- Delete `test/dependencies/test/` directory.
- Delete `test/dependencies/homeassistant/` directory (HASS runs in
  container, no pip install needed).

The venv lives at `test/appdaemon_integration_test/.appdaemon` (keep
existing path so `bin/mypy`, `bin/basedpyright`, and `pyproject.toml`
type-checker config references remain stable).

`setup_virtualenv.sh` simplified to a single env:

```sh
./test/setup_virtualenv.sh  # creates the single venv
```

No more `test|hass|appdaemon|all` argument. The hass branch is deleted
(no local HASS venv). The test branch is deleted (merged). The appdaemon
branch becomes the default and only mode.

#### 2. docker-compose.yml

New file: `test/docker/compose.yml`

```yaml
services:
  hass:
    image: ghcr.io/home-assistant/home-assistant:stable
    ports:
      - "18000:8123"
    volumes:
      - ../appdaemon_integration_test/output/hass:/config

  appdaemon:
    image: kangirungungi/appdaemon:latest
    ports:
      - "18001:18001"
    volumes:
      - ../appdaemon_integration_test/output/appdaemon:/conf
    command: --config /conf
```

Notes:
- HASS container exposes 8123 internally, mapped to host 18000 (matches
  existing test port).
- AppDaemon container exposes 18001 directly (matches existing test port).
- Config dirs are volume-mounted from `output/` so fixtures can write
  configs before starting containers.
- Services are started individually by fixtures (not `up -d` globally)
  because configs must be generated first.

#### 3. Modified fixtures (start_stop.py)

The `home_assistant` and `appdaemon` session fixtures change from
spawning subprocesses to managing Docker containers:

**`home_assistant` fixture:**
1. Generate config into `output/hass/` (existing logic in
   `home_assistant.py`, unchanged).
2. Copy auth file to `output/hass/.storage/auth` (existing logic).
3. Run `docker compose -f test/docker/compose.yml up -d hass` from repo
   root.
4. Poll `http://127.0.0.1:18000/api/` for readiness (existing logic).
5. Teardown: `docker compose -f test/docker/compose.yml stop hass`.

**`appdaemon` fixture:**
1. Generate config into `output/appdaemon/` (existing logic in
   `app_daemon.py`, with symlink→copy change — see below).
2. Run `docker compose -f test/docker/compose.yml up -d appdaemon`.
3. Poll `http://127.0.0.1:18001/api/appdaemon/TestApp` (existing logic).
4. Teardown: `docker compose -f test/docker/compose.yml stop appdaemon`.

Both fixtures return the same dict shape (`{"host": ..., "port": ...}`)
so conftest.py and test code need no changes.

The `hass` and `appdaemon` wrapper scripts
(`test/appdaemon_integration_test/hass`,
`test/appdaemon_integration_test/appdaemon`) are deleted — replaced by
`docker compose` commands.

#### 4. Config generation changes (app_daemon.py)

`create_appdaemon_apps_config` currently uses `os.symlink` to point at
prod app `.py` files. Symlinks to host paths don't resolve inside
containers. Change all `os.symlink` calls to `shutil.copy` (or
`shutil.copy2` to preserve metadata).

Affected symlinks:
- Top-level `.py` modules from `prod_app_dir` (e.g. `hass.py`) → copy.
- `apps/` subdir `.py` modules → copy.
- `test_apps/` subdir `.py` modules → copy.

The `appdaemon.yaml` symlink in `create_appdaemon_configuration` also
becomes a copy.

#### 5. CI config (.circleci/config.yml)

Single job on `machine` executor with Docker Layer Caching:

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

On cache hit: `setup_virtualenv.sh` finds the venv already populated; uv
sync is instant (all deps satisfied). On cache miss: uv sync installs
from scratch, then cache is saved for next run.

`docker_layer_caching: true` caches Docker image pulls (HASS, AppDaemon)
on the Docker host across runs.

#### 6. Type checker config (pyproject.toml)

No changes needed to `bin/mypy` and `bin/basedpyright` — they already
point at `test/appdaemon_integration_test/.appdaemon/bin/`. The venv path
is unchanged.

The `pyproject.toml` basedpyright config `venvPath`/`venv` stays the same.

mypy `exclude` entries referencing `test/appdaemon_integration_test/.hass/`
can be removed (that venv no longer exists). The `test/.venv/` exclude
can also be removed (that venv no longer exists).

### Caching

Two caching layers:

**1. Python venv cache:**
- `restore_cache` with key `venv-{{ checksum "test/dependencies/appdaemon/uv.lock" }}`.
- Restores `test/appdaemon_integration_test/.appdaemon/` directory.
- On cache hit (lockfile unchanged): `uv sync` is instant — all deps
  satisfied.
- On cache miss: `uv sync` installs from scratch, then `save_cache`
  stores the populated venv.
- Keyed by `uv.lock` checksum so a dependency bump invalidates the cache
  automatically.

**2. Docker image cache:**
- `docker_layer_caching: true` on the machine executor.
- Docker pulls of `ghcr.io/home-assistant/home-assistant:stable` and
  `kangirungungi/appdaemon:latest` are cached on the Docker host.
- Base layers cache persistently; final layers re-pull when tags move
  (`stable`/`latest`).
- No manual version management needed.

### What's deleted

- `test/dependencies/test/` (merged into appdaemon)
- `test/dependencies/homeassistant/` (HASS runs in container)
- `test/docker/Dockerfile` (replaced by compose.yml — no custom image
  needed)
- `test/appdaemon_integration_test/hass` (wrapper script, replaced by
  docker compose)
- `test/appdaemon_integration_test/appdaemon` (wrapper script, replaced
  by docker compose)
- `setup_virtualenv.sh` hass/test/appdaemon branches (single env only)

### Trade-offs

**Pros:**
- HASS runs production container image — no more old pip-installed version
  diverging from production.
- Single venv for test deps, AppDaemon, and type checking.
- No more `--no-deps` HASS install hack.
- Consistent local + CI setup.
- CI caching for both venv and Docker images.

**Cons:**
- `machine` executor costs more credits than `docker` executor. Slower
  spin-up (instant to ~90s).
- Symlinks → copies in config generation. Slight test setup cost.
- Local dev now requires Docker installed.
- `stable`/`latest` tags are non-deterministic — a HASS or AppDaemon
  update could break tests without a code change. Acceptable trade-off
  for staying close to production; breakages surface quickly.