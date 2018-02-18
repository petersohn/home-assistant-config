*** Settings ***

Library  libraries/DateTimeUtil.py
Library  DateTime


*** Test Cases ***

To Time
    ${result} =  To Time  10:15:30
    Should Be Equal  ${result.hour}  ${10}
    Should Be Equal  ${result.minute}  ${15}
    Should Be Equal  ${result.second}  ${30}

Find Time On Same Day
    ${result} =  Find Time  2018-01-01 12:00:00  13:15:30
    ${result_string} =  Convert Date  ${result}  result_format=timestamp
    ${expected_result} =  Convert Date  2018-01-01 13:15:30  result_format=timestamp
    Should Be Equal  ${result_string}  ${expected_result}

Find Time On Next Day
    ${result} =  Find Time  2018-01-01 12:00:00  10:32:40
    ${result_string} =  Convert Date  ${result}  result_format=timestamp
    ${expected_result} =  Convert Date  2018-01-02 10:32:40  result_format=timestamp
    Should Be Equal  ${result_string}  ${expected_result}
