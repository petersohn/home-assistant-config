*** Settings ***

Library        libraries/TypeUtil.py
Library        Collections
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${name} =    test_history_manager
${entity} =  sensor.test_sensor
${sum_entity} =  sensor.test_sensor_sum
${sum_entity_r} =  sensor.test_sensor_sum_refresh_interval
${mean_entity} =  sensor.test_sensor_mean
${enabler} =  test_history_enabler


*** Test Cases ***

Get History
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  2
    Unblock For  1 min
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  0
    History Should Be  3  2  3  0
    Limited History Should Be  65 s  3  0

Refresh Interval
    Set Test Variable  ${name}  test_history_manager_refresh_interval
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  6
    Unblock For  1 min
    Set State  ${entity}  2
    Unblock For  3 min
    Set State  ${entity}  3
    Unblock For  2 min
    Set State  ${entity}  0
    Unblock For  2 min
    Set State  ${entity}  10
    History Should Be  3  6  2  2  2  3  3  0  0  10


No Events for a Long Time
    Set Test Variable  ${name}  test_history_manager_refresh_interval
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  6
    Unblock For  1 hour 1 min
    ${expected_result} =  Repeat Item  6  ${60}
    History Should Be  @{expected_result}


Events After a Long Time
    Set Test Variable  ${name}  test_history_manager_refresh_interval
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  6
    Unblock For  1 hour 1 min
    Set State  ${entity}  8
    Unblock For  30 sec
    ${expected_result} =  Repeat Item  6  ${59}
    Append To List  ${expected_result}  8
    History Should Be  @{expected_result}

Old History Elements Are Removed
    Set State  ${entity}  20
    Unblock For  20 min
    Set State  ${entity}  13
    Unblock For  20 min
    Set State  ${entity}  1
    Unblock For  20 min
    Set State  ${entity}  6
    Unblock For  21 min
    Set State  ${entity}  54
    History Should Be  1  6  54

History Enabler
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  1 min
    Set State  ${entity}  4
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  1 min
    Set State  ${entity}  3
    Enabled State Should Be  ${enabler}  ${True}
    Unblock For  1 min
    Set State  ${entity}  4
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  3 min 30 s
    Set State  ${entity}  1
    Enabled State Should Be  ${enabler}  ${True}
    Unblock For  4 min
    Enabled State Should Be  ${enabler}  ${False}

Aggregated Value
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${0}
    Set State  ${entity}  3
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${3}
    Set State  ${entity}  5
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${8}
    Set State  ${entity}  2
    Set State  ${entity}  2
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${7}
    Set State  ${entity}  5
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${7}
    Set State  ${entity}  1
    Unblock For  1 min
    State Should Be As  ${sum_entity}  Int  ${6}

Aggregated Value With Refresh Interval
    Unblock For  20 sec
    Set State  ${entity}  3
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${3}
    Set State  ${entity}  5
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${8}
    Set State  ${entity}  2
    Set State  ${entity}  2
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${10}
    Set State  ${entity}  5
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${12}
    Set State  ${entity}  10
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${17}
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${25}
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${30}
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${30}
    Set State  ${entity}  1
    Unblock For  1 min
    State Should Be As  ${sum_entity_r}  Int  ${21}

Custom Aggregator
    Unblock For  1 min
    Set State  ${entity}  0
    Unblock For  1 min
    Set State  ${entity}  20
    Unblock For  1 min
    Set State  ${entity}  10
    Unblock For  1 min
    State Should Be As  ${mean_entity}  Int  ${15}


*** Keywords ***

Get Values
    [Arguments]  ${interval}=${None}
    [Return]  ${result}

Should Be Loaded
    ${result} =  Call Function  call_on_app  ${name}  is_loaded
    Should Be True  ${result}

History Should Be
    [Arguments]  @{expected_values}  &{kwargs}
    ${values} =  Call Function  call_on_app  ${name}  get_values  &{kwargs}
    Lists Should Be Equal  ${values}  ${expected_values}

Limited History Should Be
    [Arguments]  ${interval}  @{expected_values}
    ${arg_types} =  Create List  ${None}  ${None}  convert_timedelta
    ${values} =  Call Function  call_on_app  ${name}
    ...   get_values  ${interval}  arg_types=${arg_types}
    Lists Should Be Equal  ${values}  ${expected_values}

Initialize
    Initialize States
    ...    ${entity}=${0}
    Clean States And History
    Initialize States
    ...    ${entity}=${0}
    ${apps} =  Create List  TestApp  history  enabler  aggregator
    ${app_configs} =  Create List  TestApp  HistoryManager
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
    Wait Until Keyword Succeeds  30 sec  1 sec  Should Be Loaded
