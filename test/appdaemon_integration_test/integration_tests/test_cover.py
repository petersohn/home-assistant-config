from __future__ import annotations
import time

from appdaemon_integration_test.helpers.appdaemon_client import AppDaemonClient
from appdaemon_integration_test.helpers.history_watcher import HistoryWatcher

input_entity1 = "sensor.test_cover_position1"
input_entity2 = "sensor.test_cover_position2"
output_entity = "input_number.cover_position"
availability_entity = "sensor.cover_available"
mode_switch = "input_select.test_cover_mode"
cover = "cover.test_cover"


def _initialize_services(appdaemon_client: AppDaemonClient) -> None:
    appdaemon_client.call_service("cover/close_cover", entity_id=cover)
    appdaemon_client.select_option(mode_switch, "stable")
    appdaemon_client.wait_for_state(output_entity, 0.0)
    appdaemon_client.wait_for_state(cover, "closed")


def _initialize(
    appdaemon_client: AppDaemonClient,
    history_watcher: HistoryWatcher,
    *configs: str,
) -> None:
    appdaemon_client.initialize_states(
        **{
            input_entity1: 0,
            input_entity2: 0,
            output_entity: 0,
            availability_entity: "on",
            mode_switch: "stable",
        }
    )
    _initialize_services(appdaemon_client)
    appdaemon_client.load_apps("HistoryWatcher", *configs)
    history_watcher.wait_for_history(mode_switch, "auto", mode_switch, "stable")
    history_watcher.check_history(mode_switch, "auto", mode_switch, "stable")


def _wait_for_mode_quiescence(
    appdaemon_client: AppDaemonClient,
    quiet_seconds: float = 1.0,
    timeout: float = 15.0,
) -> None:
    """Wait until the mode switch settles on "stable" and stays there.

    CoverController's initialization flip-flops the mode switch (auto ->
    stable -> auto -> stable) through its own on_mode_change listener,
    and the last writes are asynchronous. Waiting for a single (auto,
    stable) history pair returns before the flip-flop finishes, and a
    straggler "stable" write can then clobber a mode selected right
    afterwards (e.g. "manual" in test_reload_while_manual). Requiring
    the mode to hold "stable" continuously ensures every pending write
    has landed.
    """
    deadline = time.time() + timeout
    last_change = time.time()
    last_state: object = object()
    while time.time() < deadline:
        state = appdaemon_client.get_state(mode_switch)
        if state != last_state:
            last_state = state
            last_change = time.time()
        if state == "stable" and time.time() - last_change >= quiet_seconds:
            return
        time.sleep(0.05)
    assert last_state == "stable" and time.time() - last_change >= quiet_seconds, (
        f"mode switch did not settle on stable: last state {last_state!r}"
    )


def test_simple_state_changes(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(appdaemon_client, history_watcher, "Cover1")
    appdaemon_client.set_state(input_entity1, 50)
    history_watcher.wait_for_history(mode_switch, "auto", mode_switch, "stable")
    history_watcher.check_history(
        mode_switch, "auto", output_entity, 50.0, mode_switch, "stable"
    )
    appdaemon_client.set_state(input_entity1, "open")
    history_watcher.wait_for_history(mode_switch, "auto", mode_switch, "stable")
    history_watcher.check_history(
        mode_switch, "auto", output_entity, 100.0, mode_switch, "stable"
    )
    appdaemon_client.set_state(input_entity1, "closed")
    history_watcher.wait_for_history(mode_switch, "auto", mode_switch, "stable")
    history_watcher.check_history(
        mode_switch, "auto", output_entity, 0.0, mode_switch, "stable"
    )


def test_reload_while_stable(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(appdaemon_client, history_watcher, "Cover1")
    appdaemon_client.set_state(input_entity1, 60)
    appdaemon_client.set_state(input_entity2, 40)
    history_watcher.wait_for_history(mode_switch, "auto", mode_switch, "stable")
    history_watcher.check_history(
        mode_switch, "auto", output_entity, 60.0, mode_switch, "stable"
    )
    appdaemon_client.load_apps("HistoryWatcher", "Cover2", "dummy1")


def test_reload_while_manual(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(appdaemon_client, history_watcher, "Cover1")
    # CoverController's initialization flip-flops the mode switch (auto ->
    # stable -> auto -> stable) with asynchronous writes; the last "stable"
    # can land after the (auto, stable) history pair above is observed.
    # Wait for quiescence before selecting "manual", otherwise the
    # straggler write clobbers it.
    _wait_for_mode_quiescence(appdaemon_client)
    appdaemon_client.select_option(mode_switch, "manual")
    appdaemon_client.set_state(input_entity2, 40)
    appdaemon_client.load_apps("HistoryWatcher", "Cover2", "dummy1")
    time.sleep(3)
    assert appdaemon_client.get_state(mode_switch) == "manual"
    appdaemon_client.wait_for_state(output_entity, 0.0)