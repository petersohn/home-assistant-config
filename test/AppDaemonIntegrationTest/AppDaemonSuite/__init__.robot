*** Settings ***

Library         libraries/mutex_graph.py
Library         OperatingSystem
Resource        resources/Config.robot
Resource        resources/HomeAssistant.robot
Resource        resources/AppDaemon.robot
Suite Setup     Run Keywords
...             Initialize Variables
...             Initialize Home Assistant
...             Initialize AppDaemon
Suite Teardown  Run Keywords
...             Cleanup AppDaemon
...             Cleanup Home Assistant
...             Check Global Mutex Graph
Variables       libraries/Directories.py
Test Timeout    3 min


*** Keywords ***

Initialize Variables
    ${global_mutex_graph} =  Create Dictionary
    Set Suite Variable  ${global_mutex_graph}  children=true

Check Global Mutex Graph
    ${graph_str} =  Format Graph  ${global_mutex_graph}  Global Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${global_mutex_graph}
    Should Be Equal  ${deadlock}  ${False}

