*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_sensor1} =  sensor.test_input1
${input_sensor2} =  sensor.test_input2
${output_sensor} =  sensor.test_output


*** Test Cases ***

Sensors
    [Template]  Test Sensors
    ${0}   ${0}   ${0}
    ${0}   ${13}  ${13}
    ${63}  ${-8}  ${55}
    ${-7}  ${5}   ${-2}

*** Keywords ***

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  ${expected_output}
    Set State  ${input_sensor1}  ${sensor1}
    Set State  ${input_sensor2}  ${sensor2}
    State Should Be As  ${output_sensor}  Int  ${expected_output}

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

