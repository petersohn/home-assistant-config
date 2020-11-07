*** Settings ***

Library   OperatingSystem
Library   libraries/AppDaemon.py
Library   libraries/Config.py
Library   libraries/mutex_graph.py
Resource  resources/HomeAssistant.robot
Resource  resources/AppDaemon.robot


*** Keywords ***

Setup Output Directory
    [Arguments]  ${suffix}=${Empty}
    ${index} =  Get Variable Value  ${PABOTQUEUEINDEX}  0
    ${OUTPUT_DIRECTORY} =  Get Output Directory
    ...    ${base_output_directory}/${index}/appdaemon
    ...    ${SUITE_NAME}  ${TEST_NAME}  ${suffix}
    Set Test Variable  ${OUTPUT_DIRECTORY}
    Create Directory   ${OUTPUT_DIRECTORY}

Initialize AppDaemon
    [Arguments]  ${apps}  ${app_configs}  ${start_time}=00:00:00
    ...    ${start_date}=${default_start_date}  ${suffix}=${Empty}
    Setup Output Directory  ${suffix}
    Set Suite Variable  ${app_daemon_api_port}  ${home_assistant_port + 1000}
    ...                 children=true
    Create AppDaemon Configuration  ${OUTPUT_DIRECTORY}  ${home_assistant_host}
    ...    ${app_daemon_api_port}  ${apps}  ${app_configs}
    Start App Daemon  ${start_time}  ${start_date}
    Wait For App Daemon To Start

Cleanup AppDaemon
    Append And Check Mutex Graph
    Stop AppDaemon
    Wait For AppDaemon To Stop

Initialize Home Assistant
    Start Home Assistant
    Wait For Home Assistant To Start

Cleanup Home Assistant
    Stop Home Assistant
    Wait For Home Assistant To Stop
