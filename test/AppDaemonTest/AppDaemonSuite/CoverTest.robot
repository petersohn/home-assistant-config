*** Settings ***

Resource       resources/Config.robot
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_entity} =   sensor.test_cover_position
${output_entity} =  input_number.cover_position


*** Test Cases ***

Basic
    [Setup]  Initialize  CoverBasic
    [Template]  Basic State Check
    open    100.0
    closed  0.0
    Open    100.0
    Closed  0.0
    OPEN    100.0
    CLOSED  0.0
    10      10.0
    55      55.0
    100     100.0
    0       0.0
    72      72.0
    101     72.0
    -1      72.0
    foo     72.0
    11      11.0


Delay
    [Setup]  Initialize  CoverDelay
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    set_sensor_state  ${input_entity}  75
    Schedule Call At  2 min 30 sec
    ...    set_sensor_state  ${input_entity}  closed
    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Change At  ${output_entity}  0.0  3 min 30 sec

*** Keywords ***

Basic State Check
    [Arguments]  ${input}  ${expected}
    Set State  ${input_entity}  ${input}
    State Should Be  ${output_entity}  ${expected}

Initialize
    [Arguments]  ${config}
    Clean States
    Initialize States
    ...    ${input_entity}=${Empty}
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  cover
    ${app_configs} =  Create List  TestApp  Cover  ${config}
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
