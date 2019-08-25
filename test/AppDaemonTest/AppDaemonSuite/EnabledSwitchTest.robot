*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${switch1} =  input_boolean.test_switch
${switch2} =  input_boolean.test_switch2
${enabler} =  test_enabler


*** Test Cases ***

Switch States
    State Should Be  ${switch1}  off
    State Should Be  ${switch2}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${switch1}  on
    State Should Be  ${switch2}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${switch1}  off
    State Should Be  ${switch2}  off


*** Keywords ***

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${switch1}=off
    ...    ${switch2}=off
    ${apps} =  Create List  TestApp  enabled_switch  auto_switch  enabler
    ${app_configs} =  Create List  TestApp  EnabledSwitch
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
