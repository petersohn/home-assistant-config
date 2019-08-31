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
${integral_entity} =  sensor.test_sensor_integral
${integral_entity_b} =  sensor.test_sensor_integral_base_interval
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
    Schedule Call At   2 min       set_sensor_state  ${entity}  3
    Schedule Call At  20 min 30 s  set_sensor_state  ${entity}  5
    Schedule Call At  40 min       set_sensor_state  ${entity}  1
    State Should Change At  ${enabler}  on    6 min
    State Should Change At  ${enabler}  off  23 min 30 s
    State Should Change At  ${enabler}  on   42 min
    State Should Change At  ${enabler}  off  44 min

Aggregated Value
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${0}
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${0}
    Set State  ${entity}  4
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${4}   # 1*4
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${8}   # 2*4
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${12}  # 3*4
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${12}  # 3*4
    Set State  ${entity}  10
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${18}  # 2*4 + 1*10
    Unblock For  30 sec
    State Should Be As  ${integral_entity}  Int  ${18}  # 2*4 + 1*10
    Set State  ${entity}  3
    State Should Be As  ${integral_entity}  Int  ${21}  # 1.5*4 + 1.5*10
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${20}  # 0.5*4 + 1.5*10 + 1*3
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${16}  # 1*10 + 2*3
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${9}   # 3*3
    Unblock For  1 min
    State Should Be As  ${integral_entity}  Int  ${9}   # 3*3

Aggregated Value With Base Interval
    Unblock For  20 sec
    Set State  ${entity}  3
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${3}   # 1*3
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${6}   # 2*3
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${9}   # 3*3
    Unblock For  30 sec
    State Should Be As  ${integral_entity_b}  Int  ${18}  # 6*3
    Unblock For  1 min
    State Should Be As  ${integral_entity_b}  Int  ${36}  # 12*3
    Unblock For  1 min
    State Should Be As  ${integral_entity_b}  Int  ${54}  # 18*3
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${54}  # 18*3
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${54}  # 18*3
    Set State  ${entity}  5
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${56}  # 17*3 + 1*5
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${58}  # 16*3 + 2*5
    Unblock For  10 sec
    State Should Be As  ${integral_entity_b}  Int  ${60}  # 15*3 + 3*5
    Unblock For  30 sec
    State Should Be As  ${integral_entity_b}  Int  ${66}  # 12*3 + 6*5
    Unblock For  1 min
    State Should Be As  ${integral_entity_b}  Int  ${78}  # 6*3 + 12*5
    Unblock For  50 s
    State Should Be As  ${integral_entity_b}  Int  ${88}  # 1*3 + 17*5
    Unblock For  10 s
    State Should Be As  ${integral_entity_b}  Int  ${90}  # 18*5

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
    Set State  ${entity}  6
    Unblock For  30 s
    Set State  ${entity}  2
    Unblock For  1 min 30 s
    Set State  ${entity}  0
    # (0.5*20 + 0.5*16 + 0.5*6 + 1.5*2) / 3
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
