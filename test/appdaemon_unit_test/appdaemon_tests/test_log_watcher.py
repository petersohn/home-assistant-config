from __future__ import annotations

from datetime import timedelta
from typing import Any

from appdaemon_unit_test.test_helpers.harness import Harness


NOTIFIER = "notify/notify"


def _create_log_watcher(
    harness: Harness,
    file: str,
    poll_interval: timedelta | None = None,
    notifier: str = NOTIFIER,
    enabler: str | None = None,
    args: dict[str, Any] | None = None,
) -> Any:
    interval = poll_interval if poll_interval is not None else timedelta(seconds=10)
    kwargs: dict[str, Any] = {
        "file": file,
        "poll_interval": int(interval.total_seconds()),
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

    harness.test_app.register_service(notifier, "", capture)
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


def test_sequential_polls_only_emit_new_lines(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("first batch\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "first batch\n" in calls[0]["message"]

    with open(log_file, "a") as f:
        f.write("second batch\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    assert "second batch\n" in calls[1]["message"]
    assert "first batch\n" not in calls[1]["message"]


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


def test_enabler_disabled_suppresses_notification(harness: Harness, tmp_path: Any) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    enabler: Any = harness.create_app(
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
    harness.clear_errors()

    log_file.write_text("fresh line a\nfresh line b\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    assert "fresh line a\nfresh line b\n" in calls[1]["message"]