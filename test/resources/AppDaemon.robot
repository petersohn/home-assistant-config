*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
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

Call Function
    [Arguments]  ${function}  @{args}  &{kwargs}
    Create Http Context  ${app_daemon_host}:${app_daemon_port}
    ${content} =  Create Dictionary
    ...    function=${function}
    ...    args=@{args}
    ...    kwargs=&{kwargs}
    ${body} =  Stringify Json  ${content}
    Set Request Body  ${body}
    POST  /api/appdaemon/TestApp
    Response Status Code Should Equal  200
    ${response} =  Get Response Body
    ${result} =  Parse Json  ${response}
    [Return]  ${result}

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
