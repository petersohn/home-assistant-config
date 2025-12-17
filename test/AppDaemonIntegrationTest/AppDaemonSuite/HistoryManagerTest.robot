*** Settings ***

Library   DateTime
Library   libraries/history_util.py
Resource  resources/AppDaemon.robot
Resource  resources/Config.robot
Resource  resources/Http.robot
Test Teardown  Cleanup Apps Configs


*** Variables ***

${sensor}    sensor.history_test


*** Test Cases ***

Load History
    [Setup]  Initialize
    Set State  ${sensor}  12
    Set State  ${sensor}  3
    Set State  ${sensor}  91
    Set State  ${sensor}  -32
    Wait For History Size  ${sensor}  ${5}
    Load Apps Configs  HistoryManager
    Set State  ${sensor}  23
    Set State  ${sensor}  99

    History Should Be  test_history_manager
    ...    ${0.0}  ${12.0}  ${3.0}  ${91.0}  ${-32.0}  ${23.0}  ${99.0}


*** Keywords ***

Get History Size
    [Arguments]  ${entity_id}
    Ask For Connection Keepalive
    Authenticate
    ${now} =  Get Current Date
    ${begin_date} =  Subtract Time From Date  ${now}  1h
    ...    result_format=%Y-%m-%dT%H:%M:%S
    GET  /api/history/period/${begin_date}?filter_entity_id=${entity_id}
    ${body} =  Get Response Body
    ${content} =  Parse Json  ${body}
    ${length} =  Get Length  ${content[0]}
    RETURN  ${length}

History Size Should Be
    [Arguments]  ${entity_id}  ${expected}
    ${size} =  Get History Size  ${entity_id}
    Should Be Equal  ${size}  ${expected}

Wait For History Size
    [Arguments]  ${entity_id}  ${expected}
    Run In Http Context  ${home_assistant_host}
    ...    Wait Until Keyword Succeeds  15s  0.2s
    ...    History Size Should Be  ${entity_id}  ${expected}

History Should Be
    [Arguments]  ${app}  @{expected}
    ${history} =  Call Function  call_on_app  ${app}  get_history
    ${actual} =  Convert History Output  ${history}
    Lists Should Be Equal  ${actual}  ${expected}

Initialize
    Initialize States  ${sensor}=0
    Initialize Apps Configs
