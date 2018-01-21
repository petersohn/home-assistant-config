*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Variables  libraries/Directories.py


*** Variables ***

${home_assistant_host}  127.0.0.1
${home_assistant_port}  18123


*** Keywords ***

Start Home Assistant
    ${hass_process} =  Start Process   hass
    ...    --verbose
    ...    --config    ${hass_config_path}
    ...    --log-file  ${OUTPUT_DIRECTORY}/homeassistant.log
    Set Test Variable  ${hass_process}

Check Home Assistant
    Process Should Be Running  ${hass_process}
    Create Http Context  ${home_assistant_host}:${home_assistant_port}
    GET  /api/
    Response Status Code Should Equal  200
    ${body} =  Get Response Body
    Json Value Should Equal  ${body}  /message  "API running."

Wait For Home Assistant To Start
    Wait Until Keyword Succeeds  30 sec  0.2 sec
    ...    Check Home Assistant

Stop Home Assistant
    Send Signal To Process  TERM  ${hass_process}

Wait For Home Assistant To Stop
    Wait For Process  ${hass_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped
