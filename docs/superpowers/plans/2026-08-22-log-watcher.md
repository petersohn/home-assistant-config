# Log Watcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an AppDaemon app (`LogWatcher`) that polls a log file at a configurable interval and sends notifications when new lines are written.

**Architecture:** Single `run_every` poll loop. Each tick: `os.stat` the file (skip if unchanged), handle rotation/shrink, reopen file, seek to last offset, read new lines, batch into one message, check enabler, send via `call_service`. In-memory offset, tail from end on startup.

**Tech Stack:** Python 3.12, AppDaemon, Home Assistant. Tests use the project's mock AppDaemon test harness (`test/appdaemon_unit_test/`).

**Spec:** `docs/superpowers/specs/2026-08-22-log-watcher-design.md`

---

## File Structure

- **Create:** `home/.homeassistant/appdaemon/apps/apps/log_watcher.py` — the `LogWatcher` app class.
- **Create:** `test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py` — unit tests.

No config YAML in this plan — config is added separately by the user.

---

## Task 1: Create `LogWatcher` app with `initialize` and `poll` skeleton

**Files:**
- Create: `home/.homeassistant/appdaemon/apps/apps/log_watcher.py`

- [ ] **Step 1: Write the app file**

```python
from __future__ import annotations

import datetime
import os
from typing import Any, TYPE_CHECKING, cast

import hass

if TYPE_CHECKING:
    import enabler
    import locker


class LogWatcher(hass.Hass):
    file: str = ""
    notifier: str = ""
    extra_args: dict[str, Any] = {}
    poll_interval: datetime.timedelta = cast(
        "datetime.timedelta", cast(Any, None)
    )
    mutex: locker.Mutex = cast("locker.Mutex", cast(Any, None))
    offset: int = 0
    timer: str | None = None
    enabler: "enabler.Enabler | None" = None

    def initialize(self) -> None:
        self.file = self.args["file"]
        self.notifier = self.args["notifier"]
        poll_interval = self.args["poll_interval"]
        if isinstance(poll_interval, dict):
            self.poll_interval = datetime.timedelta(**poll_interval)
        else:
            self.poll_interval = datetime.timedelta(seconds=poll_interval)
        self.extra_args = dict(self.args.get("args", {}))

        import locker
        locker_app = self.get_app("locker")
        assert isinstance(locker_app, locker.Locker)
        self.mutex = locker_app.get_mutex("LogWatcher")

        enabler_name = self.args.get("enabler")
        if enabler_name is not None:
            import enabler
            enabler_app = self.get_app(enabler_name)
            assert isinstance(enabler_app, enabler.Enabler)
            self.enabler = enabler_app

        try:
            self.offset = os.stat(self.file).st_size
        except FileNotFoundError:
            self.offset = 0

        self.timer = self.run_every(
            self.poll,
            self.datetime() + self.poll_interval,
            int(self.poll_interval.total_seconds()),
        )

    def poll(self, kwargs: dict[str, Any]) -> None:
        with self.mutex.lock("poll"):
            self._poll()

    def _poll(self) -> None:
        try:
            st = os.stat(self.file)
        except FileNotFoundError:
            self.offset = 0
            self.error(f"File not found: {self.file}")
            return

        if st.st_size == self.offset:
            return

        if st.st_size < self.offset:
            self.offset = 0

        with open(self.file, "r") as f:
            f.seek(self.offset)
            lines = f.readlines()
            self.offset = f.tell()

        if not lines:
            return

        self.log(f"{len(lines)} new line(s) from {self.file}")

        if self.enabler is None or self.enabler.is_enabled():
            message = "".join(lines)
            self.call_service(
                self.notifier, entity_id="", message=message, **self.extra_args
            )
```

- [ ] **Step 2: Run mypy to verify types**

Run: `bin/mypy`
Expected: No errors related to `log_watcher.py`.

- [ ] **Step 3: Run basedpyright to verify types**

Run: `bin/basedpyright`
Expected: No errors related to `log_watcher.py`.

- [ ] **Step 4: Commit**

```bash
git add home/.homeassistant/appdaemon/apps/apps/log_watcher.py
git commit -m "feat: add LogWatcher app for log file monitoring"
```

---

## Task 2: Write unit tests — basic notification on new lines

**Files:**
- Create: `test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from datetime import timedelta
from typing import Any

from appdaemon_unit_test.test_helpers.harness import Harness


NOTIFIER = "notify/notify"


def _create_log_watcher(
    harness: Harness,
    file: str,
    poll_interval: timedelta = timedelta(seconds=10),
    notifier: str = NOTIFIER,
    enabler: str | None = None,
    args: dict[str, Any] | None = None,
) -> Any:
    kwargs: dict[str, Any] = {
        "file": file,
        "poll_interval": int(poll_interval.total_seconds()),
        "notifier": notifier,
    }
    if enabler is not None:
        kwargs["enabler"] = enabler
    if args is not None:
        kwargs["args"] = args
    return harness.create_app(
        "log_watcher", "LogWatcher", "log_watcher", **kwargs
    )


def _register_notifier(harness: Harness, notifier: str = NOTIFIER) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def capture(data: dict[str, Any]) -> None:
        calls.append(data)

    harness.test_app._register_service(notifier, "", capture)
    return calls


def test_startup_seeks_to_end(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing line\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    assert calls == []


def test_new_lines_notification(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("new line 1\n")
        f.write("new line 2\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "new line 1\nnew line 2\n" in calls[0]["message"]


def test_no_new_lines_no_action(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))
    harness.advance_time(timedelta(seconds=10))

    assert calls == []


def test_multiple_lines_single_notification(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("line a\n")
        f.write("line b\n")
        f.write("line c\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "line a\nline b\nline c\n" in calls[0]["message"]


def test_extra_args_passed_through(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(
        harness, str(log_file), args={"title": "TestLog"}
    )

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("hello\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert calls[0]["title"] == "TestLog"
    assert "hello\n" in calls[0]["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v appdaemon_tests/test_log_watcher.py -x`
Expected: FAIL — `log_watcher` module not found (it will be importable from sys.path, but tests may fail on behavior if the app has bugs). If module not found, verify the `conftest.py` sys.path setup includes the apps directory.

- [ ] **Step 3: Run tests to verify they pass**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v appdaemon_tests/test_log_watcher.py -x`
Expected: PASS — all 5 tests pass.

- [ ] **Step 4: Commit**

```bash
git add test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py
git commit -m "test: add unit tests for LogWatcher basic notification"
```

---

## Task 3: Write unit tests — enabler and rotation

**Files:**
- Modify: `test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py`

- [ ] **Step 1: Append enabler and rotation tests**

Add these tests to the end of `test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py`:

```python
def test_enabler_disabled_suppresses_notification(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    enabler = harness.create_app(
        "enabler", "ScriptEnabler", "test_enabler", initial=True
    )
    _create_log_watcher(harness, str(log_file), enabler="test_enabler")

    harness.advance_time(timedelta(seconds=10))

    enabler.disable()

    with open(log_file, "a") as f:
        f.write("while disabled\n")

    harness.advance_time(timedelta(seconds=10))

    assert calls == []

    with open(log_file, "a") as f:
        f.write("after re-enable\n")

    enabler.enable()

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "after re-enable\n" in calls[0]["message"]
    assert "while disabled\n" not in calls[0]["message"]


def test_file_shrink_resets_offset(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing line 1\nexisting line 2\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    log_file.write_text("rotated fresh content\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "rotated fresh content\n" in calls[0]["message"]


def test_file_missing_then_recreated(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("first line\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("second line\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "second line\n" in calls[0]["message"]

    log_file.unlink()

    harness.advance_time(timedelta(seconds=10))

    log_file.write_text("fresh line a\nfresh line b\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    assert "fresh line a\nfresh line b\n" in calls[1]["message"]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v appdaemon_tests/test_log_watcher.py -x`
Expected: PASS — all 8 tests pass.

- [ ] **Step 3: Commit**

```bash
git add test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py
git commit -m "test: add LogWatcher enabler and file rotation tests"
```

---

## Task 4: Run full verification suite

**Files:** None modified.

- [ ] **Step 1: Run mypy**

Run: `bin/mypy`
Expected: No errors.

- [ ] **Step 2: Run basedpyright**

Run: `bin/basedpyright`
Expected: No errors.

- [ ] **Step 3: Run full unit test suite**

Run: `source test/.venv/bin/activate && cd test/appdaemon_unit_test && rm -rf output && pytest -v`
Expected: All tests pass, including the 8 new `test_log_watcher.py` tests.

- [ ] **Step 4: Commit if any fixups were needed**

If any fixes were made to pass verification:

```bash
git add -A
git commit -m "fix: address type-check and test failures in LogWatcher"
```

If no fixes needed, skip this step.