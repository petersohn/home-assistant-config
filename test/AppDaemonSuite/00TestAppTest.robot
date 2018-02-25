*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${test_sensor} =                 sensor.test_sensor
${test_sensor2} =                sensor.test_sensor2
${test_sensor_value} =           sensor state
${intermediate_sensor_value} =   intermediate sensor state
${new_sensor_value} =            new sensor state
${test_switch} =                 input_boolean.test_switch
${start_time} =                  01:00:00
${alternate_start_time} =        10:11:12


*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Different Start Time
    [Setup]  Initialize  ${alternate_start_time}
    Current Time Should Be  ${alternate_start_time}

Initial State
    State Should Be  ${test_sensor}  ${test_sensor_value}

Unblock For Some Time
    Unblock For  2 min
    Current Time Should Be  01:02:00

Unblock Until Some Time
    ${unblock_time} =  Set Variable  01:05:00
    Unblock Until  ${unblock_time}
    Current Time Should Be  ${unblock_time}

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
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock For  1:59
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  2s
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Some Time
    Schedule Call At  01:10:00
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until  01:09:59
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock Until  01:10:01
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change
    Schedule Call At  01:00:05
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until Later State Change
    Schedule Call At  01:00:05
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Schedule Call At  01:00:10
    ...    set_sensor_state  ${test_sensor2}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor2}
    State Should Be  ${test_sensor2}  ${new_sensor_value}

Unblock Until State Change With Timeout
    Schedule Call In  00:00:05
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  timeout=10 sec
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:05

Unblock Until State Change With Deadline
    Schedule Call At  01:00:05
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  deadline=01:00:10
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:05

State Should Not Change With Timeout
    Schedule Call In  00:00:15
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change  ${test_sensor}  timeout=10 sec
    Current Time Should Be  01:00:10

State Should Not Change With Deadline
    Schedule Call In  00:00:15
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change  ${test_sensor}  deadline=01:00:10
    Current Time Should Be  01:00:10

State Should Change In Some Time
    ${time} =  Set Variable  10 sec
    Schedule Call In  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change In  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:10

State Should Change At Some Time
    ${time} =  Set Variable  01:00:12
    Schedule Call At  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${time}

Unblock Until State Change With New State
    Schedule Call At  01:00:05
    ...    set_sensor_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:10
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  new=${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change With Old State
    Schedule Call At  01:00:05
    ...    set_sensor_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:10
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
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
    [Arguments]  ${start_time}=${start_time}
    Clean States
    Initialize States
    ...    ${test_sensor}=${test_sensor_value}
    ...    ${test_sensor2}=${test_sensor_value}
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}

Current Time Should Be
    [Arguments]  ${time}
    ${date} =  Add Time To Date  ${start_date}  ${time}
    ${time_value} =  Convert Date  ${date}
    ${current_time} =  Call Function  get_current_time
    ${current_time_value} =  Convert Date  ${current_time}
    Should Be Equal  ${current_time_value}  ${time_value}