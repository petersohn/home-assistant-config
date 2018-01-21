*** Settings ***

Library   OperatingSystem
Library   libraries/Config.py
Resource  HomeAssistant.robot


*** Keywords ***

Setup Output Directory
    ${OUTPUT_DIRECTORY} =  Get Output Directory  ${SUITE_NAME}  ${TEST_NAME}
    Set Test Variable  ${OUTPUT_DIRECTORY}
    Create Directory   ${OUTPUT_DIRECTORY}

Initialize Environment
    Setup Output Directory
    Start Home Assistant
    Wait For Home Assistant To Start

Cleanup Environment
    Stop Home Assistant
    Wait For Home Assistant To Stop
