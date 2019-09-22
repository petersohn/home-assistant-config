*** Settings ***

Library  mutex_graph.py


*** Test Cases ***

Find Cycle
    [Template]  Test Find Cycle
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3')]}  ${False}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5')]}  ${False}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('', 'e3')]}  ${True}
    {'': [('a', 'e1'), ('b', 'e2')], 'b': [('', 'e3')]}  ${True}
    {'': [('a', 'e1')], 'a': [('b', 'e2')], 'b': [('', 'e3')]}  ${True}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5'), ('a', 'e6')]}  ${True}


*** Keywords ***

Test Find Cycle
    [Arguments]  ${graph_str}  ${expected_result}
    ${graph} =  Evaluate  ${graph_str}
    ${result} =  Find Cycle  ${graph}
    Should Be Equal  ${result}  ${expected_result}
