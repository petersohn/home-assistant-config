*** Settings ***

Library   Collections
Resource  resources/AppDaemon.robot
Resource  resources/HomeAssistant.robot
Resource  resources/Config.robot
Resource  resources/HistoryWatcher.robot


*** Variables ***

${input_switch1}   input_select.test_auto_switch_switch1
${input_switch2}   input_select.test_auto_switch_switch2
${output_switch}   input_boolean.test_switch1
${enabler}         test_enabler
@{base_configs}    HistoryWatcher  EnabledSwitch

*** Test Cases ***

State Changes
    [Setup]  Initialize  @{base_configs}  AutoSwitch1  ScriptEnablerOff
    ...    ${input_switch1}=auto
    State Should Be  ${output_switch}  off
    Select Option  ${input_switch1}  on
    Wait For State  ${output_switch}  on
    Select Option  ${input_switch1}  auto
    Wait For State  ${output_switch}  off
    Enable
    Wait For State  ${output_switch}  on
    Disable
    Wait For State  ${output_switch}  off
    Select Option  ${input_switch1}  on
    Wait For State  ${output_switch}  on
    Enable
    Select Option  ${input_switch1}  off
    Wait For State  ${output_switch}  off
    Select Option  ${input_switch1}  auto
    Wait For State  ${output_switch}  on
    Select Option  ${input_switch1}  off
    Wait For State  ${output_switch}  off
    Check History
    ...    ${output_switch}  on
    ...    ${output_switch}  off
    ...    ${output_switch}  on
    ...    ${output_switch}  off
    ...    ${output_switch}  on
    ...    ${output_switch}  off
    ...    ${output_switch}  on
    ...    ${output_switch}  off

Reload With Different Switch
    [Template]  Test Reload
    ${False}  Off  off   off   off
    ${False}  Off  on    off   on   off
    ${False}  Off  off   on    off  on
    ${False}  Off  on    on    on
    ${False}  Off  off   auto  off
    ${False}  Off  on    auto  on   off
    ${False}  Off  auto  off   off
    ${False}  Off  auto  on    off  on
    ${False}  Off  auto  auto  off
    ${False}  On   off   auto  off  on
    ${False}  On   on    auto  on
    ${False}  On   auto  off   on   off
    ${False}  On   auto  on    on
    ${False}  On   auto  auto  on
    ${True}   Off  off   off   off
    ${True}   Off  on    off   on   off
    ${True}   Off  off   on    off  on
    ${True}   Off  on    on    on
    ${True}   Off  off   auto  off
    ${True}   Off  on    auto  on   off
    ${True}   Off  auto  off   off
    ${True}   Off  auto  on    off  on
    ${True}   Off  auto  auto  off
    ${True}   On   off   auto  off  on
    ${True}   On   on    auto  on
    ${True}   On   auto  off   on   off
    ${True}   On   auto  on    on   off   on
    ${True}   On   auto  auto  on   off   on

*** Keywords ***

Test Reload
    [Teardown]  Cleanup Apps Configs
    [Arguments]  ${reentrant}  ${enabler_state}  ${initial_switch_state}
    ...    ${new_switch_state}  @{expected_states}
    Set Test Variable  ${TEST_SUFFIX}
    ...    ${reentrant}_${enabler_state}_${initial_switch_state}_${new_switch_state}

    ${enabler_config} =  Set Variable  ScriptEnabler${enabler_state}
    IF  ${reentrant}
        ${reentrant_config} =  Set Variable  Reentrant
    ELSE
        ${reentrant_config} =  Set Variable  ${Empty}
    END

    Initialize  @{base_configs}  AutoSwitch1${reentrant_config}  ${enabler_config}
    ...    ${input_switch1}=${initial_switch_state}
    ...    ${input_switch2}=${new_switch_state}

    ${expected_state1} =  Set Variable  ${expected_states[0]}
    ${expected_state2} =  Set Variable  ${expected_states[-1]}

    Wait For State  ${output_switch}  ${expected_state1}

    @{expected_history} =  Create List
    IF  '${expected_state1}' == 'on'
        Append To List  ${expected_history}  ${output_switch}  on
    END
    Check History  @{expected_history}

    Load Apps Configs  @{base_configs}  AutoSwitch2${reentrant_config}  ${enabler_config}  dummy1
    IF  '${expected_state1}' == '${expected_state2}'
        Sleep  2
    END
    Wait For State  ${output_switch}  ${expected_state2}
    @{expected_history} =  Create List
    FOR  ${state}  IN  @{expected_states[1:]}
        Append To List  ${expected_history}  ${output_switch}  ${state}
    END
    Check History  @{expected_history}


Enable
    Call Function  call_on_app  ${enabler}  enable

Disable
    Call Function  call_on_app  ${enabler}  disable

Initialize
    [Arguments]  @{configs}  &{initial_states}
    Initialize States  ${output_switch}=off  &{initial_states}
    Initialize Apps Configs  @{configs}
