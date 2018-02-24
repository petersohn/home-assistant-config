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

${high_outside_temperature} =  ${10}
${high_target} =  ${50.0}
${low_outside_temperature} =  ${0}
${low_target} =  ${60.0}


*** Test Cases ***

Switch On And Off At High Temperature
    Set State  ${outside_sensor}  ${high_outside_temperature}
    Verify Switch On And Off  ${high_target}  ${tolerance}

Switch On And Off At Low Temperature
    Set State  ${outside_sensor}  ${low_outside_temperature}
    Verify Switch On And Off  ${low_target}  ${tolerance}

Switch On And Off At Moderate Temperature
    ${outside_temperature} =  Evaluate
    ...    (${low_outside_temperature} + ${high_outside_temperature}) / 2
    ${target} =  Evaluate
    ...    (${low_target} + ${high_target}) / 2

    Set State  ${outside_sensor}  ${outside_temperature}
    Verify Switch On And Off  ${target}  ${tolerance}


*** Keywords ***

Switch State Should Be After temperature Change
    [Arguments]  ${temperature}  ${state}
    Set State  ${furnace_sensor}  ${temperature}
    Wait Until State Becomes  ${switch}  ${state}

Verify Switch On And Off
    [Arguments]  ${target}  ${tolerance}
    ${low} =  Evaluate  ${target} - ${tolerance} - 1.0
    ${high} =  Evaluate  ${target} + ${tolerance} + 1.0
    Switch State Should Be After temperature Change  ${low}  off
    Switch State Should Be After temperature Change  ${target}  off
    Switch State Should Be After temperature Change  ${high}  on
    Switch State Should Be After temperature Change  ${target}  on
    Switch State Should Be After temperature Change  ${low}  off

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
