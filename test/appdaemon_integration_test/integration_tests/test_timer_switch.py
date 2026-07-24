from __future__ import annotations
import time

from helpers.appdaemon_client import AppDaemonClient
from helpers.history_watcher import HistoryWatcher

start_sensor = "binary_sensor.start"
control_start_sensor = "binary_sensor.control_start"
control_time = "sensor.control_time"
enabler_switch = "binary_sensor.enabler_switch"
control_switch = "input_boolean.control_switch"
switch1 = "input_boolean.test_switch1"
switch2 = "input_boolean.test_switch2"
switch3 = "input_boolean.test_switch3"
base_configs = ("TimerSwitchControl", "HistoryWatcher")


def _initialize(appdaemon_client: AppDaemonClient, *configs: str) -> None:
    appdaemon_client.initialize_states(
        **{
            start_sensor: "off",
            control_start_sensor: "off",
            control_time: 0.25,
            enabler_switch: "off",
        }
    )
    appdaemon_client.load_apps(*configs)
    appdaemon_client.turn_off(control_switch)
    appdaemon_client.turn_off(switch1)
    appdaemon_client.turn_off(switch2)
    appdaemon_client.turn_off(switch3)


def _start_control(appdaemon_client: AppDaemonClient) -> None:
    appdaemon_client.set_state(start_sensor, "on")
    appdaemon_client.set_state(control_start_sensor, "on")
    appdaemon_client.wait_for_state(control_switch, "on")
    appdaemon_client.set_state(start_sensor, "off")
    appdaemon_client.set_state(control_start_sensor, "off")
    assert appdaemon_client.get_state(control_switch) == "on"


def _wait_for_control(history_watcher: HistoryWatcher) -> None:
    history_watcher.wait_for_history(control_switch, "on", control_switch, "off")


def _start_control_and_wait(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _start_control(appdaemon_client)
    _wait_for_control(history_watcher)


def test_control(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(appdaemon_client, *base_configs)
    appdaemon_client.set_state(control_time, 0.05)
    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(control_switch, "on", control_switch, "off")


def test_reload_because_of_dependency(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(appdaemon_client, *base_configs, "TimerSequences", "SwitchEnabler1")
    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch2, "on",
        switch2, "off",
        control_switch, "off",
    )
    appdaemon_client.set_state(enabler_switch, "on")
    time.sleep(1)
    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch1, "on",
        switch1, "off",
        control_switch, "off",
    )
    appdaemon_client.set_state(enabler_switch, "off")
    time.sleep(1)
    appdaemon_client.load_apps(
        *base_configs, "TimerSequences", "SwitchEnabler2", "dummy1"
    )
    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch1, "on",
        switch1, "off",
        control_switch, "off",
    )
    appdaemon_client.set_state(enabler_switch, "on")
    time.sleep(1)
    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch2, "on",
        switch2, "off",
        control_switch, "off",
    )
    appdaemon_client.set_state(enabler_switch, "off")


def test_only_reload_changed_apps(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(
        appdaemon_client,
        *base_configs,
        "TimerSequenceNoEnabler1_1",
        "TimerSequenceNoEnabler2",
    )
    _start_control(appdaemon_client)
    history_watcher.wait_for_history(switch1, "on")
    appdaemon_client.load_apps(
        *base_configs,
        "TimerSequenceNoEnabler1_2",
        "TimerSequenceNoEnabler2",
        "dummy1",
    )
    _wait_for_control(history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch2, "on",
        switch1, "on",
        switch1, "off",
        switch2, "off",
        control_switch, "off",
    )

    _start_control_and_wait(appdaemon_client, history_watcher)
    history_watcher.check_history(
        control_switch, "on",
        switch2, "on",
        switch3, "on",
        switch2, "off",
        switch3, "off",
        control_switch, "off",
    )