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
    ...    stdout=${base_output_directory}/homeassistant.stdout
    ...    stderr=${base_output_directory}/homeassistant.stderr
    Set Suite Variable  ${hass_process}

Check Home Assistant
    Process Should Be Running  ${hass_process}
    GET  /api/
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

Do Switch Off
    [Arguments]  ${entity_id}
    Set Request Body To Dictionary  entity_id=${entity_id}
    Ask For Connection Keepalive
    POST  /api/services/homeassistant/turn_off

Do Clean State
    [Arguments]  ${entity_id}
    ${is_switch} =  Run Keyword And Return Status
    ...    Should Match  ${entity_id}  input_boolean.*
    Run Keyword If  ${is_switch}
    ...    Do Switch Off  ${entity_id}
    ...    ELSE
    ...    Do Delete State  ${entity_id}

Do Get State
    [Arguments]  ${entity_id}
    Ask For Connection Keepalive
    GET  /api/states/${entity_id}
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    [Return]  ${content['state']}

Do Get States
    Ask For Connection Keepalive
    GET  /api/states
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    [Return]  ${content}

Do Clean States
    @{content} =  Do Get States
    :FOR  ${entity}  IN  @{content}
    \    Do Clean State  ${entity['entity_id']}

Do Initialize State
    [Arguments]  ${entity}  ${state}
    Set Request Body To Dictionary  state=${state}
    Ask For Connection Keepalive
    POST  /api/states/${entity}

Do Initialize States
    [Arguments]  &{states}
    :FOR  ${entity}  IN  @{states.keys()}
    \    Do Initialize State  ${entity}  ${states['${entity}']}

Do Check State
    [Arguments]  ${entity}  ${expected_state}
    ${actual_state} =  Do Get State  ${entity}
    Should Be Equal  ${actual_state}  ${expected_state}

Wait Until State Becomes
    [Arguments]  ${entity}  ${state}  ${timeout}=1s
    ${result} =  Run In Http Context
    ...    ${home_assistant_host}
    ...    Wait Until Keyword Succeeds  ${timeout}  0.01 s
    ...    Do Check State  ${entity}  ${state}
    [Return]  ${result}

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
