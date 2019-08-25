*** Settings ***

Library        libraries/TypeUtil.py
Library        libraries/HistoryUtil.py
Library        Collections
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${name} =    test_history_manager
${entity} =  sensor.test_sensor
${sum_entity} =  sensor.test_sensor_sum
${sum_entity_b} =  sensor.test_sensor_sum_base_interval
${mean_entity} =  sensor.test_sensor_mean
${enabler} =  input_boolean.test_switch


*** Test Cases ***

Get History
    Set State  ${entity}  3
    ${date1} =  Get Date
    Unblock For  1 min
    Set State  ${entity}  2
    ${date2} =  Get Date
    Unblock For  1 min
    Set State  ${entity}  3
    ${date3} =  Get Date
    Unblock For  1 min
    Set State  ${entity}  0
    ${date4} =  Get Date
    History Should Be  ${date1}  ${3}
    ...                ${date2}  ${2}
    ...                ${date3}  ${3}
    ...                ${date4}  ${0}
    ${first_date} =  Subtract Time From Date  ${date4}  65 s
    Limited History Should Be  65 s  ${first_date}  ${2}
    ...                              ${date3}  ${3}
    ...                              ${date4}  ${0}

Old History Elements Are Removed
    Set State  ${entity}  20
    ${date1} =  Get Date
    Unblock For  20 min
    Set State  ${entity}  13
    Unblock For  20 min
    Set State  ${entity}  1
    ${date2} =  Get Date
    Unblock For  20 min
    Set State  ${entity}  6
    ${date3} =  Get Date
    Unblock For  21 min
    Set State  ${entity}  54
    ${date4} =  Get Date
    ${first_date} =  Subtract Time From Date  ${date4}  1 h
    History Should Be  ${first_date}  ${13}
    ...                ${date2}  ${1}
    ...                ${date3}  ${6}
    ...                ${date4}  ${54}

Nothing Happens For A Long Time
    Set State  ${entity}  42
    Unblock For  2 min
    ${now} =  Get Date
    ${date} =  Subtract Time From Date  ${now}  1 min
    Limited History Should Be  1 min  ${date}  ${42}

History Enabler
    Set State  ${entity}  3
    Schedule Call At  20 min  set_sensor_state  ${entity}  5
    Schedule Call At  40 min  set_sensor_state  ${entity}  1
    State Should Change At  ${enabler}  on    4 min 10 s
    State Should Change At  ${enabler}  off  23 min 10 s
    State Should Change At  ${enabler}  on   42 min 10 s
    State Should Change At  ${enabler}  off  44 min 10 s

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

# Aggregated Value With Base Interval
#     Unblock For  20 sec
#     Set State  ${entity}  3
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${3}
#     Set State  ${entity}  5
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${8}
#     Set State  ${entity}  2
#     Set State  ${entity}  2
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${10}
#     Set State  ${entity}  5
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${12}
#     Set State  ${entity}  10
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${17}
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${25}
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${30}
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${30}
#     Set State  ${entity}  1
#     Unblock For  1 min
#     State Should Be As  ${sum_entity_b}  Int  ${21}
#

Mean Value
    Set State  ${entity}  0
    Unblock For  1 min
    Set State  ${entity}  20
    Unblock For  1 min
    Set State  ${entity}  10
    Unblock For  1 min
    State Should Be As  ${mean_entity}  Int  ${15}

Mean Value Irregular Intervals
    Set State  ${entity}  20
    Unblock For  1 min
    Set State  ${entity}  16
    Unblock For  30 s
    Set State  ${entity}  8
    Unblock For  30 s
    Set State  ${entity}  0
    Unblock For  2 min
    State Should Be As  ${mean_entity}  Int  ${8}


*** Keywords ***

Get Values
    [Arguments]  ${interval}=${None}
    [Return]  ${result}

Should Be Loaded
    ${result} =  Call Function  call_on_app  ${name}  is_loaded
    Should Be True  ${result}

History Should Be
    [Arguments]  @{expected_values}
    ${converted_expected_values} =  Convert History Input  ${expected_values}
    ${values} =  Call Function  call_on_app  ${name}  get_history
    ${converted_values} =  Convert History Output  ${values}
    Lists Should Be Equal  ${converted_values}  ${converted_expected_values}

Limited History Should Be
    [Arguments]  ${interval}  @{expected_values}
    ${converted_expected_values} =  Convert History Input  ${expected_values}
    ${arg_types} =  Create List  ${None}  ${None}  convert_timedelta
    ${values} =  Call Function  call_on_app  ${name}  get_history  ${interval}
    ...          arg_types=${arg_types}
    ${converted_values} =  Convert History Output  ${values}
    Lists Should Be Equal  ${converted_values}  ${converted_expected_values}

Initialize
    Initialize States
    ...    ${entity}=${0}
    ...    ${enabler}=off
    Clean States And History
    Initialize States
    ...    ${entity}=${0}
    ${apps} =  Create List  TestApp  history  enabler  aggregator  auto_switch
    ...                     enabled_switch
    ${app_configs} =  Create List  TestApp  HistoryManager
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
    Wait Until Keyword Succeeds  30 sec  1 sec  Should Be Loaded
