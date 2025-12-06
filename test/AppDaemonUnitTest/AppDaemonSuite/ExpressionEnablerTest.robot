*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot


*** Variables ***

${input_binary1} =  binary_sensor.test_input1
${input_binary2} =  binary_sensor.test_input2
${input_sensor1} =  sensor.test_input1
${input_sensor2} =  sensor.test_input2


*** Test Cases ***

Enablers
    [Template]  Test Enablers
    ${False}  ${False}
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${False}  enablers_or=${False}
    ${False}  ${True}
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${False}  enablers_or=${True}
    ${True}   ${False}
    ...    enablers_and=${False}  enablers_nand=${True}
    ...    enablers_and_not=${True}  enablers_or=${True}
    ${True}   ${True}
    ...    enablers_and=${True}  enablers_nand=${False}
    ...    enablers_and_not=${False}  enablers_or=${True}

Numeric Sensors
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

Alphanumeric Sensors
    [Template]  Test Sensors
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
    ${False}  off
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${False}
    ${False}  on
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${True}
    ${True}  off
    ...    enabler_and_binary_and=${False}  enabler_and_binary_or=${True}
    ${True}  on
    ...    enabler_and_binary_and=${True}   enabler_and_binary_or=${True}

*** Keywords ***

Create Expression Enabler
    [Arguments]  ${name}  ${expr}
    ${app} =  Create App  enabler  ExpressionEnabler  ${name}  expr=${expr}
    RETURN  ${app}

Check Expected States
    [Arguments]  &{expected_states}
    FOR  ${name}  ${value}  IN  &{expected_states}
        ${app} =  Get App  ${name}
        Enabled State Should Be  ${app}  ${value}
    END

Test Enablers
    [Arguments]  ${enabler1_state}  ${enabler2_state}  &{expected_states}
    [Teardown]  Cleanup Test Harness
    Create Test Harness
    Create App  enabler  ScriptEnabler  enabler1
    ...    initial=${enabler1_state}
    Create App  enabler  ScriptEnabler  enabler2
    ...    initial=${enabler2_state}
    Create Expression Enabler  enablers_and  e.enabler1 and e.enabler2
    Create Expression Enabler  enablers_nand  not (e.enabler1 and e.enabler2)
    Create Expression Enabler  enablers_and_not  e.enabler1 and not e.enabler2
    Create Expression Enabler  enablers_or  e.enabler1 or e.enabler2

    Check Expected States  &{expected_states}

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  &{expected_states}
    [Teardown]  Cleanup Test Harness
    Create Test Harness
    Set State  ${input_sensor1}  ${sensor1}
    Set State  ${input_sensor2}  ${sensor2}
    Create Expression Enabler  value_less  v.${input_sensor1} < v.${input_sensor2}
    Create Expression Enabler  value_equal  v.${input_sensor1} == v.${input_sensor2}

    Check Expected States  &{expected_states}

Test Binary Sensors
    [Arguments]  ${sensor1}  ${sensor2}  &{expected_states}
    [Teardown]  Cleanup Test Harness
    Create Test Harness
    Set State  ${input_binary1}  ${sensor1}
    Set State  ${input_binary2}  ${sensor2}
    Create Expression Enabler  binary_and  v.${input_binary1} and v.${input_binary2}
    Create Expression Enabler  binary_or  v.${input_binary1} or v.${input_binary2}

    Check Expected States  &{expected_states}

Test Enabler And Binary Sensor
    [Arguments]  ${enabler}  ${sensor}  &{expected_states}
    [Teardown]  Cleanup Test Harness
    Create Test Harness
    Create App  enabler  ScriptEnabler  enabler
    ...    initial=${enabler}
    Set State  ${input_binary1}  ${sensor}
    Create Expression Enabler  enabler_and_binary_and
    ...    e.enabler and v.${input_binary1}
    Create Expression Enabler  enabler_and_binary_or
    ...    e.enabler or v.${input_binary1}

    Check Expected States  &{expected_states}
