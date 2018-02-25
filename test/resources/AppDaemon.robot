*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Library    DateTime
Library    libraries/TypeUtil.py
Resource   resources/ErrorHandling.robot
Resource   resources/Http.robot
Variables  libraries/Directories.py


*** Variables ***

${app_daemon_host}  127.0.0.1:18124
${test_arg}         This is a test


*** Keywords ***

Start AppDaemon
    [Arguments]  ${start_time}
    ${start_datetime} =  Add Time To Date  ${start_date}  ${start_time}
    ...    exclude_millis=true
    ${app_daemon_process} =  Start Process   python  TestAppDaemon.py
    ...    --config      ${OUTPUT_DIRECTORY}
    ...    --starttime   ${start_datetime}
    ...    --tick        0
    ...    --interval    ${appdaemon_interval}
    ...    stdout=${OUTPUT_DIRECTORY}/appdaemon.stdout
    ...    stderr=${OUTPUT_DIRECTORY}/appdaemon.stderr
    Set Test Variable    ${app_daemon_process}

Create Call Data
    [Arguments]  ${function}  ${result_type}  @{args}  &{kwargs}
    ${result} =  Create Dictionary
    ...    function=${function}
    ...    result_type=${result_type}
    ...    args=@{args}
    ...    kwargs=&{kwargs}
    [Return]  ${result}

Call Function
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${result_type} =  Extract From Dictionary  ${kwargs}  result_type
    ${content} =  Create Call Data  ${function}  ${result_type}
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

Unblock Until
    [Arguments]  ${when}  ${real_timeout}=5s
    Call Function  unblock_until  ${when}
    Wait Until Blocked  ${real_timeout}

Unblock For
    [Arguments]  ${delay}  ${real_timeout}=5s
    Call Function  unblock_for  ${delay}
    Wait Until Blocked  ${real_timeout}

Unblock Until State Change
    [Arguments]  ${entity}
    ...          ${timeout}=${None}
    ...          ${deadline}=${None}
    ...          ${real_timeout}=5s
    ...          &{kwargs}
    Call Function  unblock_until_state_change  ${entity}
    ...    timeout=${timeout}  deadline=${deadline}  &{kwargs}
    Wait Until Blocked  ${real_timeout}

Unblock Until Date Time
    [Arguments]  ${when}  ${real_timeout}=5s
    Call Function  unblock_until_date_time  ${when}
    Wait Until Blocked  ${real_timeout}

Calculate Time
    [Arguments]  ${function}  ${delay}
    ${target} =  Call Function  ${function}  result_type=str
    ${result} =  Add Time To Date  ${target}  ${delay}
    [Return]  ${result}

Unblock Until Sunrise
    [Arguments]  ${delay}=${0}  ${real_timeout}=5s
    ${target} =  Calculate Time  sunrise  ${delay}
    Unblock Until Date Time  ${target}  ${real_timeout}

Unblock Until Sunset
    [Arguments]  ${delay}=${0}  ${real_timeout}=5s
    ${target} =  Calculate Time  sunset  ${delay}
    Unblock Until Date Time  ${target}  ${real_timeout}

State Should Not Change
    [Arguments]  ${entity}  @{args}  &{kwargs}
    ${old_state} =  Get State  ${entity}
    Unblock Until State Change  ${entity}  @{args}  &{kwargs}
    State Should Be  ${entity}  ${old_state}

State Should Change At
    [Arguments]  ${entity}  ${value}  ${time}
    ${deadline} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Change  ${entity}  deadline=${deadline}
    Unblock For  ${appdaemon_interval}
    State Should Be  ${entity}  ${value}

State Should Change In
    [Arguments]  ${entity}  ${value}  ${time}
    ${timeout} =  Subtract Time From Time  ${time}  ${appdaemon_interval}
    State Should Not Change  ${entity}  timeout=${timeout}
    Unblock For  ${appdaemon_interval}
    State Should Be  ${entity}  ${value}

Schedule Call At
    [Arguments]  ${when}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  @{args}  &{kwargs}
    Call Function  schedule_call_at  ${when}  ${data}

Schedule Call In
    [Arguments]  ${delay}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  @{args}  &{kwargs}
    Call Function  schedule_call_in  ${delay}  ${data}

Schedule Call At Date Time
    [Arguments]  ${when}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  ${None}  @{args}  &{kwargs}
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

Get State
    [Arguments]  ${entity_id}
    ${value} =  Call Function  get_state  ${entity_id}
    [Return]  ${value}

State Should Be
    [Arguments]  ${entity_id}  ${expected_value}
    ${value} =  Get State  ${entity_id}
    Should Be Equal  ${value}  ${expected_value}

Set State
    [Arguments]  ${entity_id}  ${value}
    Call Function  set_sensor_state  ${entity_id}  ${value}

Turn On
    [Arguments]  ${entity_id}
    Call Function  turn_on  ${entity_id}

Turn Off
    [Arguments]  ${entity_id}
    Call Function  turn_off  ${entity_id}

Check AppDaemon
    Critical Check  AppDaemon process failed to start
    ...    Process Should Be Running  ${app_daemon_process}
    ${result} =  Call Function  test  ${test_arg}
    Should Be Equal  ${result}  ${test_arg}

Wait For AppDaemon To Start
    Wait Until Keyword Succeeds  10 sec  0.2 sec
    ...    Run In Http Context  ${app_daemon_host}
    ...    Check AppDaemon
    Create Http Context  ${app_daemon_host}

Stop AppDaemon
    Send Signal To Process  TERM  ${app_daemon_process}
    Restore Http Context

Wait For AppDaemon To Stop
    Wait For Process  ${app_daemon_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped
