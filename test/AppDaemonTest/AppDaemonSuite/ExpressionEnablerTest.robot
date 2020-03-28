*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_binary1} =  binary_sensor.test_input1
${input_binary2} =  binary_sensor.test_input2
${input_sensor1} =  sensor.test_input1
${input_sensor2} =  sensor.test_input2


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

Sensors
    [Template]  Test Sensors
    ${-1}  ${-1}
    ...    value_less=${False}  value_equal=${True}
    ${-1}  ${0}
    ...    value_less=${True}   value_equal=${False}
    ${-1}  ${5}
    ...    value_less=${True}   value_equal=${False}
    ${-1}  ${10}
    ...    value_less=${True}   value_equal=${False}
    ${0}  ${-1}
    ...    value_less=${False}  value_equal=${False}
    ${0}  ${0}
    ...    value_less=${False}  value_equal=${True}
    ${0}  ${5}
    ...    value_less=${True}   value_equal=${False}
    ${0}  ${10}
    ...    value_less=${True}   value_equal=${False}
    ${5}  ${-1}
    ...    value_less=${False}  value_equal=${False}
    ${5}  ${0}
    ...    value_less=${False}  value_equal=${False}
    ${5}  ${5}
    ...    value_less=${False}  value_equal=${True}
    ${5}  ${10}
    ...    value_less=${True}   value_equal=${False}
    ${10}  ${-1}
    ...    value_less=${False}  value_equal=${False}
    ${10}  ${0}
    ...    value_less=${False}  value_equal=${False}
    ${10}  ${5}
    ...    value_less=${False}  value_equal=${False}
    ${10}  ${10}
    ...    value_less=${False}  value_equal=${True}

    a  a
    ...    value_less=${False}  value_equal=${True}
    a  b
    ...    value_less=${True}   value_equal=${False}
    b  a
    ...    value_less=${False}  value_equal=${False}
    a  aa
    ...    value_less=${True}   value_equal=${False}
    aa  a
    ...    value_less=${False}  value_equal=${False}
    aa  aa
    ...    value_less=${False}  value_equal=${True}


Binary Sensors
    [Template]  Test Binary Sensors
    off  off
    ...    binary_and=${False}  binary_or=${False}
    off  on
    ...    binary_and=${False}  binary_or=${True}
    on  off
    ...    binary_and=${False}  binary_or=${True}
    on  on
    ...    binary_and=${True}   binary_or=${True}

Enabler And Binary Sensor
    [Template]  Test Enabler And Binary Sensor
    disable  off
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${False}
    disable  on
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${True}
    enable  off
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${True}
    enable  on
    ...    enabler_and_binary_and=${True}   enabler_and_binary_or=${True}

*** Keywords ***

Check Expected States
    [Arguments]  &{expected_states}
    :FOR  ${name}  IN  @{expected_states.keys()}
    \   Enabled State Should Be  ${name}  ${expected_states['${name}']}

Test Enablers
    [Arguments]  ${enabler1}  ${enabler2}  &{expected_states}
    Set Enabled State  enabler1  ${enabler1}
    Set Enabled State  enabler2  ${enabler2}
    Unblock For  ${appdaemon_interval}
    Check Expected States  &{expected_states}

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  &{expected_states}
    Set State  ${input_sensor1}  ${sensor1}
    Set State  ${input_sensor2}  ${sensor2}
    Check Expected States  &{expected_states}

Test Binary Sensors
    [Arguments]  ${sensor1}  ${sensor2}  &{expected_states}
    Set State  ${input_binary1}  ${sensor1}
    Set State  ${input_binary2}  ${sensor2}
    Check Expected States  &{expected_states}

Test Enabler And Binary Sensor
    [Arguments]  ${enabler}  ${sensor}  &{expected_states}
    Set Enabled State  enabler1  ${enabler}
    Set State  ${input_binary1}  ${sensor}
    Unblock For  ${appdaemon_interval}
    Check Expected States  &{expected_states}

Initialize
    [Arguments]  ${start_time}  ${start_date}=${default_start_date}
    ...          ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${input_binary1}=off
    ...    ${input_binary2}=off
    ...    ${input_sensor1}=0
    ...    ${input_sensor2}=0
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  enabler
    ${app_configs} =  Create List  TestApp  ExpressionEnabler
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${start_date}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}

