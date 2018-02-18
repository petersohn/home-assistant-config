*** Settings ***

Library   OperatingSystem
Library   libraries/AppDaemon.py
Library   libraries/Config.py
Resource  resources/HomeAssistant.robot
Resource  resources/AppDaemon.robot


*** Keywords ***

Setup Output Directory
    ${OUTPUT_DIRECTORY} =  Get Output Directory
    ...    ${base_output_directory}  ${SUITE_NAME}  ${TEST_NAME}
    Set Test Variable  ${OUTPUT_DIRECTORY}
    Create Directory   ${OUTPUT_DIRECTORY}

Initialize AppDaemon
    [Arguments]  ${apps}  ${app_configs}
    Setup Output Directory
    Start Home Assistant
    Create AppDaemon Configuration  ${OUTPUT_DIRECTORY}  ${apps}  ${app_configs}
    Start App Daemon
    Wait For App Daemon To Start

Cleanup AppDaemon
    Stop AppDaemon
    Wait For AppDaemon To Stop
    Clean States

Initialize Home Assistant
    Start Home Assistant
    Wait For Home Assistant To Start

Cleanup Home Assistant
    Stop Home Assistant
    Wait For Home Assistant To Stop
