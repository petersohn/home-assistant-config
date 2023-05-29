*** Settings ***

Resource       resources/Config.robot
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_entity} =          sensor.test_cover_position
${output_entity} =         input_number.cover_position
${availablility_entity} =  sensor.cover_available
${mode_switch} =           input_select.test_cover_mode


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
    Test Delay

Delay With Mode Switch
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Test Delay

Availability
    [Setup]  Initialize  CoverDelay
    Test Availability

Availability With Mode Switch
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Test Availability

Temporary Manual Mode
    [Setup]  Initialize  CoverDelay
    Test Temporary Manual Mode

Temporary Manual Mode With Mode Switch
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Test Temporary Manual Mode

Manual Mode From Temp To Auto
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    call_service_  cover/set_cover_position  ${output_entity}  10.0
    ...    entity_id=cover.test_cover
    ...    position=10
    Schedule Call At  3 min
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Be  ${mode_switch}  auto
    State Should Change At  ${output_entity}  10.0  2 min
    Wait For State  ${mode_switch}  temp
    State Should Change At  ${output_entity}  50.0  3 min
    State Should Be  ${mode_switch}  auto

Manual Mode Availability Change
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service_  cover/set_cover_position  ${output_entity}  10.0
    ...    entity_id=cover.test_cover
    ...    position=10
    Schedule Call At  4 min
    ...    set_sensor_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_sensor_state  ${availablility_entity}  on
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Change At  ${output_entity}  10.0  2 min 30 sec
    State Should Change At  ${output_entity}  50.0  6 min

Manual Mode State Change Auto
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service_  cover/set_cover_position  ${output_entity}  10.0
    ...    entity_id=cover.test_cover
    ...    position=10
    Schedule Call At  4 min
    ...    set_sensor_state  ${input_entity}  open
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  auto
    Schedule Call At  6 min 10 sec
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  6 min 30 sec
    ...    call_service_  cover/close_cover  ${output_entity}  0.0
    ...    entity_id=cover.test_cover
    Schedule Call At  7 min
    ...    set_sensor_state  ${input_entity}  75
    Schedule Call At  7 min 30 sec
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Change At  ${output_entity}  10.0  2 min 30 sec
    State Should Change At  ${output_entity}  100.0  6 min
    State Should Change At  ${output_entity}  0.0  6 min 30 sec
    State Should Change At  ${output_entity}  100.0  7 min 30 sec
    State Should Change At  ${output_entity}  75.0  8 min

Manual Mode State Change Temp
    [Setup]  Initialize  CoverDelayWithModeSwitch
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service_  cover/set_cover_position  ${output_entity}  10.0
    ...    entity_id=cover.test_cover
    ...    position=10
    Schedule Call At  4 min
    ...    set_sensor_state  ${input_entity}  open
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  temp
    Schedule Call At  6 min 30 sec
    ...    call_service_  cover/close_cover  ${output_entity}  0.0
    ...    entity_id=cover.test_cover
    Schedule Call At  7 min
    ...    set_sensor_state  ${input_entity}  75

    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Change At  ${output_entity}  10.0  2 min 30 sec
    State Should Change At  ${output_entity}  0.0  6 min 30 sec
    State Should Change At  ${output_entity}  75.0  8 min


*** Keywords ***

Basic State Check
    [Arguments]  ${input}  ${expected}
    Set State  ${input_entity}  ${input}
    State Should Be  ${output_entity}  ${expected}

Test Delay
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    set_sensor_state  ${input_entity}  75
    Schedule Call At  2 min 30 sec
    ...    set_sensor_state  ${input_entity}  closed

    State Should Change At  ${output_entity}  50.0  1 min 30 sec
    State Should Change At  ${output_entity}  0.0  3 min 30 sec

Test Availability
    Schedule Call At  10 sec
    ...    set_sensor_state  ${availablility_entity}  off
    Schedule Call At  30 sec
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    set_sensor_state  ${availablility_entity}  on
    Schedule Call At  3 min
    ...    set_sensor_state  ${input_entity}  open
    Schedule Call At  3 min 10 sec
    ...    set_sensor_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_sensor_state  ${availablility_entity}  on
    Schedule Call At  6 min
    ...    set_sensor_state  ${input_entity}  closed
    Schedule Call At  6 min 30 sec
    ...    set_sensor_state  ${availablility_entity}  off
    Schedule Call At  6 min 40 sec
    ...    set_sensor_state  ${availablility_entity}  on

    State Should Change At  ${output_entity}  50.0  2 min
    State Should Change At  ${output_entity}  100.0  5 min
    State Should Change At  ${output_entity}  0.0  7 min

Test Temporary Manual Mode
    Schedule Call At  1 min
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  3 min
    ...    call_service_  cover/set_cover_position  ${output_entity}  80.0
    ...    entity_id=cover.test_cover
    ...    position=80
    Schedule Call At  4 min
    ...    set_sensor_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_sensor_state  ${availablility_entity}  on
    Schedule Call At  7 min
    ...    set_sensor_state  ${input_entity}  50
    Schedule Call At  8 min 30 sec
    ...    set_sensor_state  ${input_entity}  closed

    State Should Change At  ${output_entity}  50.0  2 min
    State Should Change At  ${output_entity}  80.0  3 min
    State Should Change At  ${output_entity}  0.0   9 min 30 sec

Initialize
    [Arguments]  ${config}
    Clean States
    Initialize States
    ...    ${input_entity}=${Empty}
    ...    ${availablility_entity}=on
    ${apps} =  Create List  TestApp  locker  mutex_graph  expression  cover
    ${app_configs} =  Create List  TestApp  Cover  ${config}
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
    Set Value  ${output_entity}  ${0}
    Select Option  ${mode_switch}  auto
