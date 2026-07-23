*** Settings ***

Resource       resources/TestHarness.robot


*** Keywords ***

Enabled State Should Be
    [Arguments]  ${enabler}  ${expected_state}
    ${state} =  Call On App  ${enabler}  is_enabled
    Should Be Equal  ${state}  ${expected_state}

Set Enabled State
    [Arguments]  ${enabler}  ${state}
    Call On App  ${enabler}  ${state}
