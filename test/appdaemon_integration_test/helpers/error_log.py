from __future__ import annotations

import os

_BORDER = "=" * 75


class _Allow:
    """Context manager returned by :meth:`ErrorLogChecker.allow_errors`.

    On exit, removes the allow-listed substring from the checker.
    """

    def __init__(self, checker: "ErrorLogChecker", message_substring: str) -> None:
        self._checker = checker
        self._message_substring = message_substring

    def __enter__(self) -> "ErrorLogChecker":
        return self._checker

    def __exit__(self, *exc: object) -> None:
        if self._message_substring in self._checker._allowed:
            self._checker._allowed.remove(self._message_substring)


class ErrorLogChecker:
    """Tracks new error.log entries per test and tolerates allow-listed blocks.

    AppDaemon writes error blocks delimited by a line of 75 ``=`` characters.
    Each block contains an ``Unexpected error: <repr>`` line. A test opens a
    context via :meth:`allow_errors` to tolerate blocks whose text matches a
    given substring (e.g. ``KeyError`` raised by an AppDaemon-internal race
    during reload).
    """

    def __init__(self, error_log_path: str) -> None:
        self._path = error_log_path
        self._offset: int = 0
        self._allowed: list[str] = []

    def mark_test_start(self) -> None:
        """Record the current end of error.log; new entries after this are new."""
        self._offset = self._size()
        self._allowed = []

    def allow_errors(self, message_substring: str) -> _Allow:
        """Tolerate error blocks whose text contains the substring."""
        self._allowed.append(message_substring)
        return _Allow(self, message_substring)

    def check_no_unexpected_errors(self) -> None:
        """Assert no error blocks were written after the test-start marker,
        except those matching a currently-allowed substring."""
        new_content = self._read_from(self._offset)
        blocks = self._parse_blocks(new_content)
        unexpected = []
        for block in blocks:
            if not any(sub in block for sub in self._allowed):
                unexpected.append(block)
        assert not unexpected, (
            "Unexpected error.log entries written during test:\n"
            + "\n".join(unexpected)
        )

    def _size(self) -> int:
        try:
            return os.path.getsize(self._path)
        except OSError:
            return 0

    def _read_from(self, offset: int) -> str:
        try:
            with open(self._path, "r") as f:
                f.seek(offset)
                return f.read()
        except OSError:
            return ""

    @staticmethod
    def _parse_blocks(content: str) -> list[str]:
        blocks: list[str] = []
        current: list[str] = []
        in_block = False
        for line in content.splitlines():
            is_border = line.endswith(_BORDER) and " ERROR " in line
            if is_border:
                if in_block:
                    current.append(line)
                    blocks.append("\n".join(current))
                    current = []
                    in_block = False
                else:
                    in_block = True
                    current = [line]
            elif in_block:
                current.append(line)
        if current:
            blocks.append("\n".join(current))
        return blocks