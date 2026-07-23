*** Keywords ***

Critical Check
    [Arguments]  ${message}  ${keyword}  @{args}  &{kwargs}
    ${result} =  Run Keyword And Return Status  ${keyword}  @{args}  &{kwargs}
    Run Keyword If  not ${result}  Fatal Error  ${message}
