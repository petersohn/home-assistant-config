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
      - `*.py`: The AppDaemon apps.
      - `apps.yaml`: The AppDaemon configuration file.
  - `.local/bin/`: script used from inside Home Assistant.
- `robotframework-httplibrary/`: Third party testing library. Don't modify this.
- `test/`
  - `setup_virtualenv.sh`: A script to set up virtualenv for local testing (CI has ptython packages pre-built in the container).
  - `AppDaemonUnitTest/`: Unit tests for AppDaemon apps.
  - `AppDaemonIntegrationTest/`: Integration tests for AppDaemon apps.
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
  global_dependencies: <modules used by the app>
  ...arguments
```

Because the Python modules are loaded dynamically, only modules loaded before the app is reachable. For this reason, dependencies need to be specified.

### Testing

There are two levels of testing:

- **Unit tests**: These use a mocked version of AppDaemon. Fast and deterministic. These test the functionality of the apps, along with exact timing and edge cases.
- **Integration tests**: These use a real Home Assistant and AppDaemon. Slow and nondeterministic. These test that the apps work in realistic conditions. No exact timing is tested. Basic functionality is tested, plus behavior that rely on AppDaemon's inner logic, such as reloading apps when the configuration changes.

#### Setting up virtual environment

To set up virtual environments to run the tests, use this command:

```sh
./test/setup_virtualenv.sh robot|hass|appdaemon|all
```

This command removes each virtualenv if it exists, then reinstalls it using `uv`.

* `robot`: installs Robot Framework and other dependencies for the test runner into `./test/.venv` (Python 3.12). Tests need to be invoked from this virtualenv.
* `hass`: installs a Home Assistant into `./test/AppDaemonIntegrationTest/.hass` (Python 3.11, `--no-deps`). It's needed to run Integration tests.
* `appdaemon`: installs an AppDaemon into `./test/AppDaemonIntegrationTest/.appdaemon` (Python 3.12). It's needed to run Integration tests.

Call this script if any of the virtual environments are missing. DO NOT call it if the virtualenv exists unless explicitly asked for.

Requires `uv` to be installed: <https://docs.astral.sh/uv/getting-started/installation/>.

#### Upgrading dependencies

Each test environment is a uv project under `test/dependencies/<env>/` (robot, appdaemon) with a `pyproject.toml` (direct dependencies) and a `uv.lock` (pinned transitives). The `homeassistant` env uses a flat `requirements.txt` (effectively its own lockfile) because HASS is installed with `--no-deps` and its pinned versions are mutually inconsistent with what uv's resolver would produce.

To upgrade all dependencies for one environment to their latest compatible versions:

```sh
cd test/dependencies/<env>
uv lock --upgrade
```

To upgrade a single package:

```sh
cd test/dependencies/<env>
uv lock --upgrade-package <name>
```

To add or remove a dependency, edit `dependencies` in `pyproject.toml` and run `uv lock`. Then commit the updated `uv.lock` (and `pyproject.toml` if it changed). For `homeassistant`, edit `test/dependencies/homeassistant/requirements.txt` directly (since HASS uses `--no-deps`, there's no resolver to update).

#### Building the CI Docker image

The Dockerfile at `test/docker/Dockerfile` produces the image used by the integration test job in CI (referenced from `.circleci/config.yml`). The deps under `test/dependencies/` live outside the Dockerfile's build context, so the repo root is supplied as a named BuildKit context.

Build it from the repo root with:

```sh
docker build --build-context deps=. -f test/docker/Dockerfile test/docker/
```

Tag and push the result to update the image consumed by CircleCI.

#### Running the tests

To run the unit tests, first make sure that the `robot` virtualenv is installed. Then run:

```sh
source test/.venv/bin/activate && cd test/AppDaemonUnitTest && rm -rf output && ./run-test -LTRACE [-s <suite> | -t <test>]
```

To run the integration tests, first make sure that all virtualenvs are installed. Then run:

```sh
source test/.venv/bin/activate && cd test/AppDaemonIntegrationTestTest && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" ./run-test -LTRACE --removekeywords WUKS [-s <suite> | -t <test>]
```

Interpreting the output:

The test produces outputs in the `output` directory.

**Outputs common to all tests:**

- `report.html`: Short list of what tests were run and their results.
- `log.html`: Detailed, human readable list of each test step.
- `output.xml`: Detailed, machine readable list of each test step.

**Outputs specific to unit tests:**

- `logs/<suite>/<test>.log`: logs generated by one test.

**Outputs specific to integration tests:**

- `hass`: Home Assistant configuration and logs.
  - `homeassistant.log`, `homeassistant.stdout`, `homeassistant.stderr`: output generated by Home Assistant.
- `appdaemon`: AppDaemon configuration and logs.
  - `appdaemon.stdout`, `appdaemon.stderr`: stdout and stderr generated by AppDaemon. Normally, these should be empty if appdaemon can start up properly.
  - `error.log`: error level logs generated by AppDaemon. Logs here usually indicate some problems during test execution.
  - `appdaemon.log`: lower level logs generated by AppDaemon. It has important information about the test run.

## Verification

Run these checks before claiming work complete. They are mandatory, not optional.

### After every change

- Type check:

  ```sh
  bin/mypy
  ```

- Unit tests. Only the suites affected by the change are needed mid-task; run the full suite before handing off:

  ```sh
  source test/.venv/bin/activate && cd test/AppDaemonUnitTest && rm -rf output && ./run-test -LTRACE
  ```

Fix any failures and rerun before continuing. Do not leave the tree in a state where `bin/mypy` or the unit tests are red.

### At the end of a task or project

Run the integration tests once the full unit test suite is green and types are clean:

```sh
source test/.venv/bin/activate && cd test/AppDaemonIntegrationTest && rm -rf output && APPDAEMON_PATH="$PWD/.appdaemon" HASS_PATH="$PWD/.hass" ./run-test -LTRACE --removekeywords WUKS
```

Integration tests are slow and nondeterministic, so save them for the end. If a change is contained to one app, scope the run with `-s <suite>` or `-t <test>`; otherwise run the full suite.
