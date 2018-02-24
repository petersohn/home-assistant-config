*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize Simple
Test Teardown  Cleanup AppDaemon


*** Variables ***

${furnace_sensor} =       sensor.furnace
${outside_sensor} =       sensor.outside
${availability_sensor} =  binary_sensor.available
${switch} =               input_boolean.temperature_controller_pump
${minimum_temperature} =  ${30.0}
${low_mode_start} =       15 min
${low_mode_time} =        5 min
${tolerance} =            ${1.0}

${simple_target} =  ${50.0}


*** Test Cases ***

Switch On And Off
    ${low_temperature} =  Evaluate  ${simple_target} - ${tolerance} - 1.0
    ${high_temperature} =  Evaluate  ${simple_target} + ${tolerance} + 1.0
    Switch State Should Be After temperature Change  ${low_temperature}  off
    Switch State Should Be After temperature Change  ${simple_target}  off
    Switch State Should Be After temperature Change  ${high_temperature}  on
    Switch State Should Be After temperature Change  ${simple_target}  on
    Switch State Should Be After temperature Change  ${low_temperature}  off

*** Keywords ***

Switch State Should Be After temperature Change
    [Arguments]  ${temperature}  ${state}
    Set State  ${furnace_sensor}  ${temperature}
    Wait Until State Becomes  ${switch}  ${state}

Initialize Simple
    Clean States
    Initialize States
    ...    ${furnace_sensor}=${10}
    ...    ${outside_sensor}=${10}
    ...    ${availability_sensor}=on
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  temperature_controller
    ${app_configs} =  Create List  TestApp  TemperatureControllerSimple
    Initialize AppDaemon  ${apps}  ${app_configs}
