*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${name} =    test_history_manager
${entity} =  sensor.test_sensor
${enabler} =  test_history_enabler


*** Test Cases ***

Get History
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  2
    Unblock For  1 min
    Set State  ${entity}  3
    Unblock For  1 min
    Set State  ${entity}  0
    History Should Be  ${EMPTY}  0  3  2  3  0
    # Since there is no time travel in HASS, initial elements happen in the future
    Limited History Should Be  65 s  ${EMPTY}  0  3  0

Old History Elements Are Removed
    Set State  ${entity}  20
    Unblock For  20 min
    Set State  ${entity}  13
    Unblock For  20 min
    Set State  ${entity}  1
    Unblock For  20 min
    Set State  ${entity}  6
    Unblock For  21 min
    Set State  ${entity}  54
    History Should Be  ${EMPTY}  0  1  6  54

History Enabler
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  1 min
    Set State  ${entity}  4
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  1 min
    Set State  ${entity}  3
    Enabled State Should Be  ${enabler}  ${True}
    Unblock For  1 min
    Set State  ${entity}  4
    Enabled State Should Be  ${enabler}  ${False}
    Unblock For  3 min 30 s
    Set State  ${entity}  1
    Enabled State Should Be  ${enabler}  ${True}
    Unblock For  4 min
    Enabled State Should Be  ${enabler}  ${False}


*** Keywords ***

Get Values
    [Arguments]  ${interval}=${None}
    [Return]  ${result}

Should Be Loaded
    ${result} =  Call Function  call_on_app  ${name}  is_loaded
    Should Be True  ${result}

History Should Be
    [Arguments]  @{expected_values}  &{kwargs}
    ${values} =  Call Function  call_on_app  ${name}  get_values  &{kwargs}
    Should Be Equal  ${values}  ${expected_values}

Limited History Should Be
    [Arguments]  ${interval}  @{expected_values}
    ${arg_types} =  Create List  ${None}  ${None}  convert_timedelta
    ${values} =  Call Function  call_on_app  ${name}
    ...   get_values  ${interval}  arg_types=${arg_types}
    Should Be Equal  ${values}  ${expected_values}

Initialize
    Clean States And History
    Initialize States
    ...    ${entity}=${0}
    ${apps} =  Create List  TestApp  history  enabler
    ${app_configs} =  Create List  TestApp  HistoryManager
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
    Wait Until Keyword Succeeds  30 sec  1 sec  Should Be Loaded
