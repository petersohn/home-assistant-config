*** Settings ***

Resource       resources/Config.robot
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon

*** Variables ***

${text_field_1}  input_text.test_text_1
${input_field}  sensor.test_input


*** Test Cases ***

Init
    State Should Be  ${text_field_1}  simple value


*** Keywords ***

Initialize
    Clean States
    Initialize States
    ...   ${input_field}=${0}
    ${apps} =  Create List  TestApp  locker  mutex_graph  state_machine
    ...                     expression
    ${app_configs} =  Create List  TestApp  StateMachine
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
