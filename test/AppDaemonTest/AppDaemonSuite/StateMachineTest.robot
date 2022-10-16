*** Settings ***

Resource       resources/Config.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon

*** Variables ***

${text_field_1}   input_text.test_text_1
${text_field_2}   input_text.test_text_2
${input_field}    sensor.test_input
${expr_value}     sensor.expr_value
${foobar_switch}  input_boolean.test_switch
${baz_switch}     input_boolean.test_switch2
${timed_switch}   input_boolean.test_switch3
${expr_switch}    input_boolean.test_switch4
${expr_value}     sensor.expr_value


*** Test Cases ***

Enter And Exit Actions
    State Should Be  ${text_field_1}  init value
    State Should Be  ${text_field_2}  ${empty}
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    Turn On  ${foobar_switch}
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${text_field_2}  entered
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    Turn Off  ${foobar_switch}
    State Should Be  ${text_field_1}  init value
    State Should Be  ${text_field_2}  exited
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

Switch Between States
    State Should Be  ${text_field_1}  init value
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    Turn On  ${baz_switch}
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on
    State Should Be  ${timed_switch}  off

    Turn On  ${foobar_switch}
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

State Change With Value
    State Should Be  ${text_field_1}  init value
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    Set State  ${input_field}  foobar
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off
    State Should Not Change For  ${foobar_switch}  ${appdaemon_interval}

    Set State  ${input_field}  baz
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on
    State Should Be  ${timed_switch}  off
    State Should Not Change For  ${baz_switch}  ${appdaemon_interval}

    Set State  ${input_field}  foobar
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on
    State Should Be  ${timed_switch}  off
    State Should Not Change For  ${baz_switch}  ${appdaemon_interval}

Timed State Change
    State Should Be  ${text_field_1}  init value
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    Schedule Call At  1 min
    ...    turn_on  ${timed_switch}
    State Should Change At  ${text_field_1}  timed  1 min
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  on

    State Should Change At  ${text_field_1}  timed2  2 min
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

    State Should Change At  ${text_field_1}  init value  2 min 30 sec
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off
    State Should Be  ${timed_switch}  off

Expr Actions
    State Should Be  ${text_field_2}  ${Empty}
    Set State  ${expr_value}  a
    Turn On  ${expr_switch}
    State Should Be  ${text_field_2}  enter a
    Turn Off  ${expr_switch}
    State Should Be  ${text_field_2}  exit a

    Set State  ${expr_value}  b
    Turn On  ${expr_switch}
    State Should Be  ${text_field_2}  enter b
    Set State  ${expr_value}  c
    State Should Be  ${text_field_2}  enter b
    Turn Off  ${expr_switch}
    State Should Be  ${text_field_2}  exit c

Expr Next State
    Set State  ${input_field}  expr
    State Should Be  ${text_field_1}  expr next
    Set State  ${input_field}  to_foobar
    State Should Be  ${text_field_1}  gone to foobar
    Set State  ${input_field}  expr
    State Should Be  ${text_field_1}  expr next
    Set State  ${input_field}  to_baz
    State Should Be  ${text_field_1}  it is baz


*** Keywords ***

Initialize
    Clean States
    Initialize States
    ...   ${input_field}=${Empty}
    ...   ${text_field_1}=${Empty}
    ...   ${text_field_2}=${Empty}
    ${apps} =  Create List  TestApp  locker  mutex_graph  state_machine
    ...                     expression
    ${app_configs} =  Create List  TestApp  StateMachine
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
