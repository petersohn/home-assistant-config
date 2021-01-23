*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Library    DateTime
Library    libraries/TypeUtil.py
Resource   resources/DateTime.robot
Resource   resources/ErrorHandling.robot
Resource   resources/Http.robot
Variables  libraries/Directories.py


*** Variables ***

${test_arg}         This is a test


*** Keywords ***

Start AppDaemon
    [Arguments]  ${start_time}  ${start_date}=${default_start_date}
    Set Test Variable  ${app_daemon_host}  127.0.0.1:${app_daemon_api_port}
    ${start_datetime} =  Add Time To Date  ${start_date}  ${start_time}
    ...    exclude_millis=true
    ${app_daemon_process} =  Start Process   ./appdaemon
    ...    --config      ${OUTPUT_DIRECTORY}
    ...    --starttime   ${start_datetime}
    ...    --timewarp    0.1  # This cannot be 0 or 1
#     ...    --debug       DEBUG
    ...    stdout=${OUTPUT_DIRECTORY}/appdaemon.stdout
    ...    stderr=${OUTPUT_DIRECTORY}/appdaemon.stderr
    Set Test Variable    ${app_daemon_process}

Create Call Data
    [Arguments]  ${function}  ${result_type}  ${arg_types}  ${kwarg_types}
    ...          @{args}  &{kwargs}

    ${result} =  Create Dictionary
    ...    function=${function}
    ...    result_type=${result_type}
    ...    arg_types=${arg_types}
    ...    kwarg_types=${kwarg_types}
    ...    args=@{args}
    ...    kwargs=&{kwargs}
    [Return]  ${result}

Call Function
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${result_type} =  Extract From Dictionary  ${kwargs}  result_type
    ${arg_types} =  Extract From Dictionary  ${kwargs}  arg_types
    ${kwarg_types} =  Extract From Dictionary  ${kwargs}  kwarg_types
    ${content} =  Create Call Data  ${function}
    ...    ${result_type}  ${arg_types}  ${kwarg_types}
    ...    @{args}  &{kwargs}
    ${body} =  Stringify Json  ${content}
    Set Request Body  ${body}
    Ask For Connection Keepalive
    POST  /api/appdaemon/TestApp
    ${response} =  Get Response Body
    ${result} =  Parse Json  ${response}
    [Return]  ${result}

Should Be Blocked
    ${result} =  Call Function  is_blocked
    Should Be True  ${result}

Wait Until Blocked
    [Arguments]  ${timeout}
    Wait Until Keyword Succeeds  ${timeout}  0.01s
    ...    Should Be Blocked

State Should Be Stable
    ${result} =  Call Function  is_state_stable
    Should Be True  ${result}

Wait Until State Is Stable
    [Arguments]  ${timeout}=10s
    Wait Until Keyword Succeeds  ${timeout}  0.01s
    ...    State Should Be Stable

Unblock Until
    [Arguments]  ${when}  ${real_timeout}=30s
    Call Function  unblock_until  ${when}
    Wait Until Blocked  ${real_timeout}

Unblock For
    [Arguments]  ${delay}  ${real_timeout}=30s
    Call Function  unblock_for  ${delay}
    Wait Until Blocked  ${real_timeout}

Unblock Until State Change
    [Arguments]  ${entity}
    ...          ${timeout}=${None}
    ...          ${deadline}=${None}
    ...          ${real_timeout}=30s
    ...          &{kwargs}
    Call Function  unblock_until_state_change  ${entity}
    ...    timeout=${timeout}  deadline=${deadline}  &{kwargs}
    Wait Until Blocked  ${real_timeout}

Unblock Until Date Time
    [Arguments]  ${when}  ${real_timeout}=30s
    Call Function  unblock_until_date_time  ${when}
    Wait Until Blocked  ${real_timeout}

Unblock Until Sunrise
    [Arguments]  ${delay}=${0}  ${real_timeout}=30s
    ${target} =  Calculate Time  sunrise  ${delay}
    Unblock Until Date Time  ${target}  ${real_timeout}

Unblock Until Sunset
    [Arguments]  ${delay}=${0}  ${real_timeout}=30s
    ${target} =  Calculate Time  sunset  ${delay}
    Unblock Until Date Time  ${target}  ${real_timeout}

State Should Not Change Until
    [Arguments]  ${entity}  ${time}
    ${old_state} =  Get State  ${entity}
    Unblock Until State Change  ${entity}  deadline=${time}
    State Should Be  ${entity}  ${old_state}
    Current Time Should Be  ${time}

State Should Not Change For
    [Arguments]  ${entity}  ${time}
    ${old_state} =  Get State  ${entity}
    ${before_time} =  Call Function  get_current_time
    Unblock Until State Change  ${entity}  timeout=${time}
    ${after_time} =  Call Function  get_current_time
    State Should Be  ${entity}  ${old_state}
    ${time_difference} =  Subtract Date From Date  ${after_time}  ${before_time}
    ${expected_difference} =  Convert Time  ${time}
    Should Be Equal  ${time_difference}  ${expected_difference}

State Should Change Now
    [Arguments]  ${entity}  ${value}
    Wait Until Keyword Succeeds  5 s  0.01 s
    ...    State Should Be  ${entity}  ${value}

State Should Change At
    [Arguments]  ${entity}  ${value}  ${time}
    ${deadline} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Be  ${entity}  ${value}
    State Should Not Change Until  ${entity}  ${deadline}
    Unblock For  ${appdaemon_interval}
    State Should Change Now  ${entity}  ${value}

State Should Change In
    [Arguments]  ${entity}  ${value}  ${time}
    ${timeout} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Be  ${entity}  ${value}
    State Should Not Change For  ${entity}  ${timeout}
    Unblock For  ${appdaemon_interval}
    State Should Change Now  ${entity}  ${value}

Schedule Call At
    [Arguments]  ${when}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  ${None}  ${None}
    ...    @{args}  &{kwargs}
    Call Function  schedule_call_at  ${when}  ${data}

Schedule Call In
    [Arguments]  ${delay}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  ${None}  ${None}
    ...    @{args}  &{kwargs}
    Call Function  schedule_call_in  ${delay}  ${data}

Schedule Call At Date Time
    [Arguments]  ${when}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  ${None}  ${None}
    ...    @{args}  &{kwargs}
    Call Function  schedule_call_at_date_time  ${when}  ${data}

Schedule Call At Sunrise
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${delay} =  Extract From Dictionary  ${kwargs}  delay
    ${target} =  Calculate Time  sunrise  ${delay}
    Schedule Call At Date Time  ${target}  ${function}  @{args}  &{kwargs}

Schedule Call At Sunset
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${delay} =  Extract From Dictionary  ${kwargs}  delay
    ${target} =  Calculate Time  sunset  ${delay}
    Schedule Call At Date Time  ${target}  ${function}  @{args}  &{kwargs}

Get Date
    ${result} =  Call Function  get_date
    [Return]  ${result}

Get State
    [Arguments]  ${entity_id}  &{kwargs}
    ${value} =  Call Function  get_state  ${entity_id}  &{kwargs}
    [Return]  ${value}

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
    Call Function  set_sensor_state  ${entity_id}  ${value}  ${attributes}
    Wait Until State Is Stable

Select Option
    [Arguments]  ${entity_id}  ${value}
    Call Function  select_option  ${entity_id}  ${value}
    Wait Until State Is Stable

Turn On
    [Arguments]  ${entity_id}
    Call Function  turn_on  ${entity_id}
    Wait Until State Is Stable

Turn Off
    [Arguments]  ${entity_id}
    Call Function  turn_off  ${entity_id}
    Wait Until State Is Stable

Turn On Or Off
    [Arguments]  ${entity_id}  ${state}
    Run Keyword If  '${state}' == 'on'
    ...    Turn On  ${entity_id}
    ...    ELSE
    ...    Turn Off  ${entity_id}

Check AppDaemon
    Critical Check  AppDaemon process failed to start
    ...    Process Should Be Running  ${app_daemon_process}
    ${result} =  Call Function  test  ${test_arg}
    Should Be Equal  ${result}  ${test_arg}

Wait For AppDaemon To Start
    Wait Until Keyword Succeeds  30 sec  0.2 sec
    ...    Run In Http Context  ${app_daemon_host}
    ...    Check AppDaemon
    Create Http Context  ${app_daemon_host}

Stop AppDaemon
    Send Signal To Process  TERM  ${app_daemon_process}
    Restore Http Context

Wait For AppDaemon To Stop
    Wait For Process  ${app_daemon_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped

Append And Check Mutex Graph
    ${mutex_graph} =  Call Function  call_on_app  locker  get_global_graph
    Append Graph  ${global_mutex_graph}  ${mutex_graph}
    ${graph_str} =  Format Graph  ${mutex_graph}  Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${mutex_graph}
    Should Be Equal  ${deadlock}  ${False}
