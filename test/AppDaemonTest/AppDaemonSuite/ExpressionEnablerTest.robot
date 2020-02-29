*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_binary} =  binary_sensor.test_input
${input_sensor} =  sensor.test_input


*** Test Cases ***

Enablers
    [Template]  Test Enablers
    disable  disable
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${False}  enablers_or=${False}
    disable  enable
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${False}  enablers_or=${True}
    enable   disable
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${True}  enablers_or=${True}
    enable   enable
    ...    enablers_and=${True}  enablers_nand=${False}
    ...    enablers_and_not=${False}  enablers_or=${True}

*** Keywords ***

Test Enablers
    [Arguments]  ${enabler1}  ${enabler2}  &{expected_states}
    Set Enabled State  enabler1  ${enabler1}
    Set Enabled State  enabler2  ${enabler2}
    Unblock For  ${appdaemon_interval}
    :FOR  ${name}  IN  @{expected_states.keys()}
    \   Enabled State Should Be  ${name}  ${expected_states['${name}']}

Initialize
    [Arguments]  ${start_time}  ${start_date}=${default_start_date}
    ...          ${suffix}=${Empty}
    Clean States
#     Initialize States
#     ...    ${input_binary}=off
#     ...    ${input_sensor}=0
    ${apps} =  Create List  TestApp  locker  mutex_graph  enabler
    ${app_configs} =  Create List  TestApp  ExpressionEnabler
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${start_date}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}

