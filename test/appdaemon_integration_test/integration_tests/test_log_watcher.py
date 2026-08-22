from __future__ import annotations

import os

from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient

sensor = "sensor.log_notifier"


def test_log_watcher_sequence(appdaemon_client: AppDaemonClient) -> None:
    watched_log = os.path.join(appdaemon_client.dir, "notify", "watched.log")
    appdaemon_client.load_apps("LogWatcher1")

    with open(watched_log, "w") as f:
        f.write("initial line\n")
    appdaemon_client.wait_for_state(sensor, "initial line")

    with open(watched_log, "a") as f:
        f.write("second line\n")
    appdaemon_client.wait_for_state(sensor, "second line")

    with open(watched_log, "w") as f:
        f.write("rotated line\n")
    appdaemon_client.wait_for_state(sensor, "rotated line")