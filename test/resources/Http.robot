*** Settings ***

Library    HttpLibrary.HTTP


*** Keywords ***

Run And Restore Http Context
    [Arguments]  ${keyword}  @{args}  &{kwargs}
    [Teardown]   Restore Http Context
    ${result} =  Run Keyword  ${keyword}   @{args}  &{kwargs}
    [Return]  ${result}

Run In Http Context
    [Arguments]  ${host}  ${keyword}  @{args}  &{kwargs}
    Create Http Context  ${host}
    ${result} =  Run And Restore Http Context  ${keyword}  @{args}  &{kwargs}
    [Return]  ${result}

Ask For Connection Keepalive
    Set Request Header  Connection  keep-alive
