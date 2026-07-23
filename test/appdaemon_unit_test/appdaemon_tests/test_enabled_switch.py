from __future__ import annotations


def _initialize(harness):
    harness.set_state("input_boolean.test_switch", "off")
    harness.set_state("input_boolean.test_switch2", "off")


def _create_enabler_and_switch(harness, initial, **kwargs):
    enabler = harness.create_app("enabler", "ScriptEnabler", "enabler", initial=initial)
    enabled_switch = harness.create_app(
        "enabled_switch", "EnabledSwitch", "enabled_switch",
        enabler="enabler", **kwargs,
    )
    return enabler, enabled_switch


def _create_basic_enabled_switch(harness, initial):
    switch1 = harness.create_app("auto_switch", "AutoSwitch", "switch1", target="input_boolean.test_switch")
    switch2 = harness.create_app("auto_switch", "AutoSwitch", "switch2", target="input_boolean.test_switch2")
    targets = ["switch1", "switch2"]
    enabler, enabled_switch = _create_enabler_and_switch(harness, initial, targets=targets)
    return switch1, switch2, enabler, enabled_switch


def _create_enabled_switch_with_guards(harness):
    on_guard = harness.create_app("enabler", "ScriptEnabler", "on_guard", initial=False)
    off_guard = harness.create_app("enabler", "ScriptEnabler", "off_guard", initial=False)
    switch = harness.create_app("auto_switch", "AutoSwitch", "switch", target="input_boolean.test_switch")
    targets = ["switch"]
    enabler, enabled_switch = _create_enabler_and_switch(
        harness, False, targets=targets, on_guard="on_guard", off_guard="off_guard",
    )
    return on_guard, off_guard, switch, enabler, enabled_switch


def test_start_with_off(harness):
    _initialize(harness)
    switch1, switch2, enabler, enabled_switch = _create_basic_enabled_switch(harness, False)
    assert harness.get_state("input_boolean.test_switch") == "off"
    assert harness.get_state("input_boolean.test_switch2") == "off"
    enabler.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    assert harness.get_state("input_boolean.test_switch2") == "on"
    enabler.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    assert harness.get_state("input_boolean.test_switch2") == "off"


def test_start_with_on(harness):
    _initialize(harness)
    switch1, switch2, enabler, enabled_switch = _create_basic_enabled_switch(harness, True)
    assert harness.get_state("input_boolean.test_switch") == "on"
    assert harness.get_state("input_boolean.test_switch2") == "on"
    enabler.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    assert harness.get_state("input_boolean.test_switch2") == "off"
    enabler.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    assert harness.get_state("input_boolean.test_switch2") == "on"


def test_guards(harness):
    _initialize(harness)
    on_guard, off_guard, switch, enabler, enabled_switch = _create_enabled_switch_with_guards(harness)
    assert harness.get_state("input_boolean.test_switch") == "off"
    enabler.enable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    on_guard.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    enabler.disable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    off_guard.enable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    enabler.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    enabler.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"


def test_turn_guards_on_and_off(harness):
    _initialize(harness)
    on_guard, off_guard, switch, enabler, enabled_switch = _create_enabled_switch_with_guards(harness)
    assert harness.get_state("input_boolean.test_switch") == "off"
    on_guard.enable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    on_guard.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    off_guard.enable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    off_guard.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"
    on_guard.enable()
    enabler.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    on_guard.disable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    off_guard.enable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    off_guard.disable()
    assert harness.get_state("input_boolean.test_switch") == "on"
    off_guard.enable()
    enabler.disable()
    assert harness.get_state("input_boolean.test_switch") == "off"