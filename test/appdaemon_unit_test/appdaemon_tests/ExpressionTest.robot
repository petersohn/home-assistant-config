*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/DateTime.robot
Test Teardown  Cleanup Test Harness


*** Variables ***

${input1} =  sensor.test_input1
${input2} =  sensor.test_input2
${input3} =  sensor.test_input3
${output} =  sensor.test_output


*** Test Cases ***

Numeric Sensors
    [Setup]  Initialize  v.${input1} + v["${input2}"]
    ...  ${input1}=0
    ...  ${input2}=0
    [Template]  Test Sensors
    ${0}   ${0}   int  ${0}
    ${0}   ${13}  int  ${13}
    ${63}  ${-8}  int  ${55}
    ${-7}  ${5}   int  ${-2}

Alphanumeric Sensors
    [Setup]  Initialize  v.${input1} + v.${input2}
    ...  ${input1}=${Empty}
    ...  ${input2}=${Empty}
    [Template]  Test Sensors
    foo       bar       str  foobar
    ${Empty}  foo       str  foo
    bar       ${Empty}  str  bar
    ${empty}  ${empty}  str  ${Empty}

Numeric Binary Sensors
    [Setup]  Initialize  v.${input1} > v.${input2}
    ...  ${input1}=0
    ...  ${input2}=0
    [Template]  Test Sensors
    ${0}   ${1}   str  off
    ${1}   ${0}   str  on
    ${0}   ${0}   str  off
    ${5}   ${10}  str  off
    ${10}  ${5}   str  on

Alphanumeric Binary Sensors
    [Setup]  Initialize  v.${input1} > v["${input2}"]
    ...  ${input1}=${Empty}
    ...  ${input2}=${Empty}
    [Template]  Test Sensors
    foo    bar          str  on
    bar    foo          str  off
    bar    bar          str  off
    ${Empty}  foo       str  off
    bar       ${Empty}  str  on
    ${empty}  ${empty}  str  off

Attributes
    [Setup]  Initialize  a.${input1}.attr1 + a["${input1}"]["attr2"]
    ...  ${input1}=${Empty}
    [Template]  Test Attributes
    ${0}   ${0}   int  ${0}
    ${0}   ${13}  int  ${13}
    ${63}  ${-8}  int  ${55}
    ${-7}  ${5}   int  ${-2}
    foo    bar    str  foobar

Ok
    [Setup]  Initialize  ok.${input1}
    ...  ${input1}=unknown
    [Template]  Test Sensors
    unknown       ${0}   str  off
    ${0}          ${0}   str  on
    unavailable   ${0}   str  off
    foo           ${0}   str  on
    ${-1}          ${0}   str  on

Get Now
    [Setup]  Initialize  now().strftime("%Y-%m-%d %H:%M:%S")
    Advance Time To  00:01:00
    ${result} =  Get State  ${output}
    Times Should Match  ${result}  00:01:00
    Advance Time To  00:01:30
    ${result} =  Get State  ${output}
    Times Should Match  ${result}  00:01:30
    Advance Time To  01:12:20
    ${result} =  Get State  ${output}
    Times Should Match  ${result}  01:12:20

Args
    [Setup]  Initialize With Args
    ...  args['list'][int(v['sensor.test_input1'])] + args['dict'][v['sensor.test_input2']]
    ...  ${input1}=0
    ...  ${input2}=a
    [Template]  Test Args
    ${0}  c  firstbaz
    ${1}  a  secondfoo
    ${2}  b  thirdbar

Changes
    [Setup]  Create Test Harness
    Set State  ${input1}  0
    Create App  history  ChangeTracker  changes  entity=${input1}
    Create Expression
    ...    expr='{} {}'.format(c.changes.strftime('%H:%M:%S'), u.changes.strftime('%H:%M:%S'))

    Advance Time To  00:01:00
    Set State  ${input1}  1  foo=bar
    Advance Time  ${appdaemon_interval}
    State Should Be  ${output}  00:01:00 00:01:00
    Advance Time To  00:01:30
    Set State  ${input1}  1  foo=baz
    Advance Time  ${appdaemon_interval}
    State Should Be  ${output}  00:01:00 00:01:30

Nums
    [Setup]  Initialize  sum(nums(v.sensor.test_input1, v.sensor.test_input2, v.sensor.test_input3))
    ...  ${input1}=unknown
    ...  ${input2}=unknown
    ...  ${input3}=unknown
    State Should Be  ${output}  0
    Set State  ${input1}  12
    Set State  ${input2}  6.5
    Set State  ${input3}  -2
    State Should Be  ${output}  16.5
    Set State  ${input2}  foo
    Set State  ${input1}  0
    State Should Be  ${output}  -2.0


*** Keywords ***

Test States
    [Arguments]  ${sensor1}  ${sensor2}  ${type}  ${expected_result}
    Set State  ${input1}  ${sensor1}
    Set State  ${input2}  ${sensor2}
    State Should Be As  ${output}  ${type}  ${expected_result}

Test Sensors
    [Arguments]  ${sensor1}  ${sensor2}  ${type}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  ${type}  ${expected_result}

Test Args
    [Arguments]  ${sensor1}  ${sensor2}  ${expected_result}
    Test States  ${sensor1}  ${sensor2}  str  ${expected_result}

Test Attributes
    [Arguments]  ${attr1}  ${attr2}  ${type}  ${expected_result}
    Set State  ${input_1}  ${0}  attr1=${attr1}  attr2=${attr2}
    State Should Be As  ${output}  ${type}  ${expected_result}

Create Expression
    [Arguments]  &{args}
    Create App  expression  Expression  expression  target=${output}  &{args}

Initialize With Args
    [Arguments]  ${expression}  &{initial_values}
    @{list} =  Create List  first  second  third
    &{dict} =  Create Dictionary  a=foo  b=bar  c=baz
    &{args} =  Create Dictionary  list=${list}  dict=${dict}
    Initialize  ${expression}  ${args}  &{initial_values}


Initialize
    [Arguments]  ${expression}  ${args}=&{Empty}  &{initial_values}
    Create Test Harness
    FOR  ${entity}  ${value}  IN  &{initial_values}
        Set State  ${entity}  ${value}
    END
    Create Expression  expr=${expression}  &{args}
