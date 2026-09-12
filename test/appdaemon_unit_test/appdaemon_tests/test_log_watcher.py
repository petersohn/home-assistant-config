from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from appdaemon_unit_test.test_helpers.harness import Harness
from appdaemon_unit_test.test_helpers.hass import Hass
from enabler import ScriptEnabler


NOTIFIER = "notify/notify"


def _create_log_watcher(
    harness: Harness,
    file: str,
    poll_interval: timedelta | None = None,
    notifier: str = NOTIFIER,
    enabler: str | None = None,
    args: dict[str, object] | None = None,
) -> Hass:
    interval = poll_interval if poll_interval is not None else timedelta(seconds=10)
    kwargs: dict[str, object] = {
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


def _message(call: dict[str, object]) -> str:
    message = call["message"]
    assert isinstance(message, str)
    return message


def _register_notifier(harness: Harness, notifier: str = NOTIFIER) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def capture(data: dict[str, object]) -> None:
        calls.append(data)

    harness.test_app.register_service(notifier, "", capture)
    return calls


def test_startup_seeks_to_end(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing line\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    assert calls == []


def test_new_lines_notification(harness: Harness, tmp_path: Path) -> None:
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
    assert "new line 1\nnew line 2\n" in _message(calls[0])


def test_no_new_lines_no_action(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))
    harness.advance_time(timedelta(seconds=10))

    assert calls == []


def test_sequential_polls_only_emit_new_lines(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("first batch\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "first batch\n" in _message(calls[0])

    with open(log_file, "a") as f:
        f.write("second batch\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    assert "second batch\n" in _message(calls[1])
    assert "first batch\n" not in _message(calls[1])


def test_extra_args_passed_through(harness: Harness, tmp_path: Path) -> None:
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
    assert "hello\n" in _message(calls[0])


def test_html_like_content_escaped(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write('Failed: error=400 <string> at byte offset 24 "x"\n')
        f.write("a & b < c > d\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    message = _message(calls[0])
    assert "<string>" not in message
    assert "&lt;string&gt;" in message
    assert "a &amp; b &lt; c &gt; d" in message


def test_enabler_disabled_suppresses_notification(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    enabler = harness.create_app(
        "enabler", "ScriptEnabler", "test_enabler", initial=True
    )
    assert isinstance(enabler, ScriptEnabler)
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
    assert "after re-enable\n" in _message(calls[0])
    assert "while disabled\n" not in _message(calls[0])


def test_file_shrink_resets_offset(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing line 1\nexisting line 2\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    log_file.write_text("rotated fresh content\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "rotated fresh content\n" in _message(calls[0])


def test_oversized_message_split_into_chunks(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    line = "x" * 1000
    with open(log_file, "a") as f:
        for i in range(5):
            f.write(f"{line} {i}\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    for call in calls:
        assert len(_message(call)) <= 4000
    combined = "".join(_message(call) for call in calls)
    assert "0\n" in combined
    assert "4\n" in combined


def test_single_oversized_line_hard_split(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("y" * 9000 + "\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 3
    for call in calls:
        assert len(_message(call)) <= 4000
    assert "".join(_message(call) for call in calls) == "y" * 9000 + "\n"


def test_mixed_lines_split_preserves_all_content(
    harness: Harness, tmp_path: Path
) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("existing\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("z" * 3000 + "\n")
        f.write("w" * 4500 + "\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 3
    for call in calls:
        assert len(_message(call)) <= 4000
    assert "".join(_message(call) for call in calls) == (
        "z" * 3000 + "\n" + "w" * 4500 + "\n"
    )
    # First chunk ends at the 3000-char line boundary.
    assert _message(calls[0]) == "z" * 3000 + "\n"


def test_file_missing_then_recreated(harness: Harness, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("first line\n")
    calls = _register_notifier(harness)
    _create_log_watcher(harness, str(log_file))

    harness.advance_time(timedelta(seconds=10))

    with open(log_file, "a") as f:
        f.write("second line\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 1
    assert "second line\n" in _message(calls[0])

    log_file.unlink()

    harness.advance_time(timedelta(seconds=10))
    harness.clear_errors()

    log_file.write_text("fresh line a\nfresh line b\n")

    harness.advance_time(timedelta(seconds=10))

    assert len(calls) == 2
    assert "fresh line a\nfresh line b\n" in _message(calls[1])