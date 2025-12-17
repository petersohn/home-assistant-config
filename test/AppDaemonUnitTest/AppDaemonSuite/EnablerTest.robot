*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot
Library        Collections


*** Variables ***

${test_input} =  sensor.test_input
${test_switch} =  input_boolean.test_switch

@{values} =  foo  bar


*** Test Cases ***

Script Enabler
    [Template]  Test Script Enabler
    ${None}   ${True}
    ${True}   ${True}
    ${False}  ${False}


Value Enabler
    [Template]  Test Value Enabler
    # class       value    expected_state
    ValueEnabler  off      ${False}        value=on
    ValueEnabler  on       ${True}         value=on
    ValueEnabler  off      ${True}         value=off
    ValueEnabler  on       ${False}        value=off
    ValueEnabler  foo      ${True}         values=${values}
    ValueEnabler  bar      ${True}         values=${values}
    ValueEnabler  foobar   ${False}        values=${values}
    ValueEnabler  ${0}     ${False}        values=${values}
    ValueEnabler  ${100}   ${False}        values=${values}
    RangeEnabler  ${-100}  ${False}        min=${10}  max=${20}
    RangeEnabler  ${0}     ${False}        min=${10}  max=${20}
    RangeEnabler  ${9}     ${False}        min=${10}  max=${20}
    RangeEnabler  ${10}    ${True}         min=${10}  max=${20}
    RangeEnabler  ${15}    ${True}         min=${10}  max=${20}
    RangeEnabler  ${20}    ${True}         min=${10}  max=${20}
    RangeEnabler  ${21}    ${False}        min=${10}  max=${20}
    RangeEnabler  ${100}   ${False}        min=${10}  max=${20}
    RangeEnabler  ${-100}  ${False}        min=${15}
    RangeEnabler  ${0}     ${False}        min=${15}
    RangeEnabler  ${14}    ${False}        min=${15}
    RangeEnabler  ${15}    ${True}         min=${15}
    RangeEnabler  ${16}    ${True}         min=${15}
    RangeEnabler  ${100}   ${True}         min=${15}
    RangeEnabler  ${-100}  ${True}         max=${15}
    RangeEnabler  ${0}     ${True}         max=${15}
    RangeEnabler  ${14}    ${True}         max=${15}
    RangeEnabler  ${15}    ${True}         max=${15}
    RangeEnabler  ${16}    ${False}        max=${15}
    RangeEnabler  ${100}   ${False}        max=${15}

Date Enabler
    [Template]  Test Date Enabler
    # start_date    expected_state
    2018-01-01      ${False}       begin=03-11  end=03-11
    2018-03-10      ${False}       begin=03-11  end=03-11
    2018-03-11      ${True}        begin=03-11  end=03-11
    2018-03-12      ${False}       begin=03-11  end=03-11
    2018-12-31      ${False}       begin=03-11  end=03-11
    2025-03-11      ${True}        begin=03-11  end=03-11
    2025-03-12      ${False}       begin=03-11  end=03-11
    2018-01-01      ${False}       begin=05-01  end=10-06
    2018-04-30      ${False}       begin=05-01  end=10-06
    2018-05-01      ${True}        begin=05-01  end=10-06
    2018-05-02      ${True}        begin=05-01  end=10-06
    2018-10-05      ${True}        begin=05-01  end=10-06
    2018-10-06      ${True}        begin=05-01  end=10-06
    2018-10-07      ${False}       begin=05-01  end=10-06
    2018-12-31      ${False}       begin=05-01  end=10-06
    2018-01-01      ${True}        begin=06-20  end=04-30
    2018-04-29      ${True}        begin=06-20  end=04-30
    2018-04-30      ${True}        begin=06-20  end=04-30
    2018-05-01      ${False}       begin=06-20  end=04-30
    2018-06-19      ${False}       begin=06-20  end=04-30
    2018-06-20      ${True}        begin=06-20  end=04-30
    2018-06-21      ${True}        begin=06-20  end=04-30
    2018-12-31      ${True}        begin=06-20  end=04-30
    2018-09-01      ${False}       begin=09-02  end=09-02
    2018-09-02      ${True}        begin=09-02  end=09-02
    2018-09-03      ${False}       begin=09-02  end=09-02

Multi Enabler
    [Template]  Test Multi Enabler
    ${False}  ${False}  ${False}  ${False}
    ${False}  ${False}  ${False}  ${True}
    ${False}  ${False}  ${True}   ${False}
    ${False}  ${False}  ${True}   ${True}
    ${False}  ${True}   ${False}  ${False}
    ${False}  ${True}   ${False}  ${True}
    ${False}  ${True}   ${True}   ${False}
    ${True}   ${True}   ${True}   ${True}

Delayed Enabler
    [Setup]  Create Test Harness
    [Teardown]  Cleanup Test Harness

    &{delay} =  Create Dictionary  minutes=${1}
    ${enabler} =  Create App  enabler  ScriptEnabler  test_enabler
    ...    initial=${False}  delay=${delay}
    ${enabled_switch} =  Create Enabled Switch  switch  test_enabler  ${test_switch}

    Schedule Call At  40 sec  call_on_app  ${enabler}  enable
    Schedule Call At  3 min  call_on_app  ${enabler}  disable
    Schedule Call At  5 min 30 sec  call_on_app  ${enabler}  enable
    Schedule Call At  6 min  call_on_app  ${enabler}  disable
    Schedule Call At  8 min  call_on_app  ${enabler}  enable
    Schedule Call At  10 min  call_on_app  ${enabler}  disable
    Schedule Call At  10 min 30 sec  call_on_app  ${enabler}  enable
    Schedule Call At  12 min  call_on_app  ${enabler}  disable

    State Should Change At  ${test_switch}  on    1 min 40 sec
    State Should Change At  ${test_switch}  off   4 min
    State Should Change At  ${test_switch}  on    9 min
    State Should Change At  ${test_switch}  off   13 min


Value Enabler Changes
    [Setup]  Create Test Harness
    [Teardown]  Cleanup Test Harness

    Set State  ${test_input}  ${Empty}
    ${enabler} =  Create App  enabler  ValueEnabler  enabler
    ...    entity=${test_input}  value=foo
    ${enabled_switch} =  Create Enabled Switch  switch  enabler  ${test_switch}
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off

    Set State  ${test_input}  foo
    Enabled State Should Be  ${enabler}  ${True}
    State Should Be  ${test_switch}  on

    Set State  ${test_input}  bar
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off


Range Enabler Changes
    [Setup]  Create Test Harness
    [Teardown]  Cleanup Test Harness

    Set State  ${test_input}  0
    ${enabler} =  Create App  enabler  RangeEnabler  enabler
    ...    entity=${test_input}  min=${10}  max=${20}
    ${enabled_switch} =  Create Enabled Switch  switch  enabler  ${test_switch}
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off

    Set State  ${test_input}  15
    Enabled State Should Be  ${enabler}  ${True}
    State Should Be  ${test_switch}  on

    Set State  ${test_input}  -15
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off


Date Enabler Changes
    [Setup]  Create Test Harness  start_date=2018-02-01  start_time=12:00:00  interval=1h
    [Teardown]  Cleanup Test Harness
    ${enabler} =  Create App  enabler  DateEnabler  enabler  begin=02-03  end=02-04
    ${enabled_switch} =  Create Enabled Switch  switch  enabler  ${test_switch}
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off

    State Should Change At Date Time  ${test_switch}  on  2018-02-03 01:00:00
    Enabled State Should Be  ${enabler}  ${True}
    State Should Change At Date Time  ${test_switch}  off  2018-02-05 01:00:00
    Enabled State Should Be  ${enabler}  ${False}


Date Enabler Exact Change Time
    [Setup]  Create Test Harness  start_time=23:59:30  interval=1s
    [Teardown]  Cleanup Test Harness
    ${enabler} =  Create App  enabler  DateEnabler  enabler  begin=01-02  end=01-02
    ${enabled_switch} =  Create Enabled Switch  switch  enabler  ${test_switch}
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off

    State Should Change At  ${test_switch}  on  00:00:01
    Enabled State Should Be  ${enabler}  ${True}


Multi Enabler Changes
    [Setup]  Create Test Harness
    [Teardown]  Cleanup Test Harness
    ${enabler1} =  Create App  enabler  ScriptEnabler  enabler1  initial=${False}
    ${enabler2} =  Create App  enabler  ScriptEnabler  enabler2  initial=${False}
    @{enablers} =  Create List  enabler1  enabler2
    ${enabler} =  Create App  enabler  MultiEnabler  enabler  enablers=${enablers}
    ${enabled_switch} =  Create Enabled Switch  switch  enabler  ${test_switch}
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off
    Set Enabled State  ${enabler1}  enable
    Enabled State Should Be  ${enabler}  ${False}
    State Should Be  ${test_switch}  off
    Set Enabled State  ${enabler2}  enable
    Enabled State Should Be  ${enabler}  ${True}
    State Should Be  ${test_switch}  on



*** Keywords ***

Test Value Enabler
    [Teardown]  Cleanup Test Harness
    [Arguments]  ${class}  ${entity_value}  ${expected_state}  &{args}
    ${arg_keys} =  Catenate  SEPARATOR=_  @{args.keys()}
    Create Test Harness  start_time=00:00:00
    ...    suffix=${class}_${entity_value}_${arg_keys}
    Set State  ${test_input}  ${entity_value}
    ${enabler} =  Create App  enabler  ${class}  enabler
    ...    entity=${test_input}  &{args}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Script Enabler
    [Teardown]  Cleanup Test Harness
    [Arguments]  ${initial_state_arg}  ${expected_initial_state}

    Create Test Harness  start_time=00:00:00
    &{args} =  Create Dictionary
    IF  ${{$initial_state_arg is not None}}
        ${args}[initial] =  Set Variable  ${initial_state_arg}
    END
    ${enabler} =  Create App  enabler  ScriptEnabler  enabler  &{args}

    Enabled State Should Be  ${enabler}  ${expected_initial_state}
    Set Enabled State  ${enabler}  disable
    Enabled State Should Be  ${enabler}  ${False}
    Set Enabled State  ${enabler}  enable
    Enabled State Should Be  ${enabler}  ${True}

Test Date Enabler
    [Teardown]  Cleanup Test Harness
    [Arguments]  ${start_date}  ${expected_state}  ${begin}  ${end}

    Create Test Harness  start_date=${start_date}  start_time=10:00:00
    ...    suffix=${begin}_${end}_${start_date}
    ${enabler} =  Create App  enabler  DateEnabler  enabler
    ...    begin=${begin}  end=${end}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Multi Enabler
    [Arguments]  ${expected_state}  @{values}
    ${suffix} =  Catenate  SEPARATOR=_  @{values}
    Create Test Harness  start_time=00:00:00  suffix=${suffix}
    @{names} =  Create List
    ${i} =  Set Variable  ${0}
    FOR  ${value}  IN  @{values}
        ${name} =  Catenate  enabler  ${i}
        Create App  enabler  ScriptEnabler  ${name}  initial=${value}
        Append To List  ${names}  ${name}
        ${i} =  Set Variable  ${{$i + 1}}
    END
    ${enabler} =  Create App  enabler  MultiEnabler  enabler  enablers=${names}
    Enabled State Should Be  ${enabler}  ${expected_state}

Create Enabled Switch
    [Arguments]  ${name}  ${enabler_name}  ${target}
    ${switch_name} =  Set Variable  ${name}_switch
    ${switch} =  Create App  auto_switch  AutoSwitch  ${switch_name}
    ...    target=${target}
    @{targets} =  Create List  ${switch_name}
    ${enabled_switch} =  Create App  enabled_switch  EnabledSwitch
    ...    ${name}  enabler=${enabler_name}  targets=${targets}
    RETURN  ${enabled_switch}
