*** Settings ***

Resource       resources/AppDaemon.robot


*** Keywords ***

Enabled State Should Be
    [Arguments]  ${enabler}  ${expected_state}
    ${state} =  Call Function  call_on_app  ${enabler}  is_enabled
    Should Be Equal  ${state}  ${expected_state}

