*** Settings ***

Resource  resources/AppDaemon.robot
Resource  resources/HomeAssistant.robot
Resource  resources/Config.robot
Resource  resources/HistoryWatcher.robot
Test Teardown  Cleanup Apps Configs


*** Variables ***

${input_switch}    input_select.test_auto_switch_switch
${output_switch}   input_boolean.test_switch1
${enabler}         test_enabler


*** Test Cases ***

Initial State
    [Template]  Test Initial State
    ${



*** Keywords ***

Test Initial State
    [Arguments]  ${initial_state}  ${initial_enabled_state}  ${expected_state}
    Initialize  ${initial_state}  ${initial_enabled_state}
    Wait Until Keyword Succeeds  10s  0.1s
    ...  State Should Be  ${output_switch}  ${expected_state}

Enable
    Call On App  ${enabler}  enable

Disable
    Call On App  ${enabler}  disable

Initialize
    [Arguments]  ${initial_state}  ${initial_enabled_state}
    Set Value  ${input_switch}  ${initial_state}
    IF  ${initial_enabled_state}
        ${enabler_config} =  ScriptEnablerOn
    ELSE
        ${enabler_config} =  ScriptEnablerOff
    END
    @{configs} =  HistoryWatcher  AutoSwitch  ${enabler_config}
    Initialize Apps Configs  @{configs}
