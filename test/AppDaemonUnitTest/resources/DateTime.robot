*** Settings ***

Library   DateTime
Resource  resources/TestHarness.robot


*** Keywords ***

Times Should Match
    [Arguments]  ${actual}  ${expected}
    ${expected_date} =  Add Time To Date  ${default_start_date}  ${expected}
    ${actual_date} =  Convert Date  ${actual}
    Should Be Equal  ${actual_date}  ${expected_date}

Current Time Should Be
    [Arguments]  ${time}
    ${current_time} =  Get Current Time
    Times Should Match  ${current_time}  ${time}

Calculate Time
    [Arguments]  ${function}  ${delay}
    ${target} =  Call Function  ${function}  result_type=str
    ${result} =  Add Time To Date  ${target}  ${delay}
    RETURN  ${result}
