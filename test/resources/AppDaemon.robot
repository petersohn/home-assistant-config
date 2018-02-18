*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Library    DateTime
Variables  libraries/Directories.py


*** Variables ***

${app_daemon_host}  127.0.0.1
${app_daemon_port}  18124
${test_arg}         This is a test


*** Keywords ***

Start AppDaemon
    ${app_daemon_process} =  Start Process   python  TestAppDaemon.py
    ...    --config     ${OUTPUT_DIRECTORY}
    ...    --starttime  ${start_time}
    ...    --tick       0
    ...    --interval   ${appdaemon_interval}
    Set Test Variable  ${app_daemon_process}

Create Call Data
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${result} =  Create Dictionary
    ...    function=${function}
    ...    args=@{args}
    ...    kwargs=&{kwargs}
    [Return]  ${result}

Call Function
    [Arguments]  ${function}  @{args}  &{kwargs}
    Create Http Context  ${app_daemon_host}:${app_daemon_port}
    ${content} =  Create Call Data  ${function}  @{args}  &{kwargs}
    ${body} =  Stringify Json  ${content}
    Set Request Body  ${body}
    POST  /api/appdaemon/TestApp
    Response Status Code Should Equal  200
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
    [Arguments]  ${when}  ${timeout}=5s
    ${epoch} =  Convert Date  ${when}  result_format=epoch
    Call Function  unblock_until  ${epoch}
    Wait Until Blocked  ${timeout}

Unblock For
    [Arguments]  ${delay}  ${timeout}=5s
    ${current_time} =  Call Function  get_current_time
    ${end_time} =  Add Time To Time  ${current_time}  ${delay}
    ${seconds} =  Convert Time  ${delay}  result_format=number
    Call Function  unblock_for  ${seconds}
    Wait Until Blocked  ${timeout}

Schedule Call At
    [Arguments]  ${when}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  @{args}  &{kwargs}
    ${epoch} =  Convert Date  ${when}  result_format=epoch
    Call Function  schedule_call_at  ${epoch}  ${data}

Schedule Call In
    [Arguments]  ${delay}  ${function}  @{args}  &{kwargs}
    ${data} =  Create Call Data  ${function}  @{args}  &{kwargs}
    ${seconds} =  Convert Time  ${delay}  result_format=number
    Call Function  schedule_call_in  ${seconds}  ${data}

State Should Be
    [Arguments]  ${entity_id}  ${expected_value}
    ${value} =  Call Function  get_state  ${entity_id}
    Should Be Equal  ${value}  ${expected_value}

Set State
    [Arguments]  ${entity_id}  ${value}
    Call Function  set_state  ${entity_id}  state=${value}

Check AppDaemon
    Process Should Be Running  ${app_daemon_process}
    ${result} =  Call Function  test  ${test_arg}
    Should Be Equal  ${result}  ${test_arg}

Wait For AppDaemon To Start
    Wait Until Keyword Succeeds  30 sec  0.2 sec
    ...    Check AppDaemon

Stop AppDaemon
    Send Signal To Process  TERM  ${app_daemon_process}

Wait For AppDaemon To Stop
    Wait For Process  ${app_daemon_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped