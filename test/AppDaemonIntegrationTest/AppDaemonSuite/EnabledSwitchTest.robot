*** Settings ***

Library   Collections
Resource  resources/AppDaemon.robot
Resource  resources/HomeAssistant.robot
Resource  resources/Config.robot
Resource  resources/HistoryWatcher.robot


*** Variables ***

${input_switch}    input_select.test_auto_switch_switch
${output_switch}   input_boolean.test_switch1
${enabler}         test_enabler


*** Test Cases ***

Initial State
    [Template]  Test Initial State
    off   ${False}  off
    off   ${True}   off
    on    ${False}  on
    on    ${True}   on
    auto  ${False}  off
    auto  ${True}   on



*** Keywords ***

Test Initial State
    [Teardown]  Cleanup Apps Configs
    [Arguments]  ${initial_state}  ${initial_enabled_state}  ${expected_state}
    Set Test Variable  ${TEST_SUFFIX}  ${initial_state}_${initial_enabled_state}
    Initialize  ${initial_state}  ${initial_enabled_state}
    Wait Until Keyword Succeeds  10s  0.1s
    ...  State Should Be  ${output_switch}  ${expected_state}
    @{expected_history} =  Create List
    IF  '${expected_state}' == 'on'
        Append To List  ${expected_history}  ${output_switch}  on
    END
    Check History  @{expected_history}


Enable
    Call On App  ${enabler}  enable

Disable
    Call On App  ${enabler}  disable

Initialize
    [Arguments]  ${initial_state}  ${initial_enabled_state}
    Initialize States
    ...    ${input_switch}=${initial_state}
    ...    ${output_switch}=off
    IF  ${initial_enabled_state}
        ${enabler_config} =  Set Variable  ScriptEnablerOn
    ELSE
        ${enabler_config} =  Set Variable  ScriptEnablerOff
    END
    Initialize Apps Configs  HistoryWatcher  AutoSwitch  ${enabler_config}
