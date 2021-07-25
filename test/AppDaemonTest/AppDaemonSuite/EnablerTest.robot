*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/Enabler.robot
Test Teardown  Cleanup AppDaemon


*** Variables ***

${input_binary} =  binary_sensor.test_input
${input_sensor_txt} =  sensor.test_input_txt
${input_sensor_num} =  sensor.test_input_num


*** Test Cases ***

Script Enabler
    [Setup]  Initialize With Config  00:00:00  ScriptEnabler
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
    [Setup]  Initialize With Config  00:00:00  ValueEnabler
    [Template]  Set Value And Check State
    # entity         value    enabler                 expected_state
    ${input_binary}  off      value_enabler_on        ${False}
    ${input_binary}  on       value_enabler_on        ${True}
    ${input_binary}  off      value_enabler_off       ${True}
    ${input_binary}  on       value_enabler_off       ${False}
    ${input_sensor_txt}  foo      value_enabler_multiple  ${True}
    ${input_sensor_txt}  bar      value_enabler_multiple  ${True}
    ${input_sensor_txt}  foobar   value_enabler_multiple  ${False}
    ${input_sensor_txt}  ${0}     value_enabler_multiple  ${False}
    ${input_sensor_txt}  ${100}   value_enabler_multiple  ${False}
    ${input_sensor_num}  ${-100}  range_enabler           ${False}
    ${input_sensor_num}  ${0}     range_enabler           ${False}
    ${input_sensor_num}  ${9}     range_enabler           ${False}
    ${input_sensor_num}  ${10}    range_enabler           ${True}
    ${input_sensor_num}  ${15}    range_enabler           ${True}
    ${input_sensor_num}  ${20}    range_enabler           ${True}
    ${input_sensor_num}  ${21}    range_enabler           ${False}
    ${input_sensor_num}  ${100}   range_enabler           ${False}
    ${input_sensor_num}  ${-100}  range_enabler_only_min  ${False}
    ${input_sensor_num}  ${0}     range_enabler_only_min  ${False}
    ${input_sensor_num}  ${14}    range_enabler_only_min  ${False}
    ${input_sensor_num}  ${15}    range_enabler_only_min  ${True}
    ${input_sensor_num}  ${16}    range_enabler_only_min  ${True}
    ${input_sensor_num}  ${100}   range_enabler_only_min  ${True}
    ${input_sensor_num}  ${-100}  range_enabler_only_max  ${True}
    ${input_sensor_num}  ${0}     range_enabler_only_max  ${True}
    ${input_sensor_num}  ${14}    range_enabler_only_max  ${True}
    ${input_sensor_num}  ${15}    range_enabler_only_max  ${True}
    ${input_sensor_num}  ${16}    range_enabler_only_max  ${False}
    ${input_sensor_num}  ${100}   range_enabler_only_max  ${False}

Date Enabler
    [Setup]  NONE
    [Teardown]  NONE
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

Multi Enabler
    [Setup]  Initialize With Config  00:00:00  ScriptEnabler  MultiEnabler
    [Template]  Test Multi Enabler
    ${False}  script_enabler_default=disable  script_enabler_true=disable  script_enabler_false=disable
    ${False}  script_enabler_default=disable  script_enabler_true=disable  script_enabler_false=enable
    ${False}  script_enabler_default=disable  script_enabler_true=enable   script_enabler_false=disable
    ${False}  script_enabler_default=disable  script_enabler_true=enable   script_enabler_false=enable
    ${False}  script_enabler_default=enable   script_enabler_true=disable  script_enabler_false=disable
    ${False}  script_enabler_default=enable   script_enabler_true=disable  script_enabler_false=enable
    ${False}  script_enabler_default=enable   script_enabler_true=enable   script_enabler_false=disable
    ${True}   script_enabler_default=enable   script_enabler_true=enable   script_enabler_false=enable

Delayed Enabler
    ${configs} =  Create List  ScriptEnablerDelayed
    ${modules} =  Create List  enabled_switch  auto_switch
    Initialize Base  00:00:00
    ...      configs=${configs}
    ...      modules=${modules}
    Schedule Call At  40 sec
    ...    call_on_app  test_enabler  enable
    Schedule Call At  3 min
    ...    call_on_app  test_enabler  disable
    Schedule Call At  5 min 30 sec
    ...    call_on_app  test_enabler  enable
    Schedule Call At  6 min
    ...    call_on_app  test_enabler  disable
    Schedule Call At  8 min
    ...    call_on_app  test_enabler  enable
    Schedule Call At  10 min
    ...    call_on_app  test_enabler  disable
    Schedule Call At  10 min 30 sec
    ...    call_on_app  test_enabler  enable
    Schedule Call At  12 min
    ...    call_on_app  test_enabler  disable

    State Should Change At  input_boolean.test_switch  on    1 min 40 sec
    State Should Change At  input_boolean.test_switch  off   4 min
    State Should Change At  input_boolean.test_switch  on    9 min
    State Should Change At  input_boolean.test_switch  off   13 min


*** Keywords ***

Set Value And Check State
    [Arguments]  ${entity}  ${value}  ${enabler}  ${expected_state}
    Set State  ${entity}  ${value}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Date Enabler
    [Teardown]  Cleanup AppDaemon
    [Arguments]  ${start_date}  ${enabler}  ${expected_state}
    ${configs} =  Create List  DateEnabler
    ${modules} =  Create List
    Initialize Base  10:00:00
    ...    configs=${configs}
    ...    modules=${modules}
    ...    start_date=${start_date}
    ...    suffix=${enabler}-${start_date}
    Enabled State Should Be  ${enabler}  ${expected_state}

Test Multi Enabler
    [Arguments]  ${expected_state}  &{kwargs}
    FOR  ${name}  IN  @{kwargs.keys()}
        Set Enabled State  ${name}  ${kwargs['${name}']}
    END
    Unblock For  ${appdaemon_interval}
    Enabled State Should Be  multi_enabler  ${expected_state}

Initialize With Config
    [Arguments]  ${start_time}  @{configs}
    ${modules} =  Create List
    Initialize Base  ${start_time}  configs=${configs}  modules=${modules}

Initialize Base
    [Arguments]  ${start_time}  ${configs}=${Empty}  ${modules}=${Empty}
    ...          ${start_date}=${default_start_date}
    ...          ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${input_binary}=off
    ...    ${input_sensor_num}=0
    ...    ${input_sensor_txt}=${Empty}
    ${apps} =  Create List  TestApp  locker  mutex_graph  enabler  @{modules}
    ${app_configs} =  Create List  TestApp  @{configs}
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    ...                   start_date=${start_date}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}
