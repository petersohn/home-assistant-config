*** Settings ***

Library   DateTime
Resource  resources/TestHarness.robot


*** Keywords ***

Times Should Match
    [Arguments]  ${actual}  ${expected}
    ${expected_date} =  Get Date From Time  ${expected}  future=${False}
    ${actual_date} =  Convert Date  ${actual}  result_format=datetime
    Should Be Equal  ${actual_date}  ${expected_date}

Current Time Should Be
    [Arguments]  ${time}
    ${current_time} =  Get Current Time
    Times Should Match  ${current_time}  ${time}

Current Date Time Should Be
    [Arguments]  ${expected}
    ${now} =  Get Current Time
    ${expected_converted} =  Convert Date  ${expected}  result_format=datetime
    Should Be Equal  ${now}  ${expected_converted}

Calculate Time
    [Arguments]  ${function}  ${delay}
    ${target} =  Call Function  ${function}  result_type=str
    ${result} =  Add Time To Date  ${target}  ${delay}
    RETURN  ${result}
