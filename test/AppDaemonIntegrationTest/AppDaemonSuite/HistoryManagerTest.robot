*** Settings ***

Library   DateTime
Library   libraries/history_util.py
Resource  resources/AppDaemon.robot
Resource  resources/Config.robot
Resource  resources/Http.robot
Test Setup  Initialize
Test Teardown  Cleanup Apps Configs


*** Variables ***

${sensor}    sensor.history_test
${sensor1}   sensor.test_sensor1
${sensor2}   sensor.test_sensor2


*** Test Cases ***

Load History
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

Change Tracker
    Set State  ${sensor1}  6  foo=1
    Set State  ${sensor2}  6  foo=1
    Sleep  0.1
    Set State  ${sensor1}  8  foo=2
    Set State  ${sensor2}  6  foo=2
    Load Apps Configs  ChangeTrackers
    Last Changed And Last Updated Should Be The Same  tracker1
    Should Be Updated After Changed  tracker2
    Set State  ${sensor1}  8  foo=3
    Set State  ${sensor2}  8  foo=3
    Should Be Updated After Changed  tracker1
    Last Changed And Last Updated Should Be The Same  tracker2

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

Get Last Changed
    [Arguments]  ${app}
    ${result} =  Call Function  call_on_app  ${app}  last_changed
    ...    result_type=datestr
    RETURN  ${result}

Get Last Updated
    [Arguments]  ${app}
    ${result} =  Call Function  call_on_app  ${app}  last_updated
    ...    result_type=datestr
    RETURN  ${result}

Last Changed And Last Updated Should Be The Same
    [Arguments]  ${app}
    ${last_changed} =  Get Last Changed  ${app}
    ${last_updated} =  Get Last Updated  ${app}
    Should Be Equal  ${last_changed}  ${last_updated}

Should Be Updated After Changed
    [Arguments]  ${app}
    ${last_changed} =  Get Last Changed  ${app}
    ${last_updated} =  Get Last Updated  ${app}
    ${difference} =  Subtract Date From Date  ${last_updated}  ${last_changed}
    ...    result_format=number
    Should Be True  ${difference} > 0


Initialize
    Initialize States  ${sensor}=0  ${sensor1}=0  ${sensor2}=0
    Initialize Apps Configs
