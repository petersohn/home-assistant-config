*** Settings ***

Library    Collections
Library    libraries/process_check.py


*** Keywords ***

Check For Leftover Process
    [Documentation]    Fails the test if any process whose command line matches
    ...                the given regex pattern is currently running. Intended
    ...                to detect processes left over from a previous test
    ...                execution. If any are found, their PID and command line
    ...                are logged at WARN level before the test fails.
    [Arguments]    ${description}    ${pattern}
    ${matches}    Find Processes Matching Cmdline    ${pattern}
    ${count}    Get Length    ${matches}
    IF    ${count} > 0
        FOR    ${match}    IN    @{matches}
            ${pid}    Get From List    ${match}    0
            ${cmdline}    Get From List    ${match}    1
            Log    Leftover ${description} process PID ${pid}: ${cmdline}    level=WARN
        END
        Fail    Found ${count} ${description} process(es) from a previous test run. See log for PIDs. Kill them before re-running.
    END
