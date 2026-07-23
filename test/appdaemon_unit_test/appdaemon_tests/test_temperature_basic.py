from __future__ import annotations


def test_basic(harness):
    in_ = "sensor.furnace_in"
    out_ = "sensor.furnace_out"
    target = "input_boolean.temperature_controller_pump"
    harness.set_state(in_, 20)
    harness.set_state(out_, 20)
    harness.set_state(target, "off")
    harness.create_app(
        "temperature_basic",
        "TemperatureBasic",
        "heating_pump",
        sensor_in=in_,
        sensor_out=out_,
        target=target,
        target_difference=5,
        tolerance=1,
        maximum_out=80,
        minimum_out=30,
    )

    harness.set_state(out_, 25)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 28)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 30)
    assert harness.get_state(target) == "on"
    harness.set_state(out_, 40)
    assert harness.get_state(target) == "on"
    harness.set_state(in_, 33)
    assert harness.get_state(target) == "on"
    harness.set_state(in_, 35)
    assert harness.get_state(target) == "on"
    harness.set_state(in_, 37)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 41)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 42)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 44)
    assert harness.get_state(target) == "on"
    harness.set_state(out_, 79)
    assert harness.get_state(target) == "on"
    harness.set_state(in_, 79)
    assert harness.get_state(target) == "off"
    harness.set_state(out_, 80)
    assert harness.get_state(target) == "on"
    harness.set_state(in_, 20)
    assert harness.get_state(target) == "on"
    harness.set_state(out_, 28)
    assert harness.get_state(target) == "off"