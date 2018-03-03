*** Settings ***

Resource       resources/Config.robot


*** Variables ***

${name} =    test_auto_switch
${target} =  input_boolean.test_switch
${switch} =  input_select.test_auto_switch_switch

*** Test Cases ***

Basic Usage
    [Template]  Switch On And Off
#   type      switch  target  off  on
    Basic     auto    off     off  on
    Basic     auto    on      off  on
    Switched  auto    off     off  on
    Switched  auto    on      off  on
    Switched  on      off     on   on
    Switched  on      on      on   on
    Switched  off     off     off  off
    Switched  off     on      off  off

Switch On And Off Manually
    [Template]  Change Manual Switch State
#   initial  changed  expected
    auto     on       on
    auto     off      off
    on       off      off
    on       auto     off
    off      on       on
    off      auto     off

Reentrancy
    [Template]  Switch On And Off Multiple Times
#   type       expected
    Basic      off
    Reentrant  on


*** Keywords ***

Switch On And Off
    [Arguments]  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    ${expected_off}  ${expected_on}
    [Teardown]  Cleanup AppDaemon
    Initialize  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    suffix=${type}.${initial_switch_state}.${initial_target_state}
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch  ${name}
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch  ${name}
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch  ${name}
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch  ${name}
    State Should Be  ${target}  ${expected_off}

Change Manual Switch State
    [Arguments]  ${initial}  ${changed}  ${expected}
    [Teardown]  Cleanup AppDaemon
    Initialize  Switched  ${initial}  off  suffix=${initial}.${changed}
    Set Manual Switch State  ${switch}  ${changed}
    State Should Be  ${target}  ${expected}

Switch On And Off Multiple Times
    [Arguments]  ${type}  ${expected}
    [Teardown]  Cleanup AppDaemon
    Initialize  ${type}  auto  off  suffix=${type}
    Turn On Auto Switch  ${name}
    State Should Be  ${target}  on
    Turn On Auto Switch  ${name}
    State Should Be  ${target}  on
    Turn Off Auto Switch  ${name}
    State Should Be  ${target}  ${expected}
    Turn Off Auto Switch  ${name}
    State Should Be  ${target}  off


Turn On Auto Switch
    [Arguments]  ${app_name}
    Call Function  call_on_app  ${app_name}  auto_turn_on

Turn Off Auto Switch
    [Arguments]  ${app_name}
    Call Function  call_on_app  ${app_name}  auto_turn_off

Set Manual Switch State
    [Arguments]  ${entity_id}  ${state}
    Call Function  call_service  input_select/select_option
    ...    entity_id=${entity_id}  option=${state}

Initialize
    [Arguments]  ${type}  ${initial_switch_state}=auto
    ...    ${initial_target_state}=off  ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${target}=${initial_target_state}
    ...    ${switch}=${initial_switch_state}
    ${apps} =  Create List  TestApp  auto_switch
    ${app_configs} =  Create List  TestApp  AutoSwitch${type}
    Initialize AppDaemon  ${apps}  ${app_configs}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}
