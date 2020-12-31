*** Settings ***

Library  DateTime


*** Keywords ***

Times Should Match
    [Arguments]  ${actual}  ${expected}
    ${expected_date} =  Add Time To Date  ${default_start_date}  ${expected}
    ${actual_date} =  Convert Date  ${actual}
    Should Be Equal  ${actual_date}  ${expected_date}

