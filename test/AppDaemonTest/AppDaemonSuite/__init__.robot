*** Settings ***

Library         libraries/Config.py
Library         libraries/mutex_graph.py
Library         OperatingSystem
Resource        resources/Config.robot
Suite Setup     Run Keywords
...             Initialize Variables
...             Initialize Home Assistant
Suite Teardown  Run Keywords
...             Cleanup Home Assistant
...             Check Global Mutex Graph


*** Keywords ***

Initialize Variables
    Set Suite Variable  ${appdaemon_interval}  ${10}  children=true
    Set Suite Variable  ${default_start_date}  2018-01-01 00:00:00  children=true
    Set Suite Variable  ${before_sunrise}  07:20:00  children=true
    Set Suite Variable  ${before_sunset}  15:50:00  children=true

    ${base_output_directory} =  Get Base Output Directory
    Set Suite Variable  ${base_output_directory}  children=true
    Create Directory  ${base_output_directory}

    ${global_mutex_graph} =  Create Dictionary
    Set Suite Variable  ${global_mutex_graph}  children=true

Check Global Mutex Graph
    ${graph_str} =  Format Graph  ${global_mutex_graph}  Global Mutex Graph
    Log  ${graph_str}
    ${deadlock} =  Find Cycle  ${global_mutex_graph}
    Should Be Equal  ${deadlock}  ${False}
