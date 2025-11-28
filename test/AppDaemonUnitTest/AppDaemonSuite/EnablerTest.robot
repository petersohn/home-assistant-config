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
    ${switch} =  Create App  auto_switch  AutoSwitch  test_switch
    ...    target=${test_switch}
    @{targets} =  Create List  test_switch
    ${enabled_switch} =  Create App  enabled_switch  EnabledSwitch
    ...    test_enabled_switch  enabler=test_enabler  targets=${targets}

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


*** Keywords ***

Test Value Enabler
    [Teardown]  Cleanup Test Harness
    [Arguments]  ${class}  ${entity_value}  ${expected_state}  &{args}
    Create Test Harness  start_time=00:00:00
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
    [Arguments]  ${start_date}  ${expected_state}  &{args}

    Create Test Harness  start_date=${start_date}  start_time=10:00:00
    ${enabler} =  Create App  enabler  DateEnabler  enabler  &{args}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Multi Enabler
    [Arguments]  ${expected_state}  @{values}
    Create Test Harness  start_time=00:00:00
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
