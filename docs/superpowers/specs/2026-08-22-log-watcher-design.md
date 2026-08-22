# Log Watcher App Design

## Purpose

An AppDaemon app that watches a log file and sends notifications when new lines are written. Polls the file at a configurable interval; batches new lines per poll cycle into a single notification.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Notification mechanism | `self.call_service(notifier, message=..., **args)` | First AppDaemon app to send notifications; no existing precedent. Notifier service name passed as config arg. |
| Enabler behavior | Poll always, notify only when enabled | Position advances regardless of enabler. Lines during disabled period are consumed (offset updated), not buffered. |
| Position persistence | Tail from end on startup | In-memory offset only. Lines written while app is down are lost. Simpler than persisting across restarts. |
| File rotation | Reset to 0 on shrink | If file size < offset, reset offset to 0 and read from start. Handles truncation/recreation. |
| File missing | Treat as truncation, reset to 0 | Same as rotation. When file reappears, read from start. |
| Notification batching | Batch per poll cycle | All lines read in one poll cycle joined into a single message. |
| Extra service kwargs | `args` dict passed verbatim | Config accepts optional `args` (e.g. `title: "Syslog"`) forwarded to `call_service`. |
| Enabler callback | None | No `add_callback`. `poll()` reads `is_enabled()` each tick. No cleanup needed in `terminate()`. |
| Timer cleanup | Automatic | AppDaemon cancels timers created by the app's own `run_every` on terminate. No `cancel_timer` needed. |
| Stat before open | Yes | `os.stat` first; if size unchanged, skip opening file entirely. |

## Architecture

New app `log_watcher.py` (`LogWatcher` class), derives from local `hass.Hass`.

### Config args

All read from `self.args` in `initialize()`, saved to instance attributes:

- `file` (`str`): path to log file to watch.
- `poll_interval` (`dict` for `timedelta`): poll frequency. Passed to `run_every`.
- `notifier` (`str`): service name to call (e.g. `notify.telegram`).
- `enabler` (`str`): name of an `Enabler` app to gate notifications.
- `args` (`dict | None`): extra kwargs passed verbatim to `call_service` (e.g. `title: "Syslog"`). Defaults to `{}`.

### Instance state (mutex-guarded after initialize)

- `self.mutex`: from `locker.get_mutex("LogWatcher")`.
- `self.offset` (`int`): byte offset of last read. On startup, set to file size (tail from end).
- `self.timer` (`str | None`): `run_every` handle.
- `self.enabler`: enabler app reference (for `is_enabled()` calls).

### Lifecycle

**`initialize()`:**
1. Read config args from `self.args`, save to instance attributes.
2. Acquire mutex from `locker.get_mutex("LogWatcher")`.
3. Get enabler app via `self.get_app(self.enabler_name)`, assert `isinstance(enabler_app, enabler.Enabler)`.
4. `os.stat(self.file)` → set `self.offset = st_size` (tail from end). If file missing, `self.offset = 0`.
5. Start `run_every(self.poll, self.datetime(), self.poll_interval.total_seconds())`.

**`terminate()`:**
- Empty. Timer auto-cancelled by AppDaemon. No callbacks registered on other apps.

## Poll logic

Public method `poll(self)` — called by `run_every` (unlocked, acquires mutex):

1. `os.stat(self.file)` → `st_size`.
   - If file missing: reset `self.offset = 0`, `self.error(...)`, return.
2. If `st_size == self.offset`: nothing new, return.
3. If `st_size < self.offset`: rotation/reset → `self.offset = 0`.
4. Open file (`open(self.file, "r")`), `seek(self.offset)`, read all new lines via `readlines()`.
5. Update `self.offset = f.tell()`.
6. If lines read:
   - `self.log(f"{len(lines)} new line(s) from {self.file}")` — logged always, regardless of enabler.
   - If `self.enabler.is_enabled()`: build message (join lines), `self.call_service(self.notifier, message=msg, **self.args)`.

### Edge cases

- **File missing on stat**: treat as truncation. Reset offset to 0. Log error. Don't crash. Next poll recovers when file reappears (reads from start).
- **File shrinks** (size < offset): rotation. Reset offset to 0. Read from start.
- **Empty read** (seek past EOF but size grew): no lines, update offset, return.
- **Partial line at EOF**: `readlines()` returns it; next poll reads continuation. Standard tail behavior.
- **Enabler disabled**: poll still reads lines and updates offset (consuming them). Notification suppressed. When re-enabled, only newly written lines are notified (lines during disabled period already consumed).

## Enabler integration

`initialize()`:
```python
enabler_app = self.get_app(self.enabler_name)
assert isinstance(enabler_app, enabler.Enabler)
self.enabler = enabler_app
```

No `add_callback`, no `enabler_id`. `poll()` reads `self.enabler.is_enabled()` each tick.

`terminate()`: empty (timer auto-cancelled, no callbacks on other apps to remove).

## Testing

### Unit tests

File: `test/appdaemon_unit_test/appdaemon_tests/test_log_watcher.py`

Tests use temp files for real file I/O. Write to file, advance time, check `call_service` calls. Do not test log output, only behavior.

Cases:
1. Startup seeks to end — no notification on first poll.
2. New lines written → poll reads → notification sent with correct message.
3. Enabler disabled → no `call_service`. Re-enable enabler, write more lines, next poll emits only the new lines (lines during disabled period consumed via polling, not buffered).
4. File shrinks (rotation) → offset resets to 0, reads from start.
5. File missing → treat as truncation, reset offset to 0. Test: write 1 line, poll (emitted), delete file, poll (missing, offset=0), recreate file with 2 lines, poll (both emitted).
6. No new lines → no action.
7. `args` (extra kwargs) passed through to `call_service`.
8. Multiple lines in one poll → single notification, multiline message.

### Integration tests

Not needed. Single app, no cross-app interactions beyond enabler (well-covered by unit tests). File I/O deterministic, not AppDaemon-internal behavior.

## App config example

```yaml
log_watcher_syslog:
  module: log_watcher
  class: LogWatcher
  file: /var/log/syslog
  poll_interval:
    seconds: 30
  notifier: notify.telegram
  enabler: log_watcher_enabler
  args:
    title: Syslog
  dependencies:
    - locker
    - log_watcher_enabler
```