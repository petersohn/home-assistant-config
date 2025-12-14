*** Settings ***

Library    HttpLibrary.HTTP
Library    Process
Library    Collections
Library    libraries/TypeUtil.py
Resource   resources/ErrorHandling.robot
Resource   resources/Http.robot
Variables  libraries/Directories.py


*** Variables ***

${test_arg}         This is a test


*** Keywords ***

Start AppDaemon
    Set Suite Variable  ${app_daemon_host}  127.0.0.1:${app_daemon_api_port}
    ...    children=True
    ${app_daemon_process} =  Start Process   ./appdaemon
    ...    --config      ${appdaemon_directory}
    ...    --tick        1
#     ...    --debug       DEBUG
    ...    stdout=${appdaemon_directory}/appdaemon.stdout
    ...    stderr=${appdaemon_directory}/appdaemon.stderr
    Set Test Variable    ${app_daemon_process}

Create Call Data
    [Arguments]  ${function}  ${result_type}  ${arg_types}  ${kwarg_types}
    ...          @{args}  &{kwargs}

    ${result} =  Create Dictionary
    ...    function=${function}
    ...    result_type=${result_type}
    ...    arg_types=${arg_types}
    ...    kwarg_types=${kwarg_types}
    ...    args=@{args}
    ...    kwargs=&{kwargs}
    RETURN  ${result}

Call Function
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${result_type} =  Extract From Dictionary  ${kwargs}  result_type
    ${arg_types} =  Extract From Dictionary  ${kwargs}  arg_types
    ${kwarg_types} =  Extract From Dictionary  ${kwargs}  kwarg_types
    ${content} =  Create Call Data  ${function}
    ...    ${result_type}  ${arg_types}  ${kwarg_types}
    ...    @{args}  &{kwargs}
    ${body} =  Stringify Json  ${content}
    Set Request Body  ${body}
    Ask For Connection Keepalive
    POST  /api/appdaemon/TestApp
    ${response} =  Get Response Body
    ${result} =  Parse Json  ${response}
    RETURN  ${result}

Log To AppDaemon
    [Arguments]  ${message}
    Call Function  log  ${message}

Get State
    [Arguments]  ${entity_id}  &{kwargs}
    ${value} =  Call Function  get_state  ${entity_id}  &{kwargs}
    RETURN  ${value}

State Should Be
    [Arguments]  ${entity_id}  ${expected_value}
    ${value} =  Get State  ${entity_id}
    Should Be Equal  ${value}  ${expected_value}

Attribute Should Be
    [Arguments]  ${entity_id}  ${attribute}  ${expected_value}
    ${value} =  Get State  ${entity_id}  attribute=${attribute}
    Should Be Equal  ${value}  ${expected_value}

State Should Not Be
    [Arguments]  ${entity_id}  ${not_expected_value}
    ${value} =  Get State  ${entity_id}
    Should Not Be Equal  ${value}  ${not_expected_value}

State Should Be As
    [Arguments]  ${entity_id}  ${type}  ${expected_value}
    ${value} =  Get State  ${entity_id}  result_type=${type}
    Should Be Equal  ${value}  ${expected_value}

Set State
    [Arguments]  ${entity_id}  ${value}  &{attributes}
    Call Function  set_state  ${entity_id}  state=${value}  attributes=${attributes}

Select Option
    [Arguments]  ${entity_id}  ${value}
    Call Function  select_option  ${entity_id}  ${value}

Set Value
    [Arguments]  ${entity_id}  ${value}
    Call Function  set_value  ${entity_id}  ${value}

Turn On
    [Arguments]  ${entity_id}
    Call Function  turn_on  ${entity_id}

Turn Off
    [Arguments]  ${entity_id}
    Call Function  turn_off  ${entity_id}

Turn On Or Off
    [Arguments]  ${entity_id}  ${state}
    Run Keyword If  '${state}' == 'on'
    ...    Turn On  ${entity_id}
    ...    ELSE
    ...    Turn Off  ${entity_id}

Watch Entities
    [Arguments]  @{entities}
    Call Function  watch_entities  ${entities}

Unwatch Entities
    Call Function  unwatch_entities

Get History
    ${result} =  Call Function  get_history
    RETURN  ${result}

Convert Expected History
    [Arguments]  @{expected}
    @{expected_pairs} =  Create List
    FOR  ${entity}  ${value}  IN  @{expected}
        @{pair} =  Create List  ${entity}  ${value}
        Append To List  ${expected_pairs}  ${pair}
    END
    RETURN  ${expected_pairs}

Check History
    [Arguments]  @{expected}
    ${expected_pairs} =  Convert Expected History  @{expected}
    ${actual} =  Get History
    Lists Should Be Equal  ${actual}  ${expected_pairs}

Should Have History
    [Arguments]  @{expected}
    ${expected_pairs} =  Convert Expected History  @{expected}
    ${result} =  Call Function  has_history  ${expected_pairs}
    Should Be True  ${result}

Wait For History
    [Arguments]  @{expected}
    Wait Until Keyword Succeeds  2 min  0.2 s
    ...    Should Have History  @{expected}

Check AppDaemon
    Critical Check  AppDaemon process failed to start
    ...    Process Should Be Running  ${app_daemon_process}
    ${result} =  Call Function  test  ${test_arg}
    Should Be Equal  ${result}  ${test_arg}

Wait For AppDaemon To Start
    Wait Until Keyword Succeeds  30 sec  0.5 sec
    ...    Run In Http Context  ${app_daemon_host}
    ...    Check AppDaemon

Stop AppDaemon
    Send Signal To Process  TERM  ${app_daemon_process}

Wait For AppDaemon To Stop
    Wait For Process  ${app_daemon_process}  timeout=10 sec  on_timeout=kill
    Process Should Be Stopped

Append And Check Mutex Graph
    ${mutex_graph} =  Run In Http Context  ${app_daemon_host}
    ...    Call Function  call_on_app  locker  get_global_graph
    Append Graph  ${global_mutex_graph}  ${mutex_graph}
    ${graph_str} =  Format Graph  ${mutex_graph}  Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${mutex_graph}
    Should Be Equal  ${deadlock}  ${False}

Apps Should Be Loaded
    [Arguments]  @{apps}
    ${result} =  Call Function  is_all_apps_loaded  ${apps}
    Should Be True  ${result}

Apps Should Be Unoaded
    [Arguments]  @{apps}
    ${result} =  Call Function  is_all_apps_unloaded  ${apps}
    Should Be True  ${result}

Schedule Call At State Change
    [Arguments]  ${entity}  ${value}  ${function}  @{args}  &{kwargs}
    Call Function  schedule_call_at_state_change
    ...    ${entity}  ${value}  ${function}  @{args}  &{kwargs}
