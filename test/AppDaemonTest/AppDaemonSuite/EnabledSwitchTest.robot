*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Teardown  Cleanup AppDaemon


*** Variables ***

${switch1} =  input_boolean.test_switch
${switch2} =  input_boolean.test_switch2
${enabler} =  test_enabler


*** Test Cases ***

Start With Off
    [Setup]  Initialize  EnabledSwitchDefaultOff
    State Should Be  ${switch1}  off
    State Should Be  ${switch2}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${switch1}  on
    State Should Be  ${switch2}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${switch1}  off
    State Should Be  ${switch2}  off

Start With On
    [Setup]  Initialize  EnabledSwitchDefaultOn
    State Should Be  ${switch1}  on
    State Should Be  ${switch2}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${switch1}  off
    State Should Be  ${switch2}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${switch1}  on
    State Should Be  ${switch2}  on


*** Keywords ***

Initialize
    [Arguments]  ${config}
    Clean States
    Initialize States
    ...    ${switch1}=off
    ...    ${switch2}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  enabled_switch
    ...                     auto_switch  enabler
    ${app_configs} =  Create List  TestApp  ${config}
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
