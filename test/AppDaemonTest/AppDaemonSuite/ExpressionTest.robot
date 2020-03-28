*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/DateTime.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_sensor1} =  sensor.test_input1
${input_sensor2} =  sensor.test_input2
${output_sensor} =  sensor.test_output
${now_sensor} =     sensor.now
${args_sensor} =    sensor.args


*** Test Cases ***

Sensors
    [Template]  Test Sensors
    ${0}   ${0}   ${0}
    ${0}   ${13}  ${13}
    ${63}  ${-8}  ${55}
    ${-7}  ${5}   ${-2}

Get Now
    Unblock Until  00:01:00
    ${result} =  Get State  ${now_sensor}
    Date Should Equal Time  ${result}  ${default_start_date}  00:01:00
    Unblock Until  00:01:30
    ${result} =  Get State  ${now_sensor}
    Date Should Equal Time  ${result}  ${default_start_date}  00:01:30
    Unblock Until  01:12:20
    ${result} =  Get State  ${now_sensor}
    Date Should Equal Time  ${result}  ${default_start_date}  01:12:20

Args
    [Template]  Test Args
    ${0}  c  firstbaz
    ${1}  a  secondfoo
    ${2}  b  thirdbar

*** Keywords ***

Check Expected States
    [Arguments]  ${type}  &{expected_states}
    :FOR  ${name}  IN  @{expected_states.keys()}
    \   State Should Be As  ${name}  ${type}  ${expected_states['${name}']}

Test States
    [Arguments]  ${sensor1}  ${sensor2}  ${type}  &{expected_states}
    Set State  ${input_sensor1}  ${sensor1}
    Set State  ${input_sensor2}  ${sensor2}
    Check Expected States  ${type}  &{expected_states}

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  Int  ${output_sensor}=${expected_result}

Test Args
    [Arguments]  ${sensor1}  ${sensor2}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  str  ${args_sensor}=${expected_result}

Initialize
    [Arguments]  ${start_time}  ${start_date}=${default_start_date}
    ...          ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${input_sensor1}=0
    ...    ${input_sensor2}=0
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression
    ${app_configs} =  Create List  TestApp  Expression
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${start_date}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}
