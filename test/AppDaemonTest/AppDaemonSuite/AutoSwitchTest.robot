*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot


*** Variables ***

${name} =    test_auto_switch
${target} =  input_boolean.test_switch
${switch} =  input_select.test_auto_switch_switch
${enabler} =  switch_enabler


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

Basic Usage With Enabler
    [Template]  Switch On And Off With Enabler
#   type             switch  target  enabler  off  on
    Enabled          auto    off     enable   off  on
    Enabled          auto    on      enable   off  on
    Enabled          auto    off     disable  off  off
    Enabled          auto    on      disable  off  off
    EnabledSwitched  auto    off     enable   off  on
    EnabledSwitched  auto    on      enable   off  on
    EnabledSwitched  on      off     enable   on   on
    EnabledSwitched  on      on      enable   on   on
    EnabledSwitched  off     off     enable   off  off
    EnabledSwitched  off     on      enable   off  off
    EnabledSwitched  auto    off     disable  off  off
    EnabledSwitched  auto    on      disable  off  off
    EnabledSwitched  on      off     disable  on   on
    EnabledSwitched  on      on      disable  on   on
    EnabledSwitched  off     off     disable  off  off
    EnabledSwitched  off     on      disable  off  off

Switch On And Off Manually
    [Template]  Change Manual Switch State
#   initial  auto_switch_state  changed  expected
    auto     off                on       on
    auto     off                off      off
    on       off                off      off
    on       off                auto     off
    off      off                on       on
    off      off                auto     off
    auto     on                 on       on
    auto     on                 off      off
    on       on                 off      off
    on       on                 auto     on
    off      on                 on       on
    off      on                 auto     on

Target State Changes
    [Teardown]  Cleanup AppDaemon
    Initialize  Switched
    Set Manual Switch State  ${switch}  off
    State Should Be  ${target}  off
    Turn On  ${target}
    State Should Be  ${target}  on
    State Should Be  ${switch}  on
    Turn Off  ${target}
    State Should Be  ${target}  off
    State Should Be  ${switch}  off

    Set Manual Switch State  ${switch}  auto
    Turn Off Auto Switch  ${name}
    Turn On  ${target}
    State Should Be  ${target}  off
    State Should Be  ${switch}  auto
    Turn On Auto Switch  ${name}
    Turn Off  ${target}
    State Should Be  ${target}  on
    State Should Be  ${switch}  auto

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

Switch On And Off With Enabler
    [Arguments]  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    ${enabler_state}  ${expected_off}  ${expected_on}
    [Teardown]  Cleanup AppDaemon
    Initialize  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    suffix=${type}.${initial_switch_state}.${initial_target_state}.${enabler_state}
    Set Enabled State  ${enabler}  ${enabler_state}
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
    [Arguments]  ${initial}  ${auto_switch_state}  ${changed}  ${expected}
    [Teardown]  Cleanup AppDaemon
    Initialize  Switched  ${initial}  ${target}  suffix=${initial}.${auto_switch_state}.${changed}
    Turn On Or Off Auto Switch  ${name}  ${auto_switch_state}
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
    Select Option  ${entity_id}  ${state}

Turn On Or Off Auto Switch
    [Arguments]  ${app_name}  ${state}
    Run Keyword If  '${state}' == 'on'
    ...    Turn On Auto Switch  ${app_name}
    ...    ELSE
    ...    Turn Off Auto Switch  ${app_name}

Initialize
    [Arguments]  ${type}  ${initial_switch_state}=auto
    ...    ${initial_target_state}=off  ${suffix}=${Empty}
    Clean States
    Initialize States
    ...    ${target}=${initial_target_state}
    ...    ${switch}=${initial_switch_state}
    ${apps} =  Create List  TestApp  locker  mutex_graph  enabler  auto_switch
    ${app_configs} =  Create List  TestApp  AutoSwitch${type}
    Initialize AppDaemon  ${apps}  ${app_configs}  suffix=${suffix}
    Unblock For  ${appdaemon_interval}

# TODO: test turn off -> turn on before it would turn on
