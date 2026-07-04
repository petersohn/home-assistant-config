# AppDaemon 3.x → 4.5.13 Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate integration test environment from AppDaemon 3.0.5 (Python 3.8) to AppDaemon 4.5.13 (Python 3.12), passing all integration tests.

**Architecture:** Rewrite `appdaemon.yaml` for AD 4.x format (logs section, http component, api section, mandatory appdaemon fields), bump Python to 3.12, regenerate pinned requirements. App code already uses `appdaemon.plugins.hass.hassapi.Hass` which is correct for 4.x — no app code changes needed.

**Tech Stack:** AppDaemon 4.5.13, Python 3.12, Home Assistant 2023.5.4 (unchanged), Robot Framework (unchanged).

---

## Context

Current state:
- `test/docker/python_requirements/appdaemon.txt` pins `appdaemon==3.0.5` and many legacy deps.
- `test/setup_virtualenv.sh` creates venv with `python3.8`.
- `test/docker/Dockerfile` multi-stage builds Python 3.8 then copies into 3.11 image.
- `test/AppDaemonIntegrationTest/config/appdaemon/appdaemon.yaml` uses 3.x schema (`log`, `api_port` under `appdaemon`).
- `test/AppDaemonIntegrationTest/output/appdaemon/secrets.yaml` defines `api_port`, `logfile`, `errorfile`, `url`.
- App code in `home/.homeassistant/appdaemon/apps/` already imports from `appdaemon.plugins.hass.hassapi` — no changes needed.
- App code in `test/AppDaemonIntegrationTest/config/appdaemon/apps/test_app.py` and `dummy.py` use `import hass` (custom module) — works in 4.x.
- Available Python: 3.8, 3.11, 3.12, 3.14. AppDaemon 4.5.13 requires 3.10-3.13. Use 3.12.

Key 4.x config changes (from upgrade guide):
- `log` section → `logs` section.
- `api_port` moves from `appdaemon` to `http` component (defined by `url`).
- `latitude`, `longitude`, `elevation`, `timezone` mandatory in `appdaemon` section.
- Add `api` section to enable App API at `/api/appdaemon/<endpoint>`.

---

### Task 1: Rewrite `appdaemon.yaml` to 4.x schema

**Files:**
- Modify: `test/AppDaemonIntegrationTest/config/appdaemon/appdaemon.yaml:1-12`

- [ ] **Step 1: Replace entire file content**

Replace `test/AppDaemonIntegrationTest/config/appdaemon/appdaemon.yaml` with:

```yaml
appdaemon:
    latitude: 47.0
    longitude: 19.0
    elevation: 100
    timezone: Europe/Budapest
    plugins:
        HASS:
            type: hass
            ha_url: !secret url
            token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkY2U3MDgwNDIwYmI0Mjg3OWIyYjQ1MjQ4OTQzNjI4YiIsImlhdCI6MTU0NjI1MDYyNiwiZXhwIjoxODYxNjEwNjI2fQ.1YmZVaw3EH2bu0jExU2Q6mIyrD1Qf0cPPJmt877mNC0

http:
    url: http://127.0.0.1:18001

logs:
    default_log:
        filename: !secret logfile
    error_log:
        filename: !secret errorfile

api:
```

- [ ] **Step 2: Verify file**

Run: `cat test/AppDaemonIntegrationTest/config/appdaemon/appdaemon.yaml`
Expected: New schema visible. No `log:` key, has `http:`, `logs:`, `api:`.

---

### Task 2: Update secrets file with HTTP URL

**Files:**
- Modify: `test/AppDaemonIntegrationTest/output/appdaemon/secrets.yaml:1-4`

- [ ] **Step 1: Replace entire file content**

Replace `test/AppDaemonIntegrationTest/output/appdaemon/secrets.yaml` with:

```yaml
errorfile: /home/petersohn/workspace/home-assistant-config/test/AppDaemonIntegrationTest/output/appdaemon/error.log
logfile: /home/petersohn/workspace/home-assistant-config/test/AppDaemonIntegrationTest/output/appdaemon/appdaemon.log
url: http://127.0.0.1:18000
```

(`api_port` removed — its value (18001) now lives in `appdaemon.yaml` under `http.url`.)

- [ ] **Step 2: Verify file**

Run: `cat test/AppDaemonIntegrationTest/output/appdaemon/secrets.yaml`
Expected: 3 lines, no `api_port:`.

---

### Task 3: Update `setup_virtualenv.sh` to use Python 3.12

**Files:**
- Modify: `test/setup_virtualenv.sh:35`

- [ ] **Step 1: Change `python3.8` to `python3.12` in appdaemon block**

Edit `test/setup_virtualenv.sh` line 35 from:
```bash
    setup python3.8 AppDaemonIntegrationTest/.appdaemon appdaemon.txt
```
to:
```bash
    setup python3.12 AppDaemonIntegrationTest/.appdaemon appdaemon.txt
```

(Leave `hass` line alone — that one already uses `python3.11`.)

- [ ] **Step 2: Verify file**

Run: `grep -n "python3" test/setup_virtualenv.sh`
Expected: Only `python3.12 AppDaemonIntegrationTest/.appdaemon` (hass line still `python3.11`).

---

### Task 4: Regenerate `appdaemon.txt` with new pinned requirements

**Files:**
- Modify: `test/docker/python_requirements/appdaemon.txt:1-32`

- [ ] **Step 1: Run setup_virtualenv.sh to install fresh appdaemon venv**

Run:
```bash
./test/setup_virtualenv.sh appdaemon
```
Expected: venv created at `test/AppDaemonIntegrationTest/.appdaemon/`, appdaemon installed without errors. May take 1-2 minutes.

- [ ] **Step 2: Verify appdaemon installed**

Run:
```bash
test/AppDaemonIntegrationTest/.appdaemon/bin/pip show appdaemon | head -3
```
Expected: `Version: 4.5.13` (or close — exact version depends on when setup runs).

- [ ] **Step 3: Freeze new requirements**

Run:
```bash
test/AppDaemonIntegrationTest/.appdaemon/bin/pip freeze > test/docker/python_requirements/appdaemon.txt
```

- [ ] **Step 4: Verify file contains appdaemon 4.x**

Run: `head -5 test/docker/python_requirements/appdaemon.txt`
Expected: First line should be `appdaemon==4.5.13` (or similar 4.x). No `aiohttp==2.x`, no `daemonize`.

- [ ] **Step 5: Trim to just direct deps + critical transitive**

Replace `test/docker/python_requirements/appdaemon.txt` with the freeze output. Keep it as-is — pip freeze is the source of truth for reproducible installs.

---

### Task 5: Update Dockerfile to use Python 3.12 only

**Files:**
- Modify: `test/docker/Dockerfile:1-25`

- [ ] **Step 1: Replace entire file content**

Replace `test/docker/Dockerfile` with:

```dockerfile
FROM python:3.12

COPY python_requirements/robot.txt /python_requirements/robot.txt
RUN pip3 install -r /python_requirements/robot.txt
COPY python_requirements/homeassistant.txt /python_requirements/homeassistant.txt
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install -r /python_requirements/homeassistant.txt

COPY python_requirements/appdaemon.txt /python_requirements/appdaemon.txt
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install -r /python_requirements/appdaemon.txt

RUN rm -rf /python_requirements
```

- [ ] **Step 2: Verify file**

Run: `cat test/docker/Dockerfile`
Expected: Single-stage Python 3.12 build, no multi-stage.

---

### Task 6: Run integration tests with new venv

**Files:** none modified

- [ ] **Step 1: Run a fast single test to verify AD starts**

Run:
```bash
cd /home/petersohn/workspace/home-assistant-config
rm -rf test/AppDaemonIntegrationTest/output
APPDAEMON_PATH="$PWD/test/AppDaemonIntegrationTest/.appdaemon" HASS_PATH="$PWD/test/AppDaemonIntegrationTest/.hass" \
  test/.venv/bin/python -m robot --outputdir=test/AppDaemonIntegrationTest/output --variable "base_output_directory:test/AppDaemonIntegrationTest/output" \
  -t "Simple State Changes" test/AppDaemonIntegrationTest/AppDaemonSuite/CoverTest.robot
```
Expected: Single test passes. If appdaemon fails to start, check `test/AppDaemonIntegrationTest/output/appdaemon/appdaemon.log` and `error.log` for the actual error.

- [ ] **Step 2: If first test fails, debug**

Check `test/AppDaemonIntegrationTest/output/appdaemon/appdaemon.log` for the actual error. Common issues:
- App API not enabled → confirm `api:` block in `appdaemon.yaml`.
- `register_endpoint` path changed → check 4.x changelog.
- HASS plugin token / URL → confirm `secrets.yaml` resolved.

- [ ] **Step 3: Run full integration test suite**

Run:
```bash
cd /home/petersohn/workspace/home-assistant-config
rm -rf test/AppDaemonIntegrationTest/output
APPDAEMON_PATH="$PWD/test/AppDaemonIntegrationTest/.appdaemon" HASS_PATH="$PWD/test/AppDaemonIntegrationTest/.hass" \
  test/.venv/bin/python -m robot --outputdir=test/AppDaemonIntegrationTest/output --variable "base_output_directory:test/AppDaemonIntegrationTest/output" \
  --removekeywords WUKS test/AppDaemonIntegrationTest/AppDaemonSuite/
```
Expected: All tests pass. Check `test/AppDaemonIntegrationTest/output/report.html` for summary.

- [ ] **Step 4: Commit**

```bash
cd /home/petersohn/workspace/home-assistant-config
git add test/AppDaemonIntegrationTest/config/appdaemon/appdaemon.yaml \
        test/AppDaemonIntegrationTest/output/appdaemon/secrets.yaml \
        test/setup_virtualenv.sh \
        test/docker/Dockerfile \
        test/docker/python_requirements/appdaemon.txt
git commit -m "Migrate AppDaemon from 3.0.5 to 4.5.13"
```

---

## Self-Review

1. **Spec coverage:**
   - Rewrite integration test appdaemon config → Task 1.
   - New virtualenv for appdaemon with newest version → Task 4.
   - Use latest Python version → Task 3, Task 5 (3.12).
   - Run integration tests with new APPDAEMON_PATH → Task 6.
   - Update requirements file → Task 4.
   - Update Dockerfile → Task 5.

2. **Placeholder scan:** No "TBD", "TODO", "implement later" in steps. All commands exact. All file contents fully specified.

3. **Type consistency:** `api_port` removed everywhere it appeared (`appdaemon.yaml`, `secrets.yaml`). New `http.url` value matches old `api_port: 18001`. No other renames.

