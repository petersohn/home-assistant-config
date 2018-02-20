*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Resource   resources/Http.robot
Variables  libraries/Directories.py


*** Variables ***

${home_assistant_host}  127.0.0.1:18123


*** Keywords ***

Start Home Assistant
    ${hass_process} =   Start Process   hass
    ...    --verbose
    ...    --config     ${hass_config_path}
    ...    --log-file   ${base_output_directory}/homeassistant.log
    Set Suite Variable  ${hass_process}

Check Home Assistant
    Process Should Be Running  ${hass_process}
    GET  /api/
    Response Status Code Should Equal  200
    ${body} =  Get Response Body
    Json Value Should Equal  ${body}  /message  "API running."

Wait For Home Assistant To Start
    Wait Until Keyword Succeeds  30 sec  0.2 sec
    ...    Run In Http Context  ${home_assistant_host}
    ...    Check Home Assistant

Stop Home Assistant
    Send Signal To Process  TERM  ${hass_process}

Wait For Home Assistant To Stop
    Wait For Process  ${hass_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped

Do Delete State
    [Arguments]  ${entity_id}
    Ask For Connection Keepalive
    DELETE  /api/states/${entity_id}
    Response Status Code Should Equal  200

Do Get States
    Ask For Connection Keepalive
    GET  /api/states
    Response Status Code Should Equal  200
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    [Return]  ${content}

Do Clean States
    @{content} =  Do Get States
    :FOR  ${entity}  IN  @{content}
    \    Do Delete State  ${entity['entity_id']}

Do Initialize State
    [Arguments]  ${entity}  ${state}
    ${content} =  Create Dictionary  state=${state}
    ${body} =  Stringify Json  ${content}
    Set Request Body  ${body}
    POST  /api/states/${entity}

Do Initialize States
    [Arguments]  &{states}
    :FOR  ${entity}  IN  @{states.keys()}
    \    Do Initialize State  ${entity}  ${states['${entity}']}

Get States
    ${result} =  Run In Http Context
    ...    ${home_assistant_host}
    ...    Do Get States
    [Return]  ${result}

Clean States
    Run In Http Context  ${home_assistant_host}
    ...    Do Clean States

Initialize States
    [Arguments]  &{states}
    Run In Http Context  ${home_assistant_host}
    ...    Do Initialize States  &{states}
