*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot
Library        DateTime
Library        libraries/date_time_util.py
Test Setup     Create Test Harness
Test Teardown  Cleanup Test Harness


*** Variables ***
${in} =      sensor.furnace_in
${out} =     sensor.furnace_out
${target} =  input_boolean.temperature_controller_pump


*** Test Cases ***

Basic
    Set State  ${in}  ${20}
    Set State  ${out}  ${20}
    Set State  ${target}  off
    Create App  temperature_basic  TemperatureBasic  heating_pump
    ...    sensor_in=${in}
    ...    sensor_out=${out}
    ...    target=${target}
    ...    target_difference=${5}
    ...    tolerance=${1}
    ...    maximum_out=${80}
    ...    minimum_out=${30}
    Set State  ${out}  ${25}
    State Should Be  ${target}  off
    Set State  ${out}  ${28}
    State Should Be  ${target}  off
    Set State  ${out}  ${30}
    State Should Be  ${target}  on
    Set State  ${out}  ${40}
    State Should Be  ${target}  on
    Set State  ${in}   ${33}
    State Should Be  ${target}  on
    Set State  ${in}   ${35}
    State Should Be  ${target}  on
    Set State  ${in}   ${37}
    State Should Be  ${target}  off
    Set State  ${out}  ${41}
    State Should Be  ${target}  off
    Set State  ${out}  ${42}
    State Should Be  ${target}  off
    Set State  ${out}  ${44}
    State Should Be  ${target}  on
    Set State  ${out}  ${79}
    State Should Be  ${target}  on
    Set State  ${in}   ${79}
    State Should Be  ${target}  off
    Set State  ${out}  ${80}
    State Should Be  ${target}  on
    Set State  ${in}   ${20}
    State Should Be  ${target}  on
    Set State  ${out}  ${28}
    State Should Be  ${target}  off


*** Keywords ***
