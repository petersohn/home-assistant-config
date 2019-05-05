*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_binary} =  binary_sensor.test_input
${input_sensor} =  sensor.test_input


*** Test Cases ***

Script Enabler
    Enabled State Should Be  script_enabler_default  ${True}
    Enabled State Should Be  script_enabler_true  ${True}
    Enabled State Should Be  script_enabler_false  ${False}

    Set Enabled State  script_enabler_default  disable
    Enabled State Should Be  script_enabler_default  ${False}
    Set Enabled State  script_enabler_default  enable
    Enabled State Should Be  script_enabler_default  ${True}

    Set Enabled State  script_enabler_true  disable
    Enabled State Should Be  script_enabler_true  ${False}
    Set Enabled State  script_enabler_true  enable
    Enabled State Should Be  script_enabler_true  ${True}

    Set Enabled State  script_enabler_false  enable
    Enabled State Should Be  script_enabler_false  ${True}
    Set Enabled State  script_enabler_false  disable
    Enabled State Should Be  script_enabler_false  ${False}

Entity Based Enablers
    [Template]  Set Value And Check State
    # entity         value    enabler                 expected_state
    ${input_binary}  off      value_enabler_on        ${False}
    ${input_binary}  on       value_enabler_on        ${True}
    ${input_binary}  off      value_enabler_off       ${True}
    ${input_binary}  on       value_enabler_off       ${False}
    ${input_sensor}  foo      value_enabler_multiple  ${True}
    ${input_sensor}  bar      value_enabler_multiple  ${True}
    ${input_sensor}  foobar   value_enabler_multiple  ${False}
    ${input_sensor}  ${0}     value_enabler_multiple  ${False}
    ${input_sensor}  ${100}   value_enabler_multiple  ${False}
    ${input_sensor}  ${-100}  range_enabler           ${False}
    ${input_sensor}  ${0}     range_enabler           ${False}
    ${input_sensor}  ${9}     range_enabler           ${False}
    ${input_sensor}  ${10}    range_enabler           ${True}
    ${input_sensor}  ${15}    range_enabler           ${True}
    ${input_sensor}  ${20}    range_enabler           ${True}
    ${input_sensor}  ${21}    range_enabler           ${False}
    ${input_sensor}  ${100}   range_enabler           ${False}
    ${input_sensor}  ${-100}  range_enabler_only_min  ${False}
    ${input_sensor}  ${0}     range_enabler_only_min  ${False}
    ${input_sensor}  ${14}    range_enabler_only_min  ${False}
    ${input_sensor}  ${15}    range_enabler_only_min  ${True}
    ${input_sensor}  ${16}    range_enabler_only_min  ${True}
    ${input_sensor}  ${100}   range_enabler_only_min  ${True}
    ${input_sensor}  ${-100}  range_enabler_only_max  ${True}
    ${input_sensor}  ${0}     range_enabler_only_max  ${True}
    ${input_sensor}  ${14}    range_enabler_only_max  ${True}
    ${input_sensor}  ${15}    range_enabler_only_max  ${True}
    ${input_sensor}  ${16}    range_enabler_only_max  ${False}
    ${input_sensor}  ${100}   range_enabler_only_max  ${False}

Date Enabler
    [Setup]  NONE
    [Template]  Test Date Enabler
    # start_date  enabler                expected_state
    2018-01-01    date_enabler_same      ${False}
    2018-03-10    date_enabler_same      ${False}
    2018-03-11    date_enabler_same      ${True}
    2018-03-12    date_enabler_same      ${False}
    2018-12-31    date_enabler_same      ${False}
    2018-01-01    date_enabler_forward   ${False}
    2018-04-30    date_enabler_forward   ${False}
    2018-05-01    date_enabler_forward   ${True}
    2018-05-02    date_enabler_forward   ${True}
    2018-10-05    date_enabler_forward   ${True}
    2018-10-06    date_enabler_forward   ${True}
    2018-10-07    date_enabler_forward   ${False}
    2018-12-31    date_enabler_forward   ${False}
    2018-01-01    date_enabler_backward  ${True}
    2018-04-29    date_enabler_backward  ${True}
    2018-04-30    date_enabler_backward  ${True}
    2018-05-01    date_enabler_backward  ${False}
    2018-06-19    date_enabler_backward  ${False}
    2018-06-20    date_enabler_backward  ${True}
    2018-06-21    date_enabler_backward  ${True}
    2018-12-31    date_enabler_backward  ${True}

*** Keywords ***

Set Value And Check State
    [Arguments]  ${entity}  ${value}  ${enabler}  ${expected_state}
    Set State  ${entity}  ${value}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Date Enabler
    [Teardown]  Cleanup AppDaemon
    [Arguments]  ${start_date}  ${enabler}  ${expected_state}
    Initialize  10:00:00  ${start_date}  ${enabler}-${start_date}
    Enabled State Should Be  ${enabler}  ${expected_state}

Initialize
    [Arguments]  ${start_time}  ${start_date}=${default_start_date}
    ...          ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${input_binary}=off
    ...    ${input_sensor}=0
    ${apps} =  Create List  TestApp  enabler
    ${app_configs} =  Create List  TestApp  Enabler
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${start_date}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}
