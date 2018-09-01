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
${alternate_start_time} =        10:11:20


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

Unblock Until Exact Time
    ${unblock_time} =  Set Variable  2018-01-01 01:05:00
    Unblock Until Date Time  ${unblock_time}
    Current Time Should Be  01:05:00

Unblock Until Sunrise
    [Setup]  Initialize  ${before_sunrise}
    Unblock Until Sunrise  -10 sec
    Sun Should Be Down
    Unblock For  10 sec
    Sun Should Be Up

Unblock Until Sunset
    [Setup]  Initialize  ${before_sunset}
    Unblock Until Sunset  -10 sec
    Sun Should Be Up
    Unblock For  10 sec
    Sun Should Be Down

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
    Turn On  ${test_switch}
    State Should Be  ${test_switch}  on

Turn On Or Off Test
    [Template]  Test Turn On Or Off
    on
    off

Schedule State Change In Some Time
    Schedule Call In  2:00
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock For  1:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  ${appdaemon_interval}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Some Time
    Schedule Call At  01:10:00
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until  01:09:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  ${appdaemon_interval}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Exact Time
    Schedule Call At Date Time  2018-01-01 01:10:00
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until  01:09:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  ${appdaemon_interval}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Sunrise
    [Setup]  Initialize  ${before_sunrise}
    Schedule Call At Sunrise  set_sensor_state
    ...    ${test_sensor}  ${new_sensor_value}  delay=10 sec
    Unblock Until Sunrise
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  10 sec
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Sunset
    [Setup]  Initialize  ${before_sunset}
    Schedule Call At Sunset  set_sensor_state
    ...    ${test_sensor}  ${new_sensor_value}  delay=-10 sec
    Unblock Until Sunset  -20 sec
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Unblock For  10 sec
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change
    ${change_time} =  Set Variable  01:00:10
    Schedule Call At  ${change_time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${change_time}

Unblock Until Later State Change
    ${change_time1} =  Set Variable  01:00:10
    ${change_time2} =  Set Variable  01:00:30
    Schedule Call At  ${change_time1}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Schedule Call At  ${change_time2}
    ...    set_sensor_state  ${test_sensor2}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor2}
    State Should Be  ${test_sensor2}  ${new_sensor_value}
    Current Time Should Be  ${change_time2}

Unblock Until State Change With Timeout
    Schedule Call In  20 sec
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  timeout=30 sec
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:20

Unblock Until State Change With Deadline
    Schedule Call At  01:00:20
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  deadline=01:00:30
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:20

Unblock Until State Change With New State
    Schedule Call At  01:00:20
    ...    set_sensor_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:40
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  new=${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Unblock Until State Change With Old State
    Schedule Call At  01:00:20
    ...    set_sensor_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:40
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    Unblock Until State Change  ${test_sensor}  old=${intermediate_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

State Should Not Change With Timeout
    Schedule Call In  30 sec
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change  ${test_sensor}  timeout=20 sec
    Current Time Should Be  01:00:20

State Should Not Change With Deadline
    Schedule Call In  30 sec
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change  ${test_sensor}  deadline=01:00:20
    Current Time Should Be  01:00:20

State Should Change In Some Time
    ${time} =  Set Variable  30 sec
    Schedule Call In  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change In  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:30

State Should Change At Some Time
    ${time} =  Set Variable  01:01:00
    Schedule Call At  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${time}

State Should Change In One Time Frame
    ${time} =  Set Variable  ${appdaemon_interval}
    Schedule Call In  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change In  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:10

State Should Change At Next Time Frame
    ${time} =  Set Variable  01:00:10
    Schedule Call At  ${time}
    ...    set_sensor_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${time}

Clean Home Assistant States
    Turn On  ${test_switch}
    Clean States
    Run Keyword And Expect Error  *Internal Server Error*
    ...    Get State  ${test_sensor}
    State Should Be  ${test_switch}  off

Type Conversions
    [Template]  Convert Types
    Foo      ${None}  Foo
    ${21}    ${None}  ${21}
    ${41}    int      ${41}
    ${26}    str      26
    ${True}  str      True
    ${0}     bool     ${False}
    ${1}     bool     ${True}
    123      int      ${123}
    41.5     float    ${41.5}
    41.0     Int      ${41}

Converted State Expectations
    Set State  ${test_sensor}  12
    State Should Be As  ${test_sensor}  int  ${12}

Call External App
    [Setup]  Initialize With External Test App
    ${input} =  Set Variable  Some Test
    ${result} =  Call Function  call_on_app
    ...    other_test_app  other_test  ${input}
    Should Be Equal  ${result}  ${input}


*** Keywords ***

Convert Types
    [Arguments]  ${argument}  ${type}  ${expected_result}
    ${result1} =  Call Function  test  ${argument}  result_type=${type}
    Should Be Equal  ${result1}  ${expected_result}

    ${arg_types} =  Create List  ${type}
    ${result2} =  Call Function  test  ${argument}  arg_types=${arg_types}
    Should Be Equal  ${result2}  ${expected_result}

    ${kwarg_types} =  Create Dictionary  arg=${type}
    ${result3} =  Call Function  test  arg=${argument}
    ...    kwarg_types=${kwarg_types}
    Should Be Equal  ${result3}  ${expected_result}

Initialize
    [Arguments]  ${start_time}=${start_time}
    Clean States
    Initialize States
    ...    ${test_sensor}=${test_sensor_value}
    ...    ${test_sensor2}=${test_sensor_value}
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}

Initialize With External Test App
    Clean States
    ${apps} =  Create List  TestApp  TestOtherApp
    ${app_configs} =  Create List  TestApp  TestOtherApp
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}

Current Time Should Be
    [Arguments]  ${time}
    ${date} =  Add Time To Date  ${start_date}  ${time}
    ${time_value} =  Convert Date  ${date}
    ${current_time} =  Call Function  get_current_time
    ${current_time_value} =  Convert Date  ${current_time}
    Should Be Equal  ${current_time_value}  ${time_value}

Test Turn On Or Off
    [Arguments]  ${state}
    Turn On Or Off  ${test_switch}  ${state}
    State Should Be  ${test_switch}  ${state}

Sun Should Be Up
    ${result} =  Call Function  sun_up
    Should Be True  ${result}

Sun Should Be Down
    ${result} =  Call Function  sun_up
    Should Be True  not ${result}
