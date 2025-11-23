*** Settings ***

Library    apps/mutex_graph.py
Library    libraries/config.py
Library    DateTime

*** Variables ***

*** Keywords ***

Create Test Harness
    [Arguments]  ${start_date}=${default_start_date}  ${start_time}=00:00:00
    Set Test Variable  ${start_date}
    ${start_datetime} =  Add Time To Date  ${start_date}  ${start_time}  result_format=datetime
    ${app_manager} =  Create App Manager  ${start_datetime}  logs/${SUITE_NAME}/${TEST_NAME}.log
    Set Test Variable  ${app_manager}
    ${locker} =  Create App  locker  Locker  locker  enable_logging=${True}
    Set Test Variable  ${locker}
    ${test_app} =  Create App  test_app  TestApp  test_app
    Set Test Variable  ${test_app}

Cleanup Test Harness
    Append And Check Mutex Graph

Create App
    [Arguments]  ${module}  ${class}  ${name}  &{args}
    ${app} =  Call Method  ${app_manager}  create_app  ${module}  ${class}  ${name}  &{args}
    RETURN  ${app}

Append And Check Mutex Graph
    ${mutex_graph} =  Call Method  ${locker}  get_global_graph
    Append Graph  ${global_mutex_graph}  ${mutex_graph}
    ${graph_str} =  Format Graph  ${mutex_graph}  Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${mutex_graph}
    Should Be Equal  ${deadlock}  ${False}

Call On App
    [Arguments]  ${app}  ${method}  @{args}  &{kwargs}
    ${result} =  Call Method  ${app}  ${method}  @{args}  &{kwargs}
    Call Method  ${app_manager}  call_pending_callbacks
    RETURN  ${result}

Step
    Call Method  ${app_manager}  step  ${appdaemon_interval}

Advance Time
    [Arguments]  ${amount}
    ${amount_timedelta} =  Convert Time  ${amount}  result_format=timedelta
    Call Method  ${app_manager}  advance_time
    ...    ${amount_timedelta}  ${appdaemon_interval}

Advance Time To
    [Arguments]  ${target}
    ${target_date} =  Add Time To Date  ${start_date}  ${target}
    Advance Time To Date Time  ${target_date}

Advance Time To Date Time
    [Arguments]  ${target}
    ${target_datetime} =  Convert Date  ${target}  result_format=datetime
    Call Method  ${app_manager}  advance_time_to
    ...    ${target_datetime}  ${appdaemon_interval}

Get Current Time
    ${result} =  Call Method  ${app_manager}  datetime
    RETURN  ${result}

Get State
    [Arguments]  ${entity_id}  &{kwargs}
    ${value} =  Call On App  ${test_app}  get_state_as  ${entity_id}  &{kwargs}
    RETURN  ${value}

State Should Be
    [Arguments]  ${entity_id}  ${expected_value}
    ${value} =  Get State  ${entity_id}
    Should Be Equal  ${value}  ${expected_value}

Attribute Should Be
    [Arguments]  ${entity_id}  ${attribute}  ${expected_value}
    ${value} =  Get State  ${entity_id}  attribute=${attribute}
    Should Be Equal  ${value}  ${expected_value}

State Should Not Be
    [Arguments]  ${entity_id}  ${not_expected_value}
    ${value} =  Get State  ${entity_id}
    Should Not Be Equal  ${value}  ${not_expected_value}

State Should Be As
    [Arguments]  ${entity_id}  ${type}  ${expected_value}
    ${value} =  Get State  ${entity_id}  type=${type}
    Should Be Equal  ${value}  ${expected_value}

Set State
    [Arguments]  ${entity_id}  ${value}  &{attributes}
    Call On App  ${test_app}  set_state  ${entity_id}  ${value}  ${attributes}

Turn On
    [Arguments]  ${entity_id}
    Set State  ${entity_id}  on

Turn Off
    [Arguments]  ${entity_id}
    Set State  ${entity_id}  off

Schedule Call In
    [Arguments]  ${time}  ${function}  @{args}  &{kwargs}
    ${delay} =  Convert Time  ${time}  result_format=timedelta
    Call On App  ${test_app}
    ...    schedule_call_in  ${delay}  ${function}  @{args}  &{kwargs}

Schedule Call At
    [Arguments]  ${time}  ${function}  @{args}  &{kwargs}
    ${date} =  Add Time To Date  ${start_date}  ${time}
    Schedule Call At Date Time  ${date}  ${function}  @{args}  &{kwargs}

Schedule Call At Date Time
    [Arguments]  ${date}  ${function}  @{args}  &{kwargs}
    ${date_time} =  Convert Date  ${date}  result_format=datetime
    Call On App  ${test_app}
    ...    schedule_call_at  ${date_time}  ${function}  @{args}  &{kwargs}

Wait For State Change
    [Arguments]  ${entity}
    ...          ${timeout}=${None}
    ...          ${deadline}=${None}
    ...          &{kwargs}
    IF  ${{$timeout is not None}}
        ${now} =  Get Current Time
        ${date_time} =  Add Time To Date  ${now}  ${timeout}  result_format=datetime
    ELSE IF  ${{$deadline is not None}}
        ${date_time} =  Add Time To Date  ${start_date}  ${deadline}  result_format=datetime
    ELSE
        ${date_time} =  Set Variable  ${None}
    END
    Call On App  ${app_manager}  wait_for_state_change
    ...    ${entity}  ${date_time}  ${appdaemon_interval}  &{kwargs}

State Should Not Change For
    [Arguments]  ${entity}  ${time}
    ${old_state} =  Get State  ${entity}
    ${before_time} =  Get Current Time
    Wait For State Change  ${entity}  timeout=${time}
    ${after_time} =  Get Current Time
    State Should Be  ${entity}  ${old_state}
    ${time_difference} =  Subtract Date From Date  ${after_time}  ${before_time}
    ${expected_difference} =  Convert Time  ${time}
    Should Be Equal  ${time_difference}  ${expected_difference}

State Should Not Change Until
    [Arguments]  ${entity}  ${time}
    ${old_state} =  Get State  ${entity}
    Wait For State Change  ${entity}  deadline=${time}
    State Should Be  ${entity}  ${old_state}
    Current Time Should Be  ${time}

State Should Change At
    [Arguments]  ${entity}  ${value}  ${time}
    ${deadline} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Be  ${entity}  ${value}
    State Should Not Change Until  ${entity}  ${deadline}
    Step
    State Should Be  ${entity}  ${value}

State Should Change In
    [Arguments]  ${entity}  ${value}  ${time}
    ${timeout} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Be  ${entity}  ${value}
    State Should Not Change For  ${entity}  ${timeout}
    Step
    State Should Be  ${entity}  ${value}
