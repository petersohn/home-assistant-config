*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${test_sensor} =        sensor.test_sensor
${test_sensor_value} =  sensor state
${intermediate_sensor_value} =   intermediate sensor state
${new_sensor_value} =   new sensor state
${test_switch} =             input_boolean.test_switch


*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Initial State
    State Should Be  ${test_sensor}  ${test_sensor_value}

Unblock For Some Time
    ${unblock_time} =  Set Variable  2:00
    ${finish_time} =  Add Time To Date  ${start_time}  ${unblock_time}

    Unblock For  ${unblock_time}
    Current Time Should Be  ${finish_time}

Unblock Until Some Time
    ${unblock_time} =  Set Variable  12:05:00
    ${finish_time} =  Find Time  ${start_time}  ${unblock_time}

    Unblock Until  ${unblock_time}
    Current Time Should Be  ${finish_time}

Set State
    Set State  ${test_sensor}  ${new_sensor_value}
    Wait Until State Becomes  ${test_sensor}  ${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Turn On And Off
    Turn On  ${test_switch}
    State Should Be  ${test_switch}  on
    Turn Off  ${test_switch}
    State Should Be  ${test_switch}  off
    Turn On  ${test_switch}
    State Should Be  ${test_switch}  on

Schedule State Change In Some Time
    Schedule Call In  2:00
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock For  1:59
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  2s
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Some Time
    Schedule Call At  12:10:00
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock Until  12:09:59
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock Until  12:10:01
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change
    Schedule Call At  12:00:05
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock Until State Change  ${test_sensor}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change With New State
    Schedule Call At  12:00:05
    ...    set_state  ${test_sensor}  state=${intermediate_sensor_value}
    Schedule Call At  12:00:10
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  new=${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change With Old State
    Schedule Call At  12:00:05
    ...    set_state  ${test_sensor}  state=${intermediate_sensor_value}
    Schedule Call At  12:00:10
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  old=${intermediate_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Clean Home Assistant States
    Turn On  ${test_switch}
    Clean States
    Run Keyword And Expect Error  *Internal Server Error*
    ...    Get State  ${test_sensor}
    State Should Be  ${test_switch}  off


*** Keywords ***

Initialize
    Clean States
    Initialize States  ${test_sensor}=${test_sensor_value}
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize AppDaemon  ${apps}  ${app_configs}

Current Time Should Be
    [Arguments]  ${time}
    ${time_value} =  Convert Date  ${time}
    ${current_time} =  Call Function  get_current_time
    ${current_time_value} =  Convert Date  ${current_time}
    Should Be Equal  ${current_time_value}  ${time_value}
