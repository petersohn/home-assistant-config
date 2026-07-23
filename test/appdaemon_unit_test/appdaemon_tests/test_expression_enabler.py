from __future__ import annotations
import pytest

input_binary1 = "binary_sensor.test_input1"
input_binary2 = "binary_sensor.test_input2"
input_sensor1 = "sensor.test_input1"
input_sensor2 = "sensor.test_input2"


def _create_expression_enabler(harness, name, expr):
    return harness.create_app("enabler", "ExpressionEnabler", name, expr=expr)


def _check_expected_states(harness, expected_states):
    for name, value in expected_states.items():
        app = harness.get_app(name)
        assert app.is_enabled() == value


@pytest.mark.parametrize("enabler1_state, enabler2_state, expected_states", [
    (False, False, {"enablers_and": False, "enablers_nand": True, "enablers_and_not": False, "enablers_or": False}),
    (False, True, {"enablers_and": False, "enablers_nand": True, "enablers_and_not": False, "enablers_or": True}),
    (True, False, {"enablers_and": False, "enablers_nand": True, "enablers_and_not": True, "enablers_or": True}),
    (True, True, {"enablers_and": True, "enablers_nand": False, "enablers_and_not": False, "enablers_or": True}),
])
def test_enablers(harness, enabler1_state, enabler2_state, expected_states):
    harness.create_app("enabler", "ScriptEnabler", "enabler1", initial=enabler1_state)
    harness.create_app("enabler", "ScriptEnabler", "enabler2", initial=enabler2_state)
    _create_expression_enabler(harness, "enablers_and", "e.enabler1 and e.enabler2")
    _create_expression_enabler(harness, "enablers_nand", "not (e.enabler1 and e.enabler2)")
    _create_expression_enabler(harness, "enablers_and_not", "e.enabler1 and not e.enabler2")
    _create_expression_enabler(harness, "enablers_or", "e.enabler1 or e.enabler2")
    _check_expected_states(harness, expected_states)


@pytest.mark.parametrize("sensor1, sensor2, expected_states", [
    (-1, -1, {"value_less": False, "value_equal": True}),
    (-1, 0, {"value_less": True, "value_equal": False}),
    (-1, 5, {"value_less": True, "value_equal": False}),
    (-1, 10, {"value_less": True, "value_equal": False}),
    (0, -1, {"value_less": False, "value_equal": False}),
    (0, 0, {"value_less": False, "value_equal": True}),
    (0, 5, {"value_less": True, "value_equal": False}),
    (0, 10, {"value_less": True, "value_equal": False}),
    (5, -1, {"value_less": False, "value_equal": False}),
    (5, 0, {"value_less": False, "value_equal": False}),
    (5, 5, {"value_less": False, "value_equal": True}),
    (5, 10, {"value_less": True, "value_equal": False}),
    (10, -1, {"value_less": False, "value_equal": False}),
    (10, 0, {"value_less": False, "value_equal": False}),
    (10, 5, {"value_less": False, "value_equal": False}),
    (10, 10, {"value_less": False, "value_equal": True}),
])
def test_numeric_sensors(harness, sensor1, sensor2, expected_states):
    harness.set_state(input_sensor1, sensor1)
    harness.set_state(input_sensor2, sensor2)
    _create_expression_enabler(harness, "value_less", f"v.{input_sensor1} < v.{input_sensor2}")
    _create_expression_enabler(harness, "value_equal", f"v.{input_sensor1} == v.{input_sensor2}")
    _check_expected_states(harness, expected_states)


@pytest.mark.parametrize("sensor1, sensor2, expected_states", [
    ("a", "a", {"value_less": False, "value_equal": True}),
    ("a", "b", {"value_less": True, "value_equal": False}),
    ("b", "a", {"value_less": False, "value_equal": False}),
    ("a", "aa", {"value_less": True, "value_equal": False}),
    ("aa", "a", {"value_less": False, "value_equal": False}),
    ("aa", "aa", {"value_less": False, "value_equal": True}),
])
def test_alphanumeric_sensors(harness, sensor1, sensor2, expected_states):
    harness.set_state(input_sensor1, sensor1)
    harness.set_state(input_sensor2, sensor2)
    _create_expression_enabler(harness, "value_less", f"v.{input_sensor1} < v.{input_sensor2}")
    _create_expression_enabler(harness, "value_equal", f"v.{input_sensor1} == v.{input_sensor2}")
    _check_expected_states(harness, expected_states)


@pytest.mark.parametrize("sensor1, sensor2, expected_states", [
    ("off", "off", {"binary_and": False, "binary_or": False}),
    ("off", "on", {"binary_and": False, "binary_or": True}),
    ("on", "off", {"binary_and": False, "binary_or": True}),
    ("on", "on", {"binary_and": True, "binary_or": True}),
])
def test_binary_sensors(harness, sensor1, sensor2, expected_states):
    harness.set_state(input_binary1, sensor1)
    harness.set_state(input_binary2, sensor2)
    _create_expression_enabler(harness, "binary_and", f"v.{input_binary1} and v.{input_binary2}")
    _create_expression_enabler(harness, "binary_or", f"v.{input_binary1} or v.{input_binary2}")
    _check_expected_states(harness, expected_states)


@pytest.mark.parametrize("enabler_state, sensor, expected_states", [
    (False, "off", {"enabler_and_binary_and": False, "enabler_and_binary_or": False}),
    (False, "on", {"enabler_and_binary_and": False, "enabler_and_binary_or": True}),
    (True, "off", {"enabler_and_binary_and": False, "enabler_and_binary_or": True}),
    (True, "on", {"enabler_and_binary_and": True, "enabler_and_binary_or": True}),
])
def test_enabler_and_binary_sensor(harness, enabler_state, sensor, expected_states):
    harness.create_app("enabler", "ScriptEnabler", "enabler", initial=enabler_state)
    harness.set_state(input_binary1, sensor)
    _create_expression_enabler(
        harness, "enabler_and_binary_and", f"e.enabler and v.{input_binary1}"
    )
    _create_expression_enabler(
        harness, "enabler_and_binary_or", f"e.enabler or v.{input_binary1}"
    )
    _check_expected_states(harness, expected_states)


def test_changes(harness):
    harness.set_state(input_binary1, "off")
    harness.set_state(input_binary2, "off")
    _create_expression_enabler(harness, "enabler1", f"v.{input_binary1}")
    _create_expression_enabler(harness, "enabler2", f"not v.{input_binary2}")
    enabler = _create_expression_enabler(harness, "enabler", "e.enabler1 and e.enabler2")
    assert enabler.is_enabled() == False
    harness.set_state(input_binary1, "on")
    assert enabler.is_enabled() == True
    harness.set_state(input_binary2, "on")
    assert enabler.is_enabled() == False