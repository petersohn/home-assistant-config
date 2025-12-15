*** Settings ***

Resource   resources/AppDaemon.robot

*** Keywords ***

Call On History Watcher
    [Arguments]  ${function}  @{args}  &{kwargs}
    ${result} =  Call Function  call_on_app  history_watcher
    ...    ${function}  @{args}  &{kwargs}
    RETURN  ${result}

Get History
    ${result} =  Call On History Watcher  get_history
    RETURN  ${result}

Convert Expected History
    [Arguments]  @{expected}
    @{expected_pairs} =  Create List
    FOR  ${entity}  ${value}  IN  @{expected}
        @{pair} =  Create List  ${entity}  ${value}
        Append To List  ${expected_pairs}  ${pair}
    END
    RETURN  ${expected_pairs}

Check History
    [Arguments]  @{expected}
    ${expected_pairs} =  Convert Expected History  @{expected}
    ${actual} =  Get History
    Lists Should Be Equal  ${actual}  ${expected_pairs}

Should Have History
    [Arguments]  @{expected}
    ${expected_pairs} =  Convert Expected History  @{expected}
    ${result} =  Call On History Watcher  has_history  ${expected_pairs}
    Should Be True  ${result}

Wait For History
    [Arguments]  @{expected}
    Wait Until Keyword Succeeds  30s  0.2s
    ...    Should Have History  @{expected}
