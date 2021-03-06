*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/DateTime.robot
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_sensor1} =  sensor.test_input1
${input_sensor2} =  sensor.test_input2
${output_sensor} =  sensor.test_output


*** Test Cases ***

Sensors
    [Setup]  Initialize  00:00:00  ExpressionAdd
    [Template]  Test Sensors
    ${0}   ${0}   Int  ${0}
    ${0}   ${13}  Int  ${13}
    ${63}  ${-8}  Int  ${55}
    ${-7}  ${5}   Int  ${-2}
    foo    bar    str  foobar

Binary Sensors
    [Setup]  Initialize  00:00:00  ExpressionBinary
    [Template]  Test Sensors
    ${0}   ${1}   str  off
    ${1}   ${0}   str  on
    ${0}   ${0}   str  off
    ${5}   ${10}  str  off
    ${10}  ${5}   str  on
    foo    bar    str  on
    bar    foo    str  off
    bar    bar    str  off

Attributes
    [Setup]  Initialize  00:00:00  ExpressionAttribute
    [Template]  Test Attributes
    ${0}   ${0}   Int  ${0}
    ${0}   ${13}  Int  ${13}
    ${63}  ${-8}  Int  ${55}
    ${-7}  ${5}   Int  ${-2}
    foo    bar    str  foobar

Get Now
    [Setup]  Initialize  00:00:00  ExpressionNow
    Unblock Until  00:01:00
    ${result} =  Get State  ${output_sensor}
    Times Should Match  ${result}  00:01:00
    Unblock Until  00:01:30
    ${result} =  Get State  ${output_sensor}
    Times Should Match  ${result}  00:01:30
    Unblock Until  01:12:20
    ${result} =  Get State  ${output_sensor}
    Times Should Match  ${result}  01:12:20

Args
    [Setup]  Initialize  00:00:00  ExpressionArgs
    [Template]  Test Args
    ${0}  c  firstbaz
    ${1}  a  secondfoo
    ${2}  b  thirdbar


Changes
    [Setup]  Initialize  00:00:00  ExpressionChange
    Unblock Until  00:01:00
    Set State  ${input_sensor1}  1  foo=bar
    Unblock For  ${appdaemon_interval}
    State Should Be As  ${output_sensor}  str  00:01:00 00:01:00
    Unblock Until  00:01:30
    Set State  ${input_sensor1}  1  foo=baz
    Unblock For  ${appdaemon_interval}
    State Should Be As  ${output_sensor}  str  00:01:00 00:01:30


*** Keywords ***

Test States
    [Arguments]  ${sensor1}  ${sensor2}  ${type}  ${expected_result}
    Set State  ${input_sensor1}  ${sensor1}
    Set State  ${input_sensor2}  ${sensor2}
    State Should Be As  ${output_sensor}  ${type}  ${expected_result}

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  ${type}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  ${type}  ${expected_result}

Test Args
    [Arguments]  ${sensor1}  ${sensor2}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  str  ${expected_result}

Test Attributes
    [Arguments]  ${attr1}  ${attr2}  ${type}  ${expected_result}
    Set State  ${input_sensor_1}  ${0}  attr1=${attr1}  attr2=${attr2}
    State Should Be As  ${output_sensor}  ${type}  ${expected_result}

Initialize
    [Arguments]  ${start_time}  @{configs}
    Clean States
    Initialize States
    ...    ${input_sensor1}=0
    ...    ${input_sensor2}=0
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  history
    ${app_configs} =  Create List  TestApp  @{configs}
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${default_start_date}
    Unblock For  ${appdaemon_interval}
