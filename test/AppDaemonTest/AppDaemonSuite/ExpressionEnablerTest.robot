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
    enablers_and      disable  disable  ${False}
    enablers_and      disable  enable   ${False}
    enablers_and      enable   disable  ${False}
    enablers_and      enable   enable   ${True}
    enablers_nand     disable  disable  ${True}
    enablers_nand     disable  enable   ${True}
    enablers_nand     enable   disable  ${True}
    enablers_nand     enable   enable   ${False}
    enablers_and_not  disable  disable  ${False}
    enablers_and_not  disable  enable   ${False}
    enablers_and_not  enable   disable  ${True}
    enablers_and_not  enable   enable   ${False}
    enablers_or       disable  disable  ${False}
    enablers_or       disable  enable   ${True}
    enablers_or       enable   disable  ${True}
    enablers_or       enable   enable   ${True}

*** Keywords ***

Test Enablers
    [Arguments]  ${name}  ${enabler1}  ${enabler2}  ${expected_state}
    Set Enabled State  enabler1  ${enabler1}
    Set Enabled State  enabler2  ${enabler2}
    Unblock For  ${appdaemon_interval}
    Enabled State Should Be  ${name}  ${expected_state}

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

