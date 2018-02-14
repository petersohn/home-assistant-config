*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Test Setup     Initialize
Test Teardown  Cleanup Environment


*** Variables ***

${test_sensor} =        sensor.test_sensor
${test_sensor_value} =  sensor state


*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Unblock For Some Time
    ${unblock_time} =  Set Variable  ${120}
    ${finish_time} =  Add Time To Date  ${start_time}  ${unblock_time}
    ${real_finish_time} =  Add Time To Date  ${finish_time}  ${appdaemon_interval}
    Call Function  unblock_for  ${unblock_time}
    Wait Until Keyword Succeeds  5s  0.01s
    ...    Current Time Should Be  ${real_finish_time}

Unblock Until Some Time
    ${unblock_time} =  Set Variable  ${150}
    ${finish_time} =  Add Time To Date
    ...    ${start_time}  ${unblock_time}  result_format=epoch
    ${real_finish_time} =  Add Time To Date
    ...    ${finish_time}  ${appdaemon_interval}
    Call Function  unblock_until  ${finish_time}
    Wait Until Keyword Succeeds  5s  0.01s
    ...    Current Time Should Be  ${real_finish_time}

Set State
    Call Function  set_state  ${test_sensor}  state=${test_sensor_value}
    ${value} =  Call Function  get_state  ${test_sensor}
    Should Be Equal  ${value}  ${test_sensor_value}


*** Keywords ***

Initialize
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize Environment  ${apps}  ${app_configs}

Current Time Should Be
    [Arguments]  ${time}
    ${time_value} =  Convert Date  ${time}
    ${current_time} =  Call Function  get_current_time
    ${current_time_value} =  Convert Date  ${current_time}
    Should Be Equal  ${current_time_value}  ${time_value}
