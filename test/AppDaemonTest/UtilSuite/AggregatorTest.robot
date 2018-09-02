*** Settings ***

Library  libraries/aggregator.py


*** Test Cases ***

Test anglemean
    [Template]  Check anglemean
    ${0}    ${10}  ${5}  ${-15}
    ${0}    ${350}  ${10}
    ${180}  ${170}  ${190}
    ${180}  ${170}  ${-170}
    ${10}   ${-10}  ${30}
    ${350}   ${-30}  ${10}
    ${190}  ${170}  ${210}
    ${170}  ${150}  ${190}


*** Keywords ***

Check anglemean
    [Arguments]  ${expected_result}  @{elements}
    ${result} =  anglemean  ${elements}
    Should Be Equal  ${result}  ${expected_result}
