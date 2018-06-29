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

    Call Function  call_on_app  script_enabler_default  disable
    Enabled State Should Be  script_enabler_default  ${False}
    Call Function  call_on_app  script_enabler_default  enable
    Enabled State Should Be  script_enabler_default  ${True}

    Call Function  call_on_app  script_enabler_true  disable
    Enabled State Should Be  script_enabler_true  ${False}
    Call Function  call_on_app  script_enabler_true  enable
    Enabled State Should Be  script_enabler_true  ${True}

    Call Function  call_on_app  script_enabler_false  enable
    Enabled State Should Be  script_enabler_false  ${True}
    Call Function  call_on_app  script_enabler_false  disable
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

Sun Comes Up
    [Setup]  Initialize  ${before_sunrise}
    Enabled State Should Be  sun_enabler_day  ${False}
    Enabled State Should Be  sun_enabler_night  ${True}
    Unblock Until Sunrise
    Enabled State Should Be  sun_enabler_day  ${True}
    Enabled State Should Be  sun_enabler_night  ${False}

Sun Goes Down
    [Setup]  Initialize  ${before_sunset}
    Enabled State Should Be  sun_enabler_day  ${True}
    Enabled State Should Be  sun_enabler_night  ${False}
    Unblock Until Sunset
    Enabled State Should Be  sun_enabler_day  ${False}
    Enabled State Should Be  sun_enabler_night  ${True}


*** Keywords ***

Set Value And Check State
    [Arguments]  ${entity}  ${value}  ${enabler}  ${expected_state}
    Set State  ${entity}  ${value}
    Enabled State Should Be  ${enabler}  ${expected_state}

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${input_binary}=off
    ...    ${input_sensor}=0
    ${apps} =  Create List  TestApp  enabler
    ${app_configs} =  Create List  TestApp  Enabler
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
