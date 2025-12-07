*** Settings ***

Resource       resources/TestHarness.robot
Test Setup     Create Test Harness
Test Teardown  Cleanup Test Harness
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
    Set State  ${sensor1}  off
    Set State  ${sensor2}  off
    Set State  ${sensor3}  off
    Create Alert Aggregator

    State Should Be  ${alert_sensor}  off
    Schedule Call At  1 min  set_state  ${sensor1}  on
    Schedule Call At  2 min  set_state  ${sensor3}  on
    Schedule Call At  3 min  set_state  ${sensor2}  on
    Schedule Call At  4 min  set_state  ${sensor3}  off
    Schedule Call At  5 min  set_state  ${sensor1}  off
    Schedule Call At  6 min  set_state  ${sensor2}  off

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
    Alarm Text Should Be
    ...        binary_sensor.error1 is bad
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    State Should Not Change Until  ${alert_sensor}  5 min
    Alarm Text Should Be
    ...        binary_sensor.error2 is bad
    State Should Be  ${alert_sensor}  on

    State Should Change At  ${alert_sensor}  off  6 min

Alert On At The Beginning
    Set State  ${sensor1}  off
    Set State  ${sensor2}  on
    Set State  ${sensor3}  on
    Create Alert Aggregator

    State Should Be  ${alert_sensor}  on
    Alarm Text Should Be
    ...    binary_sensor.error2 is bad
    ...    binary_sensor.error3 is bad

    Schedule Call At  1 min  set_state  ${sensor2}  off
    Schedule Call At  2 min  set_state  ${sensor3}  off

    State Should Not Change Until  ${alert_sensor}  1 min
    Alarm Text Should Be
    ...    binary_sensor.error3 is bad
    State Should Be  ${alert_sensor}  on

    State Should Change At  ${alert_sensor}  off  2 min

Timeout
    Set State  ${sensor1}  off
    Set State  ${sensor2}  off
    Set State  ${sensor3}  off
    &{timeout} =  Create Dictionary  minutes=${1}
    Create Alert Aggregator  timeout=${timeout}

    State Should Be  ${alert_sensor}  off
    Schedule Call At  20 sec  set_state  ${sensor1}  on
    Schedule Call At  2 min  set_state  ${sensor1}  off

    Schedule Call At  2 min 30 sec  set_state  ${sensor1}  on
    Schedule Call At  3 min  set_state  ${sensor2}  on
    Schedule Call At  5 min  set_state  ${sensor1}  off
    Schedule Call At  5 min 20 sec  set_state  ${sensor2}  off

    Schedule Call At  6 min  set_state  ${sensor3}  on
    Schedule Call At  8 min  set_state  ${sensor1}  on
    Schedule Call At  8 min 30 sec  set_state  ${sensor1}  off
    Schedule Call At  9 min 30 sec  set_state  ${sensor1}  on
    Schedule Call At  11 min  set_state  ${sensor3}  off
    Schedule Call At  11 min 30 sec  set_state  ${sensor2}  on
    Schedule Call At  12 min  set_state  ${sensor1}  off
    Schedule Call At  13 min  set_state  ${sensor2}  off

    State Should Change At  ${alert_sensor}  on  1 min 20 sec
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    State Should Change At  ${alert_sensor}  off  2 min

    State Should Change At  ${alert_sensor}  on  3 min 30 sec
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    State Should Cycle At  ${alert_sensor}  4 min
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error2 is bad
    State Should Not Change Until  ${alert_sensor}  5 min
    Alarm Text Should Be
    ...    binary_sensor.error2 is bad
    State Should Change At  ${alert_sensor}  off   5 min 20 sec

    State Should Change At  ${alert_sensor}  on  7 min
    Alarm Text Should Be
    ...        binary_sensor.error3 is bad
    State Should Cycle At  ${alert_sensor}  10 min 30 sec
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    ...    binary_sensor.error3 is bad
    State Should Not Change Until  ${alert_sensor}  11 min
    Alarm Text Should Be
    ...    binary_sensor.error1 is bad
    State Should Change At  ${alert_sensor}  off   12 min
    State Should Change At  ${alert_sensor}  on  12 min 30 sec
    Alarm Text Should Be
    ...        binary_sensor.error2 is bad
    State Should Change At  ${alert_sensor}  off   13 min


*** Keywords ***

Create Alert Aggregator
    [Arguments]  &{extra_args}
    @{sources} =  Create List  ${sensor1}  ${sensor2}  ${sensor3}
    ${alert} =  Create App  alert  AlertAggregator  alert
    ...    sources=${sources}
    ...    target=${alert_sensor}
    ...    trigger_expr=v[name]
    ...    text_expr=name + ' is bad'
    ...    &{extra_args}
    ${alert_history} =  Create App  history  HistoryManager  alert_history
    ...    entity=${alert_sensor}

    Set Test Variable  ${alert}
    Set Test Variable  ${alert_history}

Should Have History
    [Arguments]  @{expected_values}
    ${converted_expected_values} =  Convert History Input  ${expected_values}
    ${values} =  Call On App  ${alert_history}  get_history
    ${converted_values} =  Convert History Output  ${values}
    ${is_found} =  Is Expected History Found
    ...    ${converted_expected_values}  ${converted_values}
    Should Be True  ${is_found}

Alarm Text Should Be
    [Arguments]  @{lines}
    ${expected_text} =  Catenate  SEPARATOR=\n  @{lines}
    State Should Be  ${alert_sensor}  ${expected_text}  attribute=text

State Should Cycle At
    [Arguments]  ${entity}  ${time}
    ${deadline} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Be  ${entity}  on
    State Should Not Change Until  ${entity}  ${deadline}
    Step
    ${date} =  Get Current Time
    Should Have History
    ...    ${date}  ${0}
    ...    ${date}  ${1}
    State Should Be  ${entity}  on
