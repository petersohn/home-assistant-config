*** Settings ***

Library   OperatingSystem
Library   libraries/AppDaemon.py
Library   libraries/Config.py
Resource  resources/HomeAssistant.robot
Resource  resources/AppDaemon.robot


*** Keywords ***

Setup Output Directory
    ${OUTPUT_DIRECTORY} =  Get Output Directory  ${SUITE_NAME}  ${TEST_NAME}
    Set Test Variable  ${OUTPUT_DIRECTORY}
    Create Directory   ${OUTPUT_DIRECTORY}

Initialize Environment
    [Arguments]  ${apps}  ${app_configs}
    Setup Output Directory
    Start Home Assistant
    Create AppDaemon Configuration  ${OUTPUT_DIRECTORY}  ${apps}  ${app_configs}
    Wait For Home Assistant To Start
    Start App Daemon
    Wait For App Daemon To Start

Cleanup Environment
    Stop Home Assistant
    Stop AppDaemon
    Wait For Home Assistant To Stop
    Wait For AppDaemon To Stop
