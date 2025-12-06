*** Settings ***

Library        libraries/TypeUtil.py
Library        libraries/HistoryUtil.py
Library        Collections
Resource       resources/TestHarness.robot
Resource       resources/DateTime.robot
Resource       resources/History.robot
Test Setup     Create Test Harness
Test Teardown  Cleanup Test Harness


*** Variables ***

${entity} =  sensor.test_sensor
${aggregated_entity} =  sensor.test_sensor_aggregated
${sum_entity} =  sensor.test_sensor_sum
${min_entity} =  sensor.test_sensor_min
${max_entity} =  sensor.test_sensor_max
${enabler} =  input_boolean.test_switch2


*** Test Cases ***

Get History
    ${history_manager} =  Initialize History Manager
    Set State  ${entity}  3
    ${date1} =  Get Current Time
    Advance Time  1 min
    Set State  ${entity}  2
    ${date2} =  Get Current Time
    Advance Time  1 min
    Set State  ${entity}  3
    ${date3} =  Get Current Time
    Advance Time  1 min
    Set State  ${entity}  0
    ${date4} =  Get Current Time
    History Should Be  ${history_manager}
    ...    ${date1}  ${3}
    ...    ${date2}  ${2}
    ...    ${date3}  ${3}
    ...    ${date4}  ${0}


Old History Elements Are Removed
    ${history_manager} =  Initialize History Manager
    Set State  ${entity}  20
    Advance Time  20 min
    Set State  ${entity}  13
    ${date1} =  Get Current Time
    Advance Time  20 min
    Set State  ${entity}  1
    ${date2} =  Get Current Time
    Advance Time  20 min
    Set State  ${entity}  6
    ${date3} =  Get Current Time
    Advance Time  21 min
    Set State  ${entity}  54
    ${date4} =  Get Current Time
    History Should Be  ${history_manager}
    ...    ${date1}  ${13}
    ...    ${date2}  ${1}
    ...    ${date3}  ${6}
    ...    ${date4}  ${54}


Nothing Happens For A Long Time
    ${history_manager} =  Initialize History Manager
    Set State  ${entity}  42
    ${date1} =  Get Current Time
    Advance Time  2 h
    History Should Be  ${history_manager}  ${date1}  ${42}
    Set State  ${entity}  10
    ${date2} =  Get Current Time
    History Should Be  ${history_manager}
    ...    ${date1}  ${42}
    ...    ${date2}  ${10}
    Advance Time  61 min
    History Should Be  ${history_manager}  ${date2}  ${10}


History Enabler
    Set State  ${enabler}  off
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${5}
    &{base_interval} =  Create Dictionary  minutes=${1}
    ${history_enabler} =  Create App  enabler  HistoryEnabler  history_enabler
    ...    manager=history_manager
    ...    interval=${interval}
    ...    base_interval=${base_interval}
    ...    aggregator=integral
    ...    min=${10}  max=${20}
    ${switch} =  Create App  auto_switch  AutoSwitch  switch  target=${enabler}
    @{targets} =  Create List  switch
    ${enabled_switch} =  Create App  enabled_switch  EnabledSwitch  enabled_switch
    ...    enabler=history_enabler  targets=${targets}

    Schedule Call At   2 min       set_state  ${entity}  3
    Schedule Call At  20 min 30 s  set_state  ${entity}  5
    Schedule Call At  40 min       set_state  ${entity}  1
    State Should Change At  ${enabler}  on    6 min
    State Should Change At  ${enabler}  off  23 min 30 s
    State Should Change At  ${enabler}  on   42 min
    State Should Change At  ${enabler}  off  44 min


Aggregated Value
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${3}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=integral

    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${0}
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${0}
    Set State  ${entity}  4
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${4}   # 1*4
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${8}   # 2*4
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${12}  # 3*4
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${12}  # 3*4
    Set State  ${entity}  10
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${18}  # 2*4 + 1*10
    Advance Time  30 sec
    State Should Be As  ${aggregated_entity}  int  ${18}  # 2*4 + 1*10
    Set State  ${entity}  3
    State Should Be As  ${aggregated_entity}  int  ${21}  # 1.5*4 + 1.5*10
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${20}  # 0.5*4 + 1.5*10 + 1*3
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${16}  # 1*10 + 2*3
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${9}   # 3*3
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${9}   # 3*3


Aggregated Value With Base Interval
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${3}
    &{base_interval} =  Create Dictionary  seconds=${10}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    base_interval=${base_interval}
    ...    aggregator=integral

    Advance Time  20 sec
    Set State  ${entity}  3
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${3}   # 1*3
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${6}   # 2*3
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${9}   # 3*3
    Advance Time  30 sec
    State Should Be As  ${aggregated_entity}  int  ${18}  # 6*3
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${36}  # 12*3
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${54}  # 18*3
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${54}  # 18*3
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${54}  # 18*3
    Set State  ${entity}  5
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${56}  # 17*3 + 1*5
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${58}  # 16*3 + 2*5
    Advance Time  10 sec
    State Should Be As  ${aggregated_entity}  int  ${60}  # 15*3 + 3*5
    Advance Time  30 sec
    State Should Be As  ${aggregated_entity}  int  ${66}  # 12*3 + 6*5
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  int  ${78}  # 6*3 + 12*5
    Advance Time  50 s
    State Should Be As  ${aggregated_entity}  int  ${88}  # 1*3 + 17*5
    Advance Time  10 s
    State Should Be As  ${aggregated_entity}  int  ${90}  # 18*5


Mean Value
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${3}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=mean

    Set State  ${entity}  0
    Advance Time  1 min
    Set State  ${entity}  20
    Advance Time  1 min
    Set State  ${entity}  10
    Advance Time  1 min
    # (0*1 + 20*1 + 10*1) / 3
    State Should Be As  ${aggregated_entity}  int  ${10}


Mean Value Irregular Intervals
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${3}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=mean

    Set State  ${entity}  20
    Advance Time  1 min
    Set State  ${entity}  16
    Advance Time  30 s
    Set State  ${entity}  6
    Advance Time  30 s
    Set State  ${entity}  2
    Advance Time  1 min 30 s
    Set State  ${entity}  0
    # (0.5*20 + 0.5*16 + 0.5*6 + 1.5*2) / 3
    State Should Be As  ${aggregated_entity}  int  ${8}


Anglemean
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${4}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=anglemean

    Set State  ${entity}  30
    Advance Time  1 min
    Set State  ${entity}  60
    Advance Time  2 min
    Set State  ${entity}  300
    Advance Time  1 min
    # (1*30 + 2*60 + 1*-60) / 4
    State Should Be As  ${aggregated_entity}  int  ${22}
    Advance Time  1 min
    # (2*60 + 2*-60) / 4
    State Should Be As  ${aggregated_entity}  int  ${0}
    Advance Time  1 min
    # (1*60 + 3*-60) / 4
    State Should Be As  ${aggregated_entity}  int  ${330}
    Advance Time  1 min
    # (4*300) / 4
    State Should Be As  ${aggregated_entity}  int  ${300}
    Set State  ${entity}  180
    Advance Time  1 min
    # (3*300 + 1*180) / 4
    State Should Be As  ${aggregated_entity}  int  ${270}
    Advance Time  1 min
    # (2*300 + 2*180) / 4
    State Should Be As  ${aggregated_entity}  int  ${240}
    Advance Time  1 min
    # (1*300 + 3*180) / 4
    State Should Be As  ${aggregated_entity}  int  ${210}
    Advance Time  1 min
    # (4*180) / 4
    State Should Be As  ${aggregated_entity}  int  ${180}


Min Max Sum Values
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${5}
    ${sum_value} =  Create App  history  AggregatedValue  sum_value
    ...    manager=history_manager
    ...    target=${sum_entity}
    ...    interval=${interval}
    ...    aggregator=sum
    ${min_value} =  Create App  history  AggregatedValue  min_value
    ...    manager=history_manager
    ...    target=${min_entity}
    ...    interval=${interval}
    ...    aggregator=min
    ${max_value} =  Create App  history  AggregatedValue  max_value
    ...    manager=history_manager
    ...    target=${max_entity}
    ...    interval=${interval}
    ...    aggregator=max

    Set State  ${entity}  20
    Advance Time  5 min
    State Should Be As  ${min_entity}  int  ${20}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${20}
    Advance Time  1 min
    Set State  ${entity}  6
    State Should Be As  ${min_entity}  int  ${6}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${26}
    Advance Time  30 s
    Set State  ${entity}  10
    State Should Be As  ${min_entity}  int  ${6}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${36}
    Advance Time  30 s
    Set State  ${entity}  -2
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${34}
    Advance Time  30 s
    Set State  ${entity}  12
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${46}
    Advance Time  1 min
    Set State  ${entity}  0
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${46}
    Advance Time  1 min
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${46}
    Advance Time  1 min
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${20}
    State Should Be As  ${sum_entity}  int  ${46}
    Advance Time  1 min
    State Should Be As  ${min_entity}  int  ${-2}
    State Should Be As  ${max_entity}  int  ${12}
    State Should Be As  ${sum_entity}  int  ${20}
    Advance Time  1 min
    State Should Be As  ${min_entity}  int  ${0}
    State Should Be As  ${max_entity}  int  ${12}
    State Should Be As  ${sum_entity}  int  ${12}
    Advance Time  1 min
    State Should Be As  ${min_entity}  int  ${0}
    State Should Be As  ${max_entity}  int  ${0}
    State Should Be As  ${sum_entity}  int  ${0}


Decaying Sum Value
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${1}
    ${aggregated_value} =  Create App  history  AggregatedValue  aggregated_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=decay_sum
    ...    fraction=${0.5}

    Set State  ${entity}  100
    State Should Be As  ${aggregated_entity}  float  ${100.0}
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  float  ${50.0}
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  float  ${25.0}
    Set State  ${entity}  1
    State Should Be As  ${aggregated_entity}  float  ${26.0}
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  float  ${13.0}
    Advance Time  1 min
    State Should Be As  ${aggregated_entity}  float  ${6.5}
    Advance Time  6 min
    State Should Be As  ${aggregated_entity}  float  ${0.1015625}


Binary Input
    ${history_manager} =  Initialize History Manager
    &{interval} =  Create Dictionary  minutes=${5}
    ${sum_value} =  Create App  history  AggregatedValue  sum_value
    ...    manager=history_manager
    ...    target=${aggregated_entity}
    ...    interval=${interval}
    ...    aggregator=mean

    Advance Time To  5 min
    Turn On  ${entity}
    Advance Time  2 min
    # 2*1 / 5
    State Should Be As  ${aggregated_entity}  percent  ${40}
    Turn Off  ${entity}
    Advance Time  1 min
    # (2*1 + 1*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${40}
    Advance Time  1 min
    # (2*1 + 2*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${40}
    Advance Time  1 min
    # (2*1 + 3*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${40}
    Advance Time  1 min
    # (1*1 + 4*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${20}
    Turn On  ${entity}
    Advance Time  1 min
    # (4*0 + 1*1) / 5
    State Should Be As  ${aggregated_entity}  percent  ${20}
    Advance Time  30 s
    Turn Off  ${entity}
    # (3.5*0 + 1.5*1) / 5
    State Should Be As  ${aggregated_entity}  percent  ${30}
    Advance Time  1 min
    # (2.5*0 + 1.5*1 + 1*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${30}
    Advance Time  1 min
    # (1.5*0 + 1.5*1 + 2*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${30}
    Advance Time  1 min
    # (0.5*0 + 1.5*1 + 3*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${30}
    Advance Time  1 min
    # (1*1 + 4*0) / 5
    State Should Be As  ${aggregated_entity}  percent  ${20}
    Advance Time  1 min
    # 5*0 / 5
    State Should Be As  ${aggregated_entity}  percent  ${0}


Change Tracker
    Set State  ${entity}  0
    ${change_tracker} =  Create App  history  ChangeTracker  change_tracker
    ...    entity=${entity}
    Advance Time To  00:01:00
    Set State  ${entity}  a
    Check Date Updates  ${change_tracker}  00:01:00  00:01:00
    Advance Time To  00:02:00
    Set State  ${entity}  b  foo=bar
    Check Date Updates  ${change_tracker}  00:02:00  00:02:00
    Advance Time To  00:03:00
    Set State  ${entity}  b  foo=baz
    Check Date Updates  ${change_tracker}  00:02:00  00:03:00
    Advance Time To  00:04:00
    Set State  ${entity}  b  foo=baz
    Check Date Updates  ${change_tracker}  00:02:00  00:03:00


*** Keywords ***

Initialize History Manager
    Set State  ${entity}  0
    ${history_manager} =  Create History Manager  history_manager  ${entity}
    RETURN  ${history_manager}

Should Be Loaded
    [Arguments]  ${app}
    ${result} =  Call On App  ${app}  is_loaded
    Should Be True  ${result}

Check Date Updates
    [Arguments]  ${change_tracker}  ${expected_changed}  ${expected_updated}
    ${actual_changed} =  Call On App  ${change_tracker}
    ...    last_changed
    Times Should Match  ${actual_changed}  ${expected_changed}
    ${actual_updated} =  Call On App  ${change_tracker}
    ...    last_updated
    Times Should Match  ${actual_updated}  ${expected_updated}
