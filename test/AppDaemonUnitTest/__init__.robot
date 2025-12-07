*** Settings ***

Library         DateTime
Library         libraries/config.py
Library         apps/mutex_graph.py
Resource        resources/TestHarness.robot
Suite Setup     Run Keywords
...             Initialize Variables
Suite Teardown  Run Keywords
...             Check Global Mutex Graph
Test Timeout    10s


*** Keywords ***

Initialize Variables
    Set Suite Variable  ${default_start_date}  2018-01-01 00:00:00  children=true

    ${global_mutex_graph} =  Create Dictionary
    Set Suite Variable  ${global_mutex_graph}  children=true

Check Global Mutex Graph
    ${graph_str} =  Format Graph  ${global_mutex_graph}  Global Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${global_mutex_graph}
    Should Be Equal  ${deadlock}  ${False}
