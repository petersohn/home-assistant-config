*** Settings ***

Resource       resources/Config.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon

*** Variables ***

${text_field_1}   input_text.test_text_1
${text_field_2}   input_text.test_text_2
${input_field}    sensor.test_input
${foobar_switch}  input_boolean.test_switch
${baz_switch}  input_boolean.test_switch2


*** Test Cases ***

Enter And Exit Actions
    State Should Be  ${text_field_1}  init value
    State Should Be  ${text_field_2}  ${empty}
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off

    Turn On  ${foobar_switch}
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${text_field_2}  entered
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off

    Turn Off  ${foobar_switch}
    State Should Be  ${text_field_1}  init value
    State Should Be  ${text_field_2}  exited
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off

Switch Between States
    State Should Be  ${text_field_1}  init value
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off

    Turn On  ${baz_switch}
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on

    Turn On  ${foobar_switch}
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off

State Change With Value
    State Should Be  ${text_field_1}  init value
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  off

    Set State  ${input_field}  1
    State Should Be  ${text_field_1}  gone to foobar
    State Should Be  ${foobar_switch}  on
    State Should Be  ${baz_switch}  off
    State Should Not Change For  ${foobar_switch}  ${appdaemon_interval}

    Set State  ${input_field}  2
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on
    State Should Not Change For  ${baz_switch}  ${appdaemon_interval}

    Set State  ${input_field}  1
    State Should Be  ${text_field_1}  it is baz
    State Should Be  ${foobar_switch}  off
    State Should Be  ${baz_switch}  on
    State Should Not Change For  ${baz_switch}  ${appdaemon_interval}



*** Keywords ***

Initialize
    Clean States
    Initialize States
    ...   ${input_field}=${0}
    ...   ${text_field_1}=${Empty}
    ...   ${text_field_2}=${Empty}
    ${apps} =  Create List  TestApp  locker  mutex_graph  state_machine
    ...                     expression
    ${app_configs} =  Create List  TestApp  StateMachine
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
