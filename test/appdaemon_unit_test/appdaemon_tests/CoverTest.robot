*** Settings ***

Resource       resources/TestHarness.robot
Test Teardown  Cleanup Test Harness


*** Variables ***

${input_entity} =          sensor.target_position
${cover_entity} =          cover.test_cover
${position_entity} =       sensor.cover_position
${availablility_entity} =  sensor.cover_available
${mode_switch} =           input_select.test_cover_mode


*** Test Cases ***

Basic
    [Setup]  Initialize
    [Template]  Basic State Check
    open    ${100}
    closed  ${0}
    Open    ${100}
    Closed  ${0}
    OPEN    ${100}
    CLOSED  ${0}
    10      ${10}
    55      ${55}
    100     ${100}
    0       ${0}
    72      ${72}
    101     ${72}
    -1      ${72}
    foo     ${72}
    11      ${11}

Delay
    [Setup]  Initialize With Delay  ${1}
    Test Delay

Delay With Mode Switch
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Test Delay

Availability
    [Setup]  Initialize With Delay  ${1}
    Test Availability

Availability With Mode Switch
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Test Availability

Temporary Manual Mode
    [Setup]  Initialize With Delay  ${1}
    Test Temporary Manual Mode

Temporary Manual Mode With Mode Switch
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Test Temporary Manual Mode

Manual Mode From Stable To Auto
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    call_service  cover/set_cover_position
    ...    entity_id=cover.test_cover
    ...    position=${10}
    Schedule Call At  3 min
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${position_entity}  50  1 min 30 sec
    State Should Be  ${mode_switch}  stable
    State Should Change At  ${position_entity}  10  2 min
    State Should Be  ${mode_switch}  stable
    State Should Change At  ${position_entity}  50  3 min
    State Should Be  ${mode_switch}  stable

Manual Mode Availability Change
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service  cover/set_cover_position
    ...    entity_id=cover.test_cover
    ...    position=${10}
    Schedule Call At  4 min
    ...    set_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_state  ${availablility_entity}  on
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${position_entity}  50  1 min 30 sec
    State Should Change At  ${position_entity}  10  2 min 30 sec
    State Should Change At  ${position_entity}  50  6 min

Manual Mode State Change Auto
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service  cover/set_cover_position
    ...    entity_id=cover.test_cover
    ...    position=${10}
    Schedule Call At  4 min
    ...    set_state  ${input_entity}  open
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  auto
    Schedule Call At  6 min 10 sec
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  6 min 30 sec
    ...    call_service  cover/close_cover
    ...    entity_id=cover.test_cover
    Schedule Call At  7 min
    ...    set_state  ${input_entity}  75
    Schedule Call At  7 min 30 sec
    ...    select_option  ${mode_switch}  auto

    State Should Change At  ${position_entity}  50  1 min 30 sec
    State Should Change At  ${position_entity}  10  2 min 30 sec
    State Should Change At  ${position_entity}  100  6 min
    State Should Change At  ${position_entity}  0  6 min 30 sec
    State Should Change At  ${position_entity}  100  7 min 30 sec
    State Should Change At  ${position_entity}  75  8 min

Manual Mode State Change Stable
    [Setup]  Initialize With Delay  ${1}  mode_switch=${mode_switch}
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    select_option  ${mode_switch}  manual
    Schedule Call At  2 min 30 sec
    ...    call_service  cover/set_cover_position
    ...    entity_id=cover.test_cover
    ...    position=${10}
    Schedule Call At  4 min
    ...    set_state  ${input_entity}  open
    Schedule Call At  6 min
    ...    select_option  ${mode_switch}  stable
    Schedule Call At  6 min 30 sec
    ...    call_service  cover/close_cover
    ...    entity_id=cover.test_cover
    Schedule Call At  7 min
    ...    set_state  ${input_entity}  75

    State Should Change At  ${position_entity}  50  1 min 30 sec
    State Should Change At  ${position_entity}  10  2 min 30 sec
    State Should Change At  ${position_entity}  0  6 min 30 sec
    State Should Change At  ${position_entity}  75  8 min


*** Keywords ***

Basic State Check
    [Arguments]  ${input}  ${expected}
    Set State  ${input_entity}  ${input}
    State Should Be As  ${position_entity}  int  ${expected}

Test Delay
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    set_state  ${input_entity}  75
    Schedule Call At  2 min 30 sec
    ...    set_state  ${input_entity}  closed

    State Should Change At  ${position_entity}  50  1 min 30 sec
    State Should Change At  ${position_entity}  0  3 min 30 sec

Test Availability
    Schedule Call At  10 sec
    ...    set_state  ${availablility_entity}  off
    Schedule Call At  30 sec
    ...    set_state  ${input_entity}  50
    Schedule Call At  2 min
    ...    set_state  ${availablility_entity}  on
    Schedule Call At  3 min
    ...    set_state  ${input_entity}  open
    Schedule Call At  3 min 10 sec
    ...    set_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_state  ${availablility_entity}  on
    Schedule Call At  6 min
    ...    set_state  ${input_entity}  closed
    Schedule Call At  6 min 30 sec
    ...    set_state  ${availablility_entity}  off
    Schedule Call At  6 min 40 sec
    ...    set_state  ${availablility_entity}  on

    State Should Change At  ${position_entity}  50  2 min
    State Should Change At  ${position_entity}  100  5 min
    State Should Change At  ${position_entity}  0  7 min

Test Temporary Manual Mode
    Schedule Call At  1 min
    ...    set_state  ${input_entity}  50
    Schedule Call At  3 min
    ...    call_service  cover/set_cover_position
    ...    entity_id=cover.test_cover
    ...    position=${80}
    Schedule Call At  4 min
    ...    set_state  ${availablility_entity}  off
    Schedule Call At  5 min
    ...    set_state  ${availablility_entity}  on
    Schedule Call At  7 min
    ...    set_state  ${input_entity}  50
    Schedule Call At  8 min 30 sec
    ...    set_state  ${input_entity}  closed

    State Should Change At  ${position_entity}  50  2 min
    State Should Change At  ${position_entity}  80  3 min
    State Should Change At  ${position_entity}  0   9 min 30 sec

Initialize
    [Arguments]  &{args}
    Create Test Harness
    Set State  ${input_entity}  0
    Set State  ${availablility_entity}  on
    Set State  ${mode_switch}  auto
    Create App  test_cover  TestCover  test_cover
    ...    entity=${cover_entity}
    ...    position_entity=${position_entity}
    ...    available_entity=${availablility_entity}
    Create App  cover  CoverController  cover
    ...    expr=v.${input_entity}
    ...    target=${cover_entity}
    ...    &{args}

Initialize With Delay
    [Arguments]  ${minutes}  &{args}
    &{delay} =  Create Dictionary  minutes=${minutes}
    Initialize  delay=${delay}  &{args}
