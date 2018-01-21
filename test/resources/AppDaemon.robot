*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Variables  libraries/Directories.py


*** Variables ***

${app_daemon_host}  127.0.0.1
${app_daemon_port}  18124


*** Keywords ***

Start AppDaemon
    ${app_daemon_process} =  Start Process   appdaemon
    ...    --config     ${OUTPUT_DIRECTORY}
    ...    --starttime  2018-01-01 12:00:00
    ...    --tick       1
    Set Test Variable  ${app_daemon_process}

Check AppDaemon
    Process Should Be Running  ${app_daemon_process}
    Create Http Context  ${app_daemon_host}:${app_daemon_port}
    Set Request Body  "{}"
    POST  /api/appdaemon/TestApp
    Response Status Code Should Equal  200

Wait For AppDaemon To Start
    Wait Until Keyword Succeeds  30 sec  0.2 sec
    ...    Check AppDaemon

Stop AppDaemon
    Send Signal To Process  TERM  ${app_daemon_process}

Wait For AppDaemon To Stop
    Wait For Process  ${app_daemon_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped
