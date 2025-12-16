*** Settings ***

Library   libraries/history_util.py
Resource  resources/AppDaemon.robot
Resource  resources/Config.robot
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
    Sleep  5
    Load Apps Configs  HistoryManager
    Set State  ${sensor}  23
    Set State  ${sensor}  99

    History Should Be  test_history_manager
    ...    ${0.0}  ${12.0}  ${3.0}  ${91.0}  ${-32.0}  ${23.0}  ${99.0}


*** Keywords ***

History Should Be
    [Arguments]  ${app}  @{expected}
    ${history} =  Call Function  call_on_app  ${app}  get_history
    ${actual} =  Convert History Output  ${history}
    Lists Should Be Equal  ${actual}  ${expected}

Initialize
    Initialize States  ${sensor}=0
    Initialize Apps Configs
