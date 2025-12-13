*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Library    OperatingSystem
Library    libraries/HomeAssistant.py
Resource   resources/Http.robot
Variables  libraries/Directories.py


*** Variables ***

${home_assistant_token}  eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkY2U3MDgwNDIwYmI0Mjg3OWIyYjQ1MjQ4OTQzNjI4YiIsImlhdCI6MTU0NjI1MDYyNiwiZXhwIjoxODYxNjEwNjI2fQ.1YmZVaw3EH2bu0jExU2Q6mIyrD1Qf0cPPJmt877mNC0


*** Keywords ***

Start Home Assistant
    Set Suite Variable  ${home_assistant_port}  ${18000}  children=true
    Set Suite Variable  ${home_assistant_host}  127.0.0.1:${home_assistant_port}
    ...                 children=true
    ${hass_path} =    Set Variable  ${base_output_directory}/hass
    Remove Directory    ${hass_path}  recursive=${True}
    Create Home Assistant Configuration  ${hass_path}  ${home_assistant_port}
    Copy File           ${hass_config_path}//auth
    ...                 ${hass_path}/.storage/
    ${hass_process} =   Start Process   ./hass
    ...    --verbose
    ...    --config     ${hass_path}
    ...    --log-file   ${hass_path}/homeassistant.log
    ...    stdout=${hass_path}/homeassistant.stdout
    ...    stderr=${hass_path}/homeassistant.stderr
    Set Suite Variable  ${hass_process}

Check Home Assistant
    Process Should Be Running  ${hass_process}
    Authenticate
    GET  /api/
    ${body} =  Get Response Body
    Json Value Should Equal  ${body}  /message  "API running."

Wait For Home Assistant To Start
    Wait Until Keyword Succeeds  2 min  0.2 sec
    ...    Run In Http Context  ${home_assistant_host}
    ...    Check Home Assistant

Stop Home Assistant
    Send Signal To Process  TERM  ${hass_process}

Wait For Home Assistant To Stop
    Wait For Process  ${hass_process}  timeout=30 sec  on_timeout=kill
    Process Should Be Stopped

Authenticate
    Set Request Header  Authorization  Bearer ${home_assistant_token}

Do Delete State
    [Arguments]  ${entity_id}
    Ask For Connection Keepalive
    Authenticate
    DELETE  /api/states/${entity_id}

Do Switch Off
    [Arguments]  ${entity_id}
    Set Request Body To Dictionary  entity_id=${entity_id}
    Ask For Connection Keepalive
    Authenticate
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
    Authenticate
    GET  /api/states/${entity_id}
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    RETURN  ${content['state']}

Do Get States
    Ask For Connection Keepalive
    Authenticate
    GET  /api/states
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    RETURN  ${content}

Do Clean States
    @{content} =  Do Get States
    FOR  ${entity}  IN  @{content}
        Do Clean State  ${entity['entity_id']}
    END

Do Initialize State
    [Arguments]  ${entity}  ${state}
    Set Request Body To Dictionary  state=${state}
    Ask For Connection Keepalive
    Authenticate
    POST  /api/states/${entity}

Do Initialize States
    [Arguments]  &{states}
    FOR  ${entity}  IN  @{states.keys()}
        Do Initialize State  ${entity}  ${states['${entity}']}
    END

Do Check State
    [Arguments]  ${entity}  ${expected_state}
    ${actual_state} =  Do Get State  ${entity}
    Should Be Equal  ${actual_state}  ${expected_state}

Do Clean History
    Set Request Body To Dictionary  keep_days=${0}
    Ask For Connection Keepalive
    Authenticate
    POST  /api/services/recorder/purge

Do Clean States And History
    Do Clean States
    Do Clean History

Wait Until State Becomes
    [Arguments]  ${entity}  ${state}  ${timeout}=2s
    ${result} =  Run In Http Context
    ...    ${home_assistant_host}
    ...    Wait Until Keyword Succeeds  ${timeout}  0.01 s
    ...    Do Check State  ${entity}  ${state}
    RETURN  ${result}

Get States
    ${result} =  Run In Http Context
    ...    ${home_assistant_host}
    ...    Do Get States
    RETURN  ${result}

Clean States
    Run In Http Context  ${home_assistant_host}
    ...    Do Clean States

Clean States And History
    Run In Http Context  ${home_assistant_host}
    ...    Do Clean States And History

Initialize States
    [Arguments]  &{states}
    Run In Http Context  ${home_assistant_host}
    ...    Do Initialize States  &{states}
