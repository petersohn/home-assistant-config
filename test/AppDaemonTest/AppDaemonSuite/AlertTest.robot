*** Settings ***

Resource       resources/Config.robot
Test Teardown  Cleanup AppDaemon
Library        DateTime
Library        libraries/DateTimeUtil.py
Library        libraries/HistoryUtil.py


*** Variables ***

${alert_sensor} =   binary_sensor.alert_sensor
${sensor1} =        binary_sensor.error1
${sensor2} =        binary_sensor.error2
${sensor3} =        binary_sensor.error3


*** Test Cases ***

Turn Alert On And Off
    [Setup]  Initialize
    ...    ${sensor1}=off
    ...    ${sensor2}=off
    ...    ${sensor3}=off

    State Should Be  ${alert_sensor}  off

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor1}  on
    Wait For History
    ...    ${date}  ${1}
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor3}  on
    Wait For History
    ...    ${date}  ${0}
    ...    ${date}  ${1}
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error3 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor2}  on
    Wait For History
    ...    ${date}  ${0}
    ...    ${date}  ${1}
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error2 is bad
    ...    binary_sensor.error3 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor3}  off
    Wait Until Keyword Succeeds  10s  0.01s
    ...    Alarm Text Should Be
    ...        binary_sensor.error1 is bad
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor1}  off
    Wait Until Keyword Succeeds  10s  0.01s
    ...    Alarm Text Should Be
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor2}  off
    State Should Change Now  ${alert_sensor}  off

Alert On At The Beginning
    [Setup]  Initialize
    ...    ${sensor1}=off
    ...    ${sensor2}=on
    ...    ${sensor3}=on

    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor2}  off
    Wait Until Keyword Succeeds  10s  0.01s
    ...    Alarm Text Should Be
    ...        binary_sensor.error3 is bad
    State Should Be  ${alert_sensor}  on

    Unblock For  1 min
    ${date} =  Get Date
    Set State  ${sensor3}  off
    State Should Change Now  ${alert_sensor}  off


*** Keywords ***

Has History
    [Arguments]  ${converted_expected_values}
    ${values} =  Call Function  call_on_app  alert_history  get_history
    ${converted_values} =  Convert History Output  ${values}
    ${is_found} =  Is Expected History Found
    ...    ${converted_expected_values}  ${converted_values}
    Should Be True  ${is_found}

Wait For History
    [Arguments]  @{expected_values}
    ${converted_expected_values} =  Convert History Input  ${expected_values}
    Wait Until Keyword Succeeds  10s  0.01s
    ...    Has History  ${converted_expected_values}

Alarm Text Should Be
    [Arguments]  @{lines}
    ${expected_text} =  Catenate  SEPARATOR=\n  @{lines}
    Attribute Should Be  ${alert_sensor}  text  ${expected_text}

Initialize
    [Arguments]  &{states}
    Clean States
    Initialize States
    ...    ${alert_sensor}=off
    ...    &{states}
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  history  alert
    ${app_configs} =  Create List  TestApp  AlertAggregator
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
