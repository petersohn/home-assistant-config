*** Settings ***

Library    apps/mutex_graph.py
Library    libraries/config.py

*** Variables ***

*** Keywords ***

Create Test Harness
    [Arguments]  ${start_date}=${default_start_date}  ${start_time}=00:00:00
    Set Test Variable  ${start_date}
    ${start_datetime} =  Add Time To Date  ${start_date}  ${start_time}  result_format=datetime
    ${app_manager} =  Create App Manager  ${start_datetime}
    Set Test Variable  ${app_manager}
    ${locker} =  Create App  locker  Locker  locker
    Set Test Variable  ${locker}
    ${test_app} =  Create App  test_app  TestApp  test_app
    Set Test Variable  ${test_app}

Cleanup Test Harness
    Append And Check Mutex Graph

Create App
    [Arguments]  ${module}  ${class}  ${name}
    ${app} =  Call Method  ${app_manager}  create_app  ${module}  ${class}  ${name}
    [Return]  ${app}

Append And Check Mutex Graph
    ${mutex_graph} =  Call Method  ${locker}  get_global_graph
    Append Graph  ${global_mutex_graph}  ${mutex_graph}
    ${graph_str} =  Format Graph  ${mutex_graph}  Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${mutex_graph}
    Should Be Equal  ${deadlock}  ${False}

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
    ${value} =  Call Method  ${app_manager}  get_state  ${entity_id}  &{kwargs}
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
    ${value} =  Get State  ${entity_id}  result_type=${type}
    Should Be Equal  ${value}  ${expected_value}

Set State
    [Arguments]  ${entity_id}  ${value}  &{attributes}
    Call Method  ${app_manager}  set_state  ${entity_id}  ${value}  ${attributes}

Schedule Call In
    [Arguments]  ${time}  ${function}  @{args}  &{kwargs}
    ${delay} =  Convert Time  ${time}  result_format=timedelta
    Call Method  ${test_app}
    ...    schedule_call_in  ${delay}  ${function}  @{args}  &{kwargs}

Schedule Call At
    [Arguments]  ${time}  ${function}  @{args}  &{kwargs}
    ${date_time} =  Add Time To Date  ${start_date}  ${time}  result_format=datetime
    Call Method  ${test_app}
    ...    schedule_call_at  ${date_time}  ${function}  @{args}  &{kwargs}

Wait For State Change
    [Arguments]  ${entity}
    ...          ${timeout}=${None}
    ...          ${deadline}=${None}
    IF  ${{$timeout is not None}}
        ${now} =  Get Current Time
        ${deadline} =  Add Time To Date  ${now}  ${timeout}  result_format=datetime
    END
    Call Method  ${app_manager}
    ...    wait_for_state_change  ${entity}  ${deadline}  ${appdaemon_interval}
