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
    [Setup]  Initialize  AlertAggregator
    ...    ${sensor1}=off
    ...    ${sensor2}=off
    ...    ${sensor3}=off

    State Should Be  ${alert_sensor}  off
    Schedule Call At  1 min
    ...    set_sensor_state  ${sensor1}  on
    Schedule Call At  2 min
    ...    set_sensor_state  ${sensor3}  on
    Schedule Call At  3 min
    ...    set_sensor_state  ${sensor2}  on
    Schedule Call At  4 min
    ...    set_sensor_state  ${sensor3}  off
    Schedule Call At  5 min
    ...    set_sensor_state  ${sensor1}  off
    Schedule Call At  6 min
    ...    set_sensor_state  ${sensor2}  off

    State Should Change At  ${alert_sensor}  on  1 min
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad

    State Should Cycle At  ${alert_sensor}  2 min
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error3 is bad

    State Should Cycle At  ${alert_sensor}  3 min
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error2 is bad
    ...    binary_sensor.error3 is bad

    State Should Not Change Until  ${alert_sensor}  4 min
    Wait For Alarm Text
    ...        binary_sensor.error1 is bad
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    State Should Not Change Until  ${alert_sensor}  5 min
    Wait For Alarm Text
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    State Should Change At  ${alert_sensor}  off  6 min

Alert On At The Beginning
    [Setup]  Initialize  AlertAggregator
    ...    ${sensor1}=off
    ...    ${sensor2}=on
    ...    ${sensor3}=on

    State Should Be  ${alert_sensor}  on
    Wait For Alarm Text
    ...    binary_sensor.error2 is bad
    ...    binary_sensor.error3 is bad

    Schedule Call At  1 min
    ...    set_sensor_state  ${sensor2}  off
    Schedule Call At  2 min
    ...    set_sensor_state  ${sensor3}  off

    State Should Not Change Until  ${alert_sensor}  1 min
    Wait For Alarm Text
    ...    binary_sensor.error3 is bad
    State Should Be  ${alert_sensor}  on

    State Should Change At  ${alert_sensor}  off  2 min

Timeout
    [Setup]  Initialize  AlertAggregatorTimeout
    ...    ${sensor1}=off
    ...    ${sensor2}=off
    ...    ${sensor3}=off

    State Should Be  ${alert_sensor}  off
    Schedule Call At  20 sec
    ...    set_sensor_state  ${sensor1}  on
    Schedule Call At  2 min
    ...    set_sensor_state  ${sensor1}  off

    Schedule Call At  2 min 30 sec
    ...    set_sensor_state  ${sensor1}  on
    Schedule Call At  3 min
    ...    set_sensor_state  ${sensor2}  on
    Schedule Call At  5 min
    ...    set_sensor_state  ${sensor1}  off
    Schedule Call At  5 min 20 sec
    ...    set_sensor_state  ${sensor2}  off

    Schedule Call At  6 min
    ...    set_sensor_state  ${sensor3}  on
    Schedule Call At  8 min
    ...    set_sensor_state  ${sensor1}  on
    Schedule Call At  8 min 30 sec
    ...    set_sensor_state  ${sensor1}  off
    Schedule Call At  9 min 30 sec
    ...    set_sensor_state  ${sensor1}  on
    Schedule Call At  11 min
    ...    set_sensor_state  ${sensor3}  off
    Schedule Call At  11 min 30 sec
    ...    set_sensor_state  ${sensor2}  on
    Schedule Call At  12 min
    ...    set_sensor_state  ${sensor1}  off
    Schedule Call At  13 min
    ...    set_sensor_state  ${sensor2}  off

    State Should Change At  ${alert_sensor}  on  1 min 20 sec
    Wait For Alarm Text
    ...    binary_sensor.error1 is bad
    State Should Change At  ${alert_sensor}  off  2 min

    State Should Change At  ${alert_sensor}  on  3 min 30 sec
    Wait For Alarm Text
    ...    binary_sensor.error1 is bad
    State Should Cycle At  ${alert_sensor}  4 min
    Wait For Alarm Text
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error2 is bad
    State Should Not Change Until  ${alert_sensor}  5 min
    Wait For Alarm Text
    ...    binary_sensor.error2 is bad
    State Should Change At  ${alert_sensor}  off   5 min 20 sec

    State Should Change At  ${alert_sensor}  on  7 min
    Wait For Alarm Text
    ...        binary_sensor.error3 is bad
    State Should Cycle At  ${alert_sensor}  10 min 30 sec
    Wait For Alarm Text
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error3 is bad
    State Should Not Change Until  ${alert_sensor}  11 min
    Wait For Alarm Text
    ...    binary_sensor.error1 is bad
    State Should Change At  ${alert_sensor}  off   12 min
    State Should Change At  ${alert_sensor}  on  12 min 30 sec
    Wait For Alarm Text
    ...        binary_sensor.error2 is bad
    State Should Change At  ${alert_sensor}  off   13 min


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

Wait For Alarm Text
    [Arguments]  @{lines}
    Wait Until Keyword Succeeds  10s  0.01s
    ...    Alarm Text Should Be  @{lines}

State Should Cycle At
    [Arguments]  ${entity}  ${time}
    ${deadline} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Be  ${entity}  on
    State Should Not Change Until  ${entity}  ${deadline}
    Unblock For  ${appdaemon_interval}
    ${date} =  Get Date
    Wait For History
    ...    ${date}  ${0}
    ...    ${date}  ${1}
    State Should Be  ${entity}  on

Initialize
    [Arguments]  @{configs}  &{states}
    Clean States
    Initialize States
    ...    ${alert_sensor}=off
    ...    &{states}
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  history  alert
    ${app_configs} =  Create List  TestApp  @{configs}
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
