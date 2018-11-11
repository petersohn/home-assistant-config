*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${switch} =           input_boolean.test_switch
${switch_interval} =  input_boolean.test_switch2
${enabler1} =         test_enabler1
${enabler2} =         test_enabler2


*** Test Cases ***

Default Interval
    State Should Be  ${switch}  off
    Set Enabled State  ${enabler1}  enable
    Unblock For  1 min
    State Should Be  ${switch}  off
    Set Enabled State  ${enabler2}  enable
    Unblock For  10 sec
    State Should Be  ${switch}  off
    Unblock For  50 sec
    State Should Be  ${switch}  on
    Set Enabled State  ${enabler1}  disable
    Unblock For  1 min
    State Should Be  ${switch}  off


Custom Interval
    State Should Be  ${switch_interval}  off
    Set Enabled State  ${enabler1}  enable
    Set Enabled State  ${enabler2}  enable
    Unblock For  1 min
    State Should Be  ${switch_interval}  on


*** Keywords ***

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${switch_interval}=off
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  enabled_switch  auto_switch  enabler
    ${app_configs} =  Create List  TestApp  EnabledSwitch
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
