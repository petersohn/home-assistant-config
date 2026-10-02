from __future__ import annotations
import os
import sys
import threading
import time

import pytest

# Make the integration-test helpers package importable.
_TEST_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _TEST_ROOT not in sys.path:
    sys.path.insert(0, _TEST_ROOT)

from appdaemon_integration_test.helpers.error_log import ErrorLogChecker

BORDER = "=" * 75


def _write_lines(path: str, lines: list[str]) -> None:
    with open(path, "a") as f:
        for line in lines:
            f.write(line + "\n")


def _block_lines(message: str) -> list[str]:
    return [
        f"2026-10-02 22:01:10.610592 ERROR test_auto_switch: {BORDER}",
        f"2026-10-02 22:01:10.612146 ERROR test_auto_switch: Unexpected error: 'test_auto_switch'",
        f"2026-10-02 22:01:10.617963 ERROR test_auto_switch: {message}",
        f"2026-10-02 22:01:10.618128 ERROR test_auto_switch: {BORDER}",
    ]


@pytest.fixture
def error_log_path(tmp_path: str) -> str:
    path = os.path.join(tmp_path, "error.log")
    open(path, "w").close()
    return path


@pytest.fixture
def checker(error_log_path: str) -> ErrorLogChecker:
    # Short wait so the degraded-deadline tests stay fast.
    return ErrorLogChecker(error_log_path, wait_timeout=0.5)


def test_allows_matching_block(checker: ErrorLogChecker, error_log_path: str) -> None:
    checker.mark_test_start()
    checker.allow_errors("KeyError")
    _write_lines(error_log_path, _block_lines("KeyError: 'test_auto_switch'"))
    checker.check_no_unexpected_errors()


def test_flags_unexpected_block(checker: ErrorLogChecker, error_log_path: str) -> None:
    checker.mark_test_start()
    _write_lines(error_log_path, _block_lines("ValueError: boom"))
    with pytest.raises(AssertionError):
        checker.check_no_unexpected_errors()


def test_allowance_does_not_leak_to_next_test(
    checker: ErrorLogChecker, error_log_path: str
) -> None:
    checker.mark_test_start()
    checker.allow_errors("KeyError")
    _write_lines(error_log_path, _block_lines("KeyError: 'x'"))
    checker.check_no_unexpected_errors()
    checker.mark_test_start()
    _write_lines(error_log_path, _block_lines("KeyError: 'x'"))
    with pytest.raises(AssertionError):
        checker.check_no_unexpected_errors()


def test_check_waits_for_block_being_written(
    checker: ErrorLogChecker, error_log_path: str
) -> None:
    """A block completing while the check runs must be read in full.

    AppDaemon writes error blocks line by line. A check that reads while
    the block is still being written would otherwise parse a partial
    block, which may not contain the allow-listed substring yet.
    """
    checker.mark_test_start()
    checker.allow_errors("KeyError")
    lines = _block_lines("KeyError: 'test_auto_switch'")
    _write_lines(error_log_path, lines[:-1])

    def complete_block() -> None:
        time.sleep(0.2)
        _write_lines(error_log_path, lines[-1:])

    t = threading.Thread(target=complete_block)
    t.start()
    try:
        checker.check_no_unexpected_errors()
    finally:
        t.join()


def test_check_parses_partial_block_when_wait_expires(
    checker: ErrorLogChecker, error_log_path: str
) -> None:
    """A block that never completes is still parsed (degraded path).

    If the writer died mid-block, surfacing the partial block beats
    silently dropping it: a partial block matches no allowance and
    fails the test, drawing attention to the broken writer.
    """
    checker.mark_test_start()
    lines = _block_lines("KeyError: 'test_auto_switch'")
    _write_lines(error_log_path, lines[:-1])  # closing border never lands
    with pytest.raises(AssertionError):
        checker.check_no_unexpected_errors()


def test_mark_test_start_waits_for_block_being_written(
    checker: ErrorLogChecker, error_log_path: str
) -> None:
    """The test-start boundary must not land inside a block.

    The previous test's teardown-time race block is written
    asynchronously; the boundary may be sampled mid-block. A boundary
    inside a block exposes the next test to an orphaned tail that no
    allowance can match. The boundary must wait for the block to
    complete and land past it, so the next test sees no new content.
    """
    lines = _block_lines("KeyError: 'test_auto_switch'")
    _write_lines(error_log_path, lines[:-1])
    # No allowance: the completed block belongs to the window before
    # this mark, so the next test must not see it at all.

    def complete_block() -> None:
        time.sleep(0.2)
        _write_lines(error_log_path, lines[-1:])

    t = threading.Thread(target=complete_block)
    t.start()
    try:
        checker.mark_test_start()
    finally:
        t.join()
    checker.check_no_unexpected_errors()


def test_mark_test_start_expires_on_never_completed_block(
    checker: ErrorLogChecker, error_log_path: str
) -> None:
    """Degraded path: an unterminated block falls to the next window whole.

    If no closing border lands within the timeout, the boundary falls
    back to the start of the open block. When the block later completes,
    the next test sees the whole block (not an orphaned tail), reported
    with full content so the failure is attributable.
    """
    lines = _block_lines("KeyError: 'test_auto_switch'")
    _write_lines(error_log_path, lines[:-1])
    checker.mark_test_start()  # waits out the timeout, then falls back
    _write_lines(error_log_path, lines[-1:])  # border lands after the mark
    # The whole block is now inside this test's window; with no
    # allowance it is unexpected, and the error shows the full block.
    with pytest.raises(AssertionError) as excinfo:
        checker.check_no_unexpected_errors()
    message = str(excinfo.value)
    # Full block attributed: opening border, message, closing border.
    assert "Unexpected error: 'test_auto_switch'" in message
    # And an allowance (had the test opted in) would match it.
    checker.allow_errors("KeyError")
    checker.check_no_unexpected_errors()