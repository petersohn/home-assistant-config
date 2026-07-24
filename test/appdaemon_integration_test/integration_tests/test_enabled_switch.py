from __future__ import annotations
import time

import pytest

from helpers.appdaemon_client import AppDaemonClient
from helpers.history_watcher import HistoryWatcher

input_switch1 = "input_select.test_auto_switch_switch1"
input_switch2 = "input_select.test_auto_switch_switch2"
output_switch = "input_boolean.test_switch1"
enabler = "test_enabler"

base_configs = ("HistoryWatcher", "EnabledSwitch")


def _initialize(
    appdaemon_client: AppDaemonClient, *configs: str, **initial_states: object
) -> None:
    appdaemon_client.initialize_states(**{output_switch: "off"}, **initial_states)
    appdaemon_client.load_apps(*configs)


def _enable(appdaemon_client: AppDaemonClient) -> None:
    appdaemon_client.call_on_app(enabler, "enable")


def _disable(appdaemon_client: AppDaemonClient) -> None:
    appdaemon_client.call_on_app(enabler, "disable")


def test_state_changes(
    appdaemon_client: AppDaemonClient, history_watcher: HistoryWatcher
) -> None:
    _initialize(
        appdaemon_client,
        *base_configs,
        "AutoSwitch1",
        "ScriptEnablerOff",
        **{input_switch1: "auto"},
    )
    assert appdaemon_client.get_state(output_switch) == "off"
    appdaemon_client.select_option(input_switch1, "on")
    appdaemon_client.wait_for_state(output_switch, "on")
    appdaemon_client.select_option(input_switch1, "auto")
    appdaemon_client.wait_for_state(output_switch, "off")
    _enable(appdaemon_client)
    appdaemon_client.wait_for_state(output_switch, "on")
    _disable(appdaemon_client)
    appdaemon_client.wait_for_state(output_switch, "off")
    appdaemon_client.select_option(input_switch1, "on")
    appdaemon_client.wait_for_state(output_switch, "on")
    _enable(appdaemon_client)
    appdaemon_client.select_option(input_switch1, "off")
    appdaemon_client.wait_for_state(output_switch, "off")
    appdaemon_client.select_option(input_switch1, "auto")
    appdaemon_client.wait_for_state(output_switch, "on")
    appdaemon_client.select_option(input_switch1, "off")
    appdaemon_client.wait_for_state(output_switch, "off")
    history_watcher.check_history(
        output_switch, "on",
        output_switch, "off",
        output_switch, "on",
        output_switch, "off",
        output_switch, "on",
        output_switch, "off",
        output_switch, "on",
        output_switch, "off",
    )


test_reload_rows = [
    pytest.param(False, "Off", "off", "off", ["off"],
                 id="False_Off_off_off"),
    pytest.param(False, "Off", "on", "off", ["on", "off"],
                 id="False_Off_on_off"),
    pytest.param(False, "Off", "off", "on", ["off", "on"],
                 id="False_Off_off_on"),
    pytest.param(False, "Off", "on", "on", ["on"],
                 id="False_Off_on_on"),
    pytest.param(False, "Off", "off", "auto", ["off"],
                 id="False_Off_off_auto"),
    pytest.param(False, "Off", "on", "auto", ["on", "off"],
                 id="False_Off_on_auto"),
    pytest.param(False, "Off", "auto", "off", ["off"],
                 id="False_Off_auto_off"),
    pytest.param(False, "Off", "auto", "on", ["off", "on"],
                 id="False_Off_auto_on"),
    pytest.param(False, "Off", "auto", "auto", ["off"],
                 id="False_Off_auto_auto"),
    pytest.param(False, "On", "off", "auto", ["off", "on"],
                 id="False_On_off_auto"),
    pytest.param(False, "On", "on", "auto", ["on"],
                 id="False_On_on_auto"),
    pytest.param(False, "On", "auto", "off", ["on", "off"],
                 id="False_On_auto_off"),
    pytest.param(False, "On", "auto", "on", ["on"],
                 id="False_On_auto_on"),
    pytest.param(False, "On", "auto", "auto", ["on"],
                 id="False_On_auto_auto"),
    pytest.param(True, "Off", "off", "off", ["off"],
                 id="True_Off_off_off"),
    pytest.param(True, "Off", "on", "off", ["on", "off"],
                 id="True_Off_on_off"),
    pytest.param(True, "Off", "off", "on", ["off", "on"],
                 id="True_Off_off_on"),
    pytest.param(True, "Off", "on", "on", ["on"],
                 id="True_Off_on_on"),
    pytest.param(True, "Off", "off", "auto", ["off"],
                 id="True_Off_off_auto"),
    pytest.param(True, "Off", "on", "auto", ["on", "off"],
                 id="True_Off_on_auto"),
    pytest.param(True, "Off", "auto", "off", ["off"],
                 id="True_Off_auto_off"),
    pytest.param(True, "Off", "auto", "on", ["off", "on"],
                 id="True_Off_auto_on"),
    pytest.param(True, "Off", "auto", "auto", ["off"],
                 id="True_Off_auto_auto"),
    pytest.param(True, "On", "off", "auto", ["off", "on"],
                 id="True_On_off_auto"),
    pytest.param(True, "On", "on", "auto", ["on"],
                 id="True_On_on_auto"),
    pytest.param(True, "On", "auto", "off", ["on", "off"],
                 id="True_On_auto_off"),
    pytest.param(True, "On", "auto", "on", ["on", "off", "on"],
                 id="True_On_auto_on"),
    pytest.param(True, "On", "auto", "auto", ["on", "off", "on"],
                 id="True_On_auto_auto"),
]


@pytest.mark.parametrize("reentrant, enabler_state, initial, new, expected_states",
                         test_reload_rows)
def test_reload(
    appdaemon_client: AppDaemonClient,
    history_watcher: HistoryWatcher,
    reentrant: bool,
    enabler_state: str,
    initial: str,
    new: str,
    expected_states: list[str],
) -> None:
    reentrant_config = "Reentrant" if reentrant else ""
    enabler_config = "ScriptEnabler" + enabler_state
    auto_switch1 = "AutoSwitch1" + reentrant_config
    auto_switch2 = "AutoSwitch2" + reentrant_config

    _initialize(
        appdaemon_client,
        *base_configs,
        auto_switch1,
        enabler_config,
        **{input_switch1: initial, input_switch2: new},
    )

    expected_state1 = expected_states[0]
    expected_state2 = expected_states[-1]

    appdaemon_client.wait_for_state(output_switch, expected_state1)

    expected: list[str] = []
    if expected_state1 == "on":
        expected += [output_switch, "on"]
    history_watcher.check_history(*expected)

    appdaemon_client.load_apps(
        *base_configs, auto_switch2, enabler_config, "dummy1"
    )
    if expected_state1 == expected_state2:
        time.sleep(2)
    appdaemon_client.wait_for_state(output_switch, expected_state2)

    expected = []
    for state in expected_states[1:]:
        expected += [output_switch, state]
    history_watcher.check_history(*expected)
