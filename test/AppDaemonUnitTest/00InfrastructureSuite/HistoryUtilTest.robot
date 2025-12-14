*** Settings ***

Library  libraries/history_util.py
Library  Collections


*** Test Cases ***

Test Convert History Input
    ${element1} =  Evaluate  ('2019-01-01 00:00:00.000', 3)
    ${element2} =  Evaluate  ('2019-02-03 01:21:04.000', 50)
    ${element3} =  Evaluate  ('2019-01-10 12:05:00.123', -1)
    ${expected_result} =  Create List  ${element1}  ${element2}  ${element3}
    ${input} =  Create List  2019-01-01                ${3}
    ...                      20190203T012104           ${50}
    ...                      2019-01-10 12:05:00.123   ${-1}
    ${result} =  Convert History Input  ${input}
    Should Be Equal  ${result}  ${expected_result}


Test Convert History Output
    ${result1} =  Evaluate  ('2019-01-01 00:00:00.000', 3)
    ${result2} =  Evaluate  ('2019-02-03 01:21:04.000', 50)
    ${result3} =  Evaluate  ('2019-01-10 12:05:00.123', -1)
    ${expected_result} =  Create List  ${result1}  ${result2}  ${result3}
    ${input1} =  Evaluate  (datetime.datetime(2019, 1, 1), 3.0)
    ...                    datetime
    ${input2} =  Evaluate  (datetime.datetime(2019, 2, 3, 1, 21, 4), 50.01)
    ...                    datetime
    ${input3} =  Evaluate  (datetime.datetime(2019, 1, 10, 12, 5, 0, 123000), -1.0)
    ...                    datetime
    ${input} =  Create List  ${input1}  ${input2}  ${input3}
    ${result} =  Convert History Output  ${input}
    Should Be Equal  ${result}  ${expected_result}
