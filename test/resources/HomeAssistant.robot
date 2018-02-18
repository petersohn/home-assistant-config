*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Variables  libraries/Directories.py


*** Variables ***

${home_assistant_host}  127.0.0.1
${home_assistant_port}  18123


*** Keywords ***

Start Home Assistant
    ${hass_process} =   Start Process   hass
    ...    --verbose
    ...    --config     ${hass_config_path}
    ...    --log-file   ${base_output_directory}/homeassistant.log
    Set Suite Variable  ${hass_process}

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

Delete State
    [Arguments]  ${entity_id}
    Set Request Header  Connection  keep-alive
    DELETE  /api/states/${entity_id}
    Response Status Code Should Equal  200

Get States
    Create Http Context  ${home_assistant_host}:${home_assistant_port}
    Set Request Header  Connection  keep-alive
    GET  /api/states
    Response Status Code Should Equal  200
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    [Return]  ${content}

Clean States
    @{content} =  Get States
    :FOR  ${entity}  IN  @{content}
    \    Delete State  ${entity['entity_id']}
