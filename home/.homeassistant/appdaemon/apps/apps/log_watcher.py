from __future__ import annotations

import datetime
import html
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
            self.poll_interval = datetime.timedelta(**self.args["poll_interval"])
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
            # Escape line-by-line so chunk boundaries never cut an HTML entity.
            message = "".join(html.escape(line) for line in lines)
            for chunk in self._split_message(message):
                self.call_service(self.notifier, message=chunk, **self.extra_args)

    # Telegram's limit is 4096 characters; leave some headroom.
    MESSAGE_LIMIT: int = 4000

    @staticmethod
    def _split_message(text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + LogWatcher.MESSAGE_LIMIT, len(text))
            if end < len(text):
                newline = text.rfind("\n", start, end)
                if newline != -1 and newline > start:
                    end = newline + 1
            chunks.append(text[start:end])
            start = end
        return chunks