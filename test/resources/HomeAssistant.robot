*** Settings ***

Library    HttpLibrary.HTTP
Library    ../libraries/Process.py
Variables  ../libraries/Directories.py


*** Variables ***

${home_assistant_host}  127.0.0.1
${home_assistant_port}  18123


*** Keywords ***

Start Home Assistant
    ${hass_process} =  Run Process   hass
    ...    --verbose
    ...    --config    ${hass_config_path}
    ...    --log-file  ${OUTPUT_DIRECTORY}/homeassistant.log
    Set Test Variable  ${hass_process}

Check Home Assistant
    ${is_running} =  Is Process Running  ${hass_process}
    Should Be True  ${is_running}
    Create Http Context  ${home_assistant_host}:${home_assistant_port}
    GET  /api/
    Response Status Code Should Equal  200
    ${body} =  Get Response Body
    Json Value Should Equal  ${body}  /message  "API running."

Wait For Home Assistant To Start
    Wait Until Keyword Succeeds  1 min  0.5 sec
    ...    Check Home Assistant

Stop Home Assistant
    Terminate Process  ${hass_process}

Wait For Home Assistant To Stop
    Wait For Process  ${hass_process}
