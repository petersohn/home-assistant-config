*** Settings ***

Library  libraries/TypeUtil.py


*** Test Cases ***

Extract Existing Item From Dictionary
    ${dictionary} =  Create Dictionary  key1=value1  key2=value2
    ${expected_output} =  Create Dictionary  key2=value2
    ${result} =  Extract From Dictionary  ${dictionary}  key1

    Should Be Equal  ${result}  value1
    Should Be Equal  ${dictionary}  ${expected_output}

Extract Nonexisting Item From Dictionary
    ${dictionary} =  Create Dictionary  key1=value1  key2=value2
    ${expected_output} =  Create Dictionary  key1=value1  key2=value2
    ${result} =  Extract From Dictionary  ${dictionary}  key3

    Should Be Equal  ${result}  ${None}
    Should Be Equal  ${dictionary}  ${expected_output}
