*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Test Setup     Initialize
Test Teardown  Cleanup Environment

*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Unblock For Some Time
    ${unblock_time} =  Set Variable  ${120}
    ${finish_time} =  Add Time To Date  ${start_time}  ${unblock_time}
    Call Function  unblock_for  ${unblock_time}
    Wait Until Keyword Succeeds  5s  0.1s
    ...    Current Time Should Be  ${finish_time}


*** Keywords ***

Initialize
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize Environment  ${apps}  ${app_configs}


Current Time Should Be
    [Arguments]  ${time}
    ${time_value} =  Convert Date  ${time}
    ${current_time} =  Call Function  get_current_time
    ${current_time_value} =  Convert Date  ${current_time}
    Should Be Equal  ${current_time_value}  ${time_value}
