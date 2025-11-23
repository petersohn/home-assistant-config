*** Settings ***

Library  apps/mutex_graph.py


*** Test Cases ***

Find Cycle
    [Template]  Test Find Cycle
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3')]}  ${False}
    {'': set([('a', 'e1'), ('b', 'e2')]), 'a': set([('b', 'e3')])}  ${False}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5')]}  ${False}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('', 'e3')]}  ${True}
    {'': set([('a', 'e1'), ('b', 'e2')]), 'a': set([('', 'e3')])}  ${True}
    {'': [('a', 'e1'), ('b', 'e2')], 'b': [('', 'e3')]}  ${True}
    {'': [('a', 'e1')], 'a': [('b', 'e2')], 'b': [('', 'e3')]}  ${True}
    {'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5'), ('a', 'e6')]}  ${True}
    {'': [('a', 'e1')], 'a': [('a', 'e2')]}  ${True}

Append Graph
    [Template]  Test Append Graph
    {'': set([('a', 'e1'), ('b', 'e2'), ('b', 'e3')])}
    ...    {'': set([('a', 'e1'), ('b', 'e2')])}
    ...    {'': set([('a', 'e1'), ('b', 'e3')])}
    {'': set([('a', 'e1'), ('b', 'e2'), ('b', 'e3')])}
    ...    {'': [('a', 'e1'), ('b', 'e2')]}
    ...    {'': [('a', 'e1'), ('b', 'e3')]}
    {'': set([('a', 'e1'), ('b', 'e2'), ('b', 'e3')])}
    ...    {'': [['a', 'e1'], ['b', 'e2']]}
    ...    {'': [['a', 'e1'], ['b', 'e3']]}
    {'': set([('a', 'e1'), ('c', 'e3')]), 'a': set([('b', 'e2')]), 'c': set([('b', 'e4')])}
    ...    {'': set([('a', 'e1')]), 'a': set([('b', 'e2')])}
    ...    {'': set([('c', 'e3')]), 'c': set([('b', 'e4')])}


*** Keywords ***

Test Find Cycle
    [Arguments]  ${graph_str}  ${expected_result}
    ${graph} =  Evaluate  ${graph_str}
    ${result} =  Find Cycle  ${graph}
    Should Be Equal  ${result}  ${expected_result}

Test Append Graph
    [Arguments]  ${expected_result_str}  ${g1_str}  ${g2_str}
    ${graph} =  Evaluate  ${g1_str}
    ${new} =  Evaluate  ${g2_str}
    ${expected_result} =  Evaluate  ${expected_result_str}
    Append Graph  ${graph}  ${new}
    Should Be Equal  ${graph}  ${expected_result}
