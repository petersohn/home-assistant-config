from __future__ import annotations

import time

_BORDER = "=" * 75
_POLL_INTERVAL = 0.05


class ErrorLogChecker:
    """Tracks new error.log entries per test and tolerates allow-listed blocks.

    AppDaemon writes error blocks delimited by a line of 75 ``=`` characters.
    Each block contains an ``Unexpected error: <repr>`` line. A test calls
    :meth:`allow_errors` before triggering code that may write a tolerated
    block (e.g. ``KeyError`` raised by an AppDaemon-internal race during
    app reload).

    The check runs once, at test teardown. Because a tolerated error block
    can be written asynchronously at any point after the triggering call —
    including during teardown-time app cleanup, which re-triggers the same
    race — the allowance is test-scoped, not call-scoped: it stays in
    effect until the next :meth:`mark_test_start` clears it.

    AppDaemon writes blocks line by line, so a block can be mid-write when
    the boundary is sampled or the check reads. Both operations wait for an
    unterminated block to complete (bounded by ``wait_timeout``) so a block
    is never cut in half: ``mark_test_start`` must not place the boundary
    inside a block (the next test would see an orphaned tail that no
    allowance can match), and the check must parse whole blocks. If a
    block never completes within the timeout (writer died), the boundary
    falls back to the start of the unterminated block so the completed
    content is reported with full diagnostics rather than as an
    unattributable tail.
    """

    _path: str
    _wait_timeout: float

    @property
    def allowed(self) -> list[str]:
        return self._allowed

    def __init__(
        self, error_log_path: str, wait_timeout: float = 5.0
    ) -> None:
        self._path = error_log_path
        self._wait_timeout = wait_timeout
        self._offset: int = 0
        self._allowed: list[str] = []

    def mark_test_start(self) -> None:
        """Record the current end of error.log; new entries after this are new.

        If an error block is mid-write, waits (bounded) for it to complete
        so the recorded boundary lies past the whole block, never inside it.
        """
        self._offset = self._boundary()
        self._allowed = []

    def allow_errors(self, message_substring: str) -> None:
        """Tolerate error blocks whose text contains the substring.

        Test-scoped: the allowance remains active for the rest of the
        test, until the next ``mark_test_start``.
        """
        self._allowed.append(message_substring)

    def check_no_unexpected_errors(self) -> None:
        """Assert no error blocks were written after the test-start marker,
        except those matching a currently-allowed substring."""
        content = self._read_from(self._offset)
        if self._ends_in_open_block(content):
            content = self._wait_for_completion(content)
        blocks = self._parse_blocks(content)
        unexpected: list[str] = []
        for block in blocks:
            if not any(sub in block for sub in self._allowed):
                unexpected.append(block)
        assert not unexpected, (
            "Unexpected error.log entries written during test:\n"
            + "\n".join(unexpected)
        )

    def _boundary(self) -> int:
        """Byte offset past all complete content, at a block boundary.

        Waits (bounded) for a mid-write block to complete and returns the
        size of the completed content. If the block never completes within
        the timeout, returns the offset of the unterminated block's opening
        border instead, so the block is wholly attributed to the next
        window (and reported with full content) rather than split.
        """
        content = self._read_from(0)
        if not self._ends_in_open_block(content):
            return len(content.encode())
        open_block_start = self._open_block_start(content)
        deadline = time.monotonic() + self._wait_timeout
        while time.monotonic() < deadline:
            time.sleep(_POLL_INTERVAL)
            content = self._read_from(0)
            if not self._ends_in_open_block(content):
                return len(content.encode())
        return open_block_start

    def _wait_for_completion(self, partial: str) -> str:
        """Wait (bounded) for the unterminated block at the end to complete."""
        content = partial
        deadline = time.monotonic() + self._wait_timeout
        while time.monotonic() < deadline:
            time.sleep(_POLL_INTERVAL)
            content = self._read_from(self._offset)
            if not self._ends_in_open_block(content):
                return content
        return content

    @staticmethod
    def _is_border(line: str) -> bool:
        return line.endswith(_BORDER) and " ERROR " in line

    @classmethod
    def _ends_in_open_block(cls, content: str) -> bool:
        in_block = False
        for line in content.splitlines():
            if cls._is_border(line):
                in_block = not in_block
        return in_block

    @classmethod
    def _open_block_start(cls, content: str) -> int:
        """Byte offset of the opening border of the trailing open block.

        Call only when :meth:`_ends_in_open_block` is true for ``content``.
        """
        offset = 0
        open_start = 0
        in_block = False
        for line in content.splitlines():
            line_start = offset
            offset += len(line.encode()) + 1  # +1 for the newline
            if cls._is_border(line):
                if not in_block:
                    in_block = True
                    open_start = line_start
        assert in_block
        return open_start

    def _read_from(self, offset: int) -> str:
        try:
            with open(self._path, "rb") as f:
                f.seek(offset)
                return f.read().decode(errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _parse_blocks(content: str) -> list[str]:
        blocks: list[str] = []
        current: list[str] = []
        in_block = False
        for line in content.splitlines():
            if ErrorLogChecker._is_border(line):
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