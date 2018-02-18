*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Test Setup     Initialize
Test Teardown  Cleanup Environment


*** Variables ***

${test_sensor} =        sensor.test_sensor
${test_sensor_value} =  sensor state
${new_sensor_value} =   new sensor state


*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Unblock For Some Time
    ${unblock_time} =  Set Variable  2:00
    ${finish_time} =  Add Time To Date  ${start_time}  ${unblock_time}

    Unblock For  ${unblock_time}
    Current Time Should Be  ${finish_time}

Unblock Until Some Time
    ${unblock_time} =  Set Variable  2:30
    ${finish_time} =  Add Time To Date  ${start_time}  ${unblock_time}

    Unblock Until  ${finish_time}
    Current Time Should Be  ${finish_time}

Set State
    Set State  ${test_sensor}  ${test_sensor_value}
    State Should Be  ${test_sensor}  ${test_sensor_value}

Schedule State Change In Some Time
    ${delay} =  Set Variable  2min
    ${unblock_time} =  Subtract Time From Time
    ...    ${delay}  ${2 * ${appdaemon_interval}}

    Set State  ${test_sensor}  ${test_sensor_value}
    Schedule Call In  ${delay}
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock For  ${unblock_time}
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  ${3 * ${appdaemon_interval}}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Some Time
    ${delay} =  Set Variable  3min
    ${finish_time} =  Add Time To Date  ${start_time}  ${delay}
    ${unblock_time} =  Subtract Time From Time
    ...    ${delay}  ${2 * ${appdaemon_interval}}

    Set State  ${test_sensor}  ${test_sensor_value}
    Schedule Call At  ${finish_time}
    ...    set_state  ${test_sensor}  state=${new_sensor_value}
    Unblock For  ${unblock_time}
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  ${3 * ${appdaemon_interval}}
    State Should Be  ${test_sensor}  ${new_sensor_value}


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


