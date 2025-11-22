*** Settings ***

Library    apps/mutex_graph.py
Library    libraries/config.py

*** Variables ***

*** Keywords ***

Create Test Harness
    [Arguments]  ${start_date}=${default_start_date}  ${start_time}=00:00:00
    ${start_datetime} =  Add Time To Date  ${start_date}  ${start_time}  result_format=datetime
    ${app_manager} =  Create App Manager  ${start_datetime}
    Set Test Variable  ${app_manager}
    ${locker} =  Call Method  ${app_manager}  create_app  locker  Locker  locker
    Set Test Variable  ${locker}

Cleanup Test Harness
    Append And Check Mutex Graph

Append And Check Mutex Graph
    ${mutex_graph} =  Call Method  ${locker}  get_global_graph
    Append Graph  ${global_mutex_graph}  ${mutex_graph}
    ${graph_str} =  Format Graph  ${mutex_graph}  Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${mutex_graph}
    Should Be Equal  ${deadlock}  ${False}

Step
    Call Method  ${app_manager}  ${appdaemon_interval}

Advance Time
    [Arguments]  ${amount}
    ${amount_timedelta} =  Convert Time  ${amount}  result_format=timedelta
    Call Method  ${app_manager}  advance_time
    ...    ${amount_timedelta}  ${appdaemon_interval}

Advance Time To
    [Arguments]  ${target}
    ${target_datetime} =  Convert Time  ${target}  result_format=datetime
    Call Method  ${app_manager}  advance_time_to
    ...    ${target_datetime}  ${appdaemon_interval}

Get Current Time
    ${result} =  Call Method  ${app_manager}  datetime
    RETURN  ${result}

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
