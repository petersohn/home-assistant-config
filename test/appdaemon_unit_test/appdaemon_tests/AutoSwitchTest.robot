*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot
Library        Collections


*** Variables ***

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
    Initialize  Switched
    Set State  ${switch}  off
    State Should Be  ${target}  off
    Turn On  ${target}
    State Should Be  ${target}  on
    State Should Be  ${switch}  on
    Turn Off  ${target}
    State Should Be  ${target}  off
    State Should Be  ${switch}  off

    Set State  ${switch}  auto
    Turn Off Auto Switch
    Turn On  ${target}
    State Should Be  ${target}  off
    State Should Be  ${switch}  auto
    Turn On Auto Switch
    Turn Off  ${target}
    State Should Be  ${target}  on
    State Should Be  ${switch}  auto

Enabled State Changes
    [Teardown]  Cleanup Test Harness
    Initialize  Enabled
    Set Enabled State  ${enabler}  enable
    Turn On Auto Switch
    State Should Be  ${target}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${target}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${target}  on


Reentrancy
    [Template]  Switch On And Off Multiple Times
#   type       expected
    Basic      off
    Reentrant  on


*** Keywords ***

Switch On And Off
    [Arguments]  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    ${expected_off}  ${expected_on}
    [Teardown]  Cleanup Test Harness
    Initialize  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    suffix=${type}_${initial_switch_state}_${initial_target_state}
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch
    State Should Be  ${target}  ${expected_off}

Switch On And Off With Enabler
    [Arguments]  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    ${enabler_state}  ${expected_off}  ${expected_on}
    [Teardown]  Cleanup Test Harness
    Initialize  ${type}  ${initial_switch_state}  ${initial_target_state}
    ...    suffix=${type}_${initial_switch_state}_${initial_target_state}_${enabler_state}
    Set Enabled State  ${enabler}  ${enabler_state}
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch
    State Should Be  ${target}  ${expected_off}
    Turn On Auto Switch
    State Should Be  ${target}  ${expected_on}
    Turn Off Auto Switch
    State Should Be  ${target}  ${expected_off}

Change Manual Switch State
    [Arguments]  ${initial}  ${auto_switch_state}  ${changed}  ${expected}
    [Teardown]  Cleanup Test Harness
    Initialize  Switched  ${initial}  ${target}
    ...    suffix=${initial}_${auto_switch_state}_${changed}
    Turn On Or Off Auto Switch  ${auto_switch_state}
    Set State  ${switch}  ${changed}
    State Should Be  ${target}  ${expected}

Switch On And Off Multiple Times
    [Arguments]  ${type}  ${expected}
    [Teardown]  Cleanup Test Harness
    Initialize  ${type}  auto  off
    Turn On Auto Switch
    State Should Be  ${target}  on
    Turn On Auto Switch
    State Should Be  ${target}  on
    Turn Off Auto Switch
    State Should Be  ${target}  ${expected}
    Turn Off Auto Switch
    State Should Be  ${target}  off

Turn On Auto Switch
    Call On App  ${auto_switch}  auto_turn_on

Turn Off Auto Switch
    Call On App  ${auto_switch}  auto_turn_off

Turn On Or Off Auto Switch
    [Arguments]  ${state}
    IF  '${state}' == 'on'
        Turn On Auto Switch
    ELSE
        Turn Off Auto Switch
    END

Initialize
    [Arguments]  ${type}
    ...    ${initial_switch_state}=auto
    ...    ${initial_target_state}=off
    ...    ${suffix}=${None}

    Create Test Harness  suffix=${suffix}
    Set State  ${target}  ${initial_target_state}
    Set State  ${switch}  ${initial_switch_state}

    &{args} =  Create Dictionary  target=${target}
    IF  'Switched' in '${type}'
        ${args}[switch] =  Set Variable  ${switch}
    END
    IF  'Reentrant' in '${type}'
        ${args}[reentrant] =  Set Variable  ${True}
    END
    IF  'Enabled' in '${type}'
        ${enabler} =  Create App  enabler  ScriptEnabler  switch_enabler
        Set Test Variable  ${enabler}
        ${args}[enabler] =  Set Variable  switch_enabler
    END

    ${auto_switch} =  Create App  auto_switch  AutoSwitch  test_auto_switch  &{args}
    Set Test Variable  ${auto_switch}

    Step

# TODO: test turn off -> turn on before it would turn on
