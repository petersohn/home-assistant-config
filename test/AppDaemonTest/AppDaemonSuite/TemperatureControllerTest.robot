*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${furnace_sensor} =       sensor.furnace
${outside_sensor} =       sensor.outside
${availability_sensor} =  binary_sensor.available
${switch} =               input_boolean.temperature_controller_pump
${minimum_temperature} =  ${30.0}
${low_mode_start} =       5 min
${low_mode_time} =        2 min
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

Low Mode
    Set State  ${outside_sensor}  ${high_outside_temperature}
    ${high_furnace_temperature} =  Evaluate  ${minimum_temperature} + 1.0
    ${low_furnace_temperature} =  Evaluate  ${minimum_temperature} - 1.0
    ${end_time} =  Set Variable  16 min

    Set State  ${furnace_sensor}  ${high_furnace_temperature}
    Schedule Call In  ${end_time}
    ...    set_sensor_state  ${furnace_sensor}  ${low_furnace_temperature}

    Repeat Keyword  2  Low Mode Should Cycle
    State Should Not Change  ${switch}  timeout=10 min

Low Mode Starts After Temperature Stops Rising
    Set State  ${furnace_sensor}  31
    Schedule Call In  2 min
    ...    set_sensor_state  ${furnace_sensor}  32
    Schedule Call In  4 min
    ...    set_sensor_state  ${furnace_sensor}  33
    Schedule Call In  6 min
    ...    set_sensor_state  ${furnace_sensor}  34

    State Should Be  ${switch}  off
    State Should Not Change  ${switch}  timeout=6 min
    Low Mode Should Cycle

Low Mode Starts After Normal Operation
    ${stop_time} =  Set Variable  6 min
    Set State  ${furnace_sensor}  70
    Schedule Call In  ${stop_time}
    ...    set_sensor_state  ${furnace_sensor}  40

    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  ${stop_time}
    Low Mode Should Cycle


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

Low Mode Should Cycle
    State Should Be  ${switch}  off
    State Should Change In  ${switch}  on  ${low_mode_start}
    State Should Change In  ${switch}  off  ${low_mode_time}

Switch Should Be After
    [Arguments]  ${delay}  ${state}
    Unblock For  ${delay}
    State Should Be  ${switch}  ${state}

Initialize
    Clean States
    Initialize States
    ...    ${furnace_sensor}=${10}
    ...    ${outside_sensor}=${10}
    ...    ${availability_sensor}=on
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  temperature_controller
    ${app_configs} =  Create List  TestApp  TemperatureController
    Initialize AppDaemon  ${apps}  ${app_configs}
