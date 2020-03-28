*** Settings ***

Library  DateTime


*** Keywords ***

Date Should Equal Time
    [Arguments]  ${date1}  ${base}  ${time}
    ${timestamp1} =  Convert Date  ${date1}
    ${timestamp2} =  Add Time To Date  ${base}  ${time}
    Should Be Equal  ${timestamp1}  ${timestamp2}
