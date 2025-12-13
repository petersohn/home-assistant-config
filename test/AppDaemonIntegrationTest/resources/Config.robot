*** Settings ***

Library   OperatingSystem
Library   libraries/AppDaemon.py
Library   libraries/mutex_graph.py
Resource  resources/HomeAssistant.robot
Resource  resources/AppDaemon.robot


*** Keywords ***

Setup Output Directory
    [Arguments]  ${suffix}=${Empty}
    Set Suite Variable  ${appdaemon_directory}
    ...    ${base_output_directory}/appdaemon
    ...    children=True
    Create Directory   ${appdaemon_directory}

Initialize AppDaemon
    Setup Output Directory
    Set Suite Variable  ${app_daemon_api_port}  ${home_assistant_port + 1}
    ...                 children=true
    Create AppDaemon Configuration  ${appdaemon_directory}  ${home_assistant_host}
    ...    ${app_daemon_api_port}
    Create AppDaemon Apps Config  ${appdaemon_directory}  TestApp
    Start AppDaemon
    Wait For App Daemon To Start

Cleanup AppDaemon
    Append And Check Mutex Graph
    Stop AppDaemon
    Wait For AppDaemon To Stop
    File Should Be Empty  ${appdaemon_directory}/appdaemon.stderr
    File Should Be Empty  ${appdaemon_directory}/error.log

Initialize Home Assistant
    Start Home Assistant
    Wait For Home Assistant To Start

Cleanup Home Assistant
    Stop Home Assistant
    Wait For Home Assistant To Stop

Load Apps Configs
    [Arguments]  @{configs}
    ${loaded_apps} =  Create AppDaemon Apps Config  ${appdaemon_directory}
    ...    TestApp  @{configs}
    Set Test Variable  ${loaded_apps}
    Create Http Context  ${app_daemon_host}
    Wait Until Keyword Succeeds  30s  0.1s
    ...    Apps Should Be Loaded  @{loaded_apps}

Unoad Apps Configs
    Create AppDaemon Apps Config  ${appdaemon_directory}  TestApp
    Wait Until Keyword Succeeds  30s  0.1s
    ...    Apps Should Be Unoaded  @{loaded_apps}
    Restore Http Context
   @{loaded_apps} =  Create List
