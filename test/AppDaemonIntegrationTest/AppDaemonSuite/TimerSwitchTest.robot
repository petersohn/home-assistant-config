*** Settings ***

Resource  resources/AppDaemon.robot
Resource  resources/HomeAssistant.robot
Resource  resources/Config.robot
Test Teardown  Unoad Apps Configs


*** Variables ***

${start_sensor}    binary_sensor.start
${control_switch}  input_boolean.control_switch


*** Test Cases ***

Control
    [Setup]  Initialize  TimerSwitchControl
    Watch Entities  ${control_switch}
    Set State  ${start_sensor}  on
    Set State  ${start_sensor}  off
    State Should Be  ${control_switch}  on
    Wait For History
    ...    ${control_switch}  on
    ...    ${control_switch}  off
    Check History
    ...    ${control_switch}  on
    ...    ${control_switch}  off


*** Keywords ***

Initialize
    [Arguments]  @{configs}
    Initialize States  ${start_sensor}=off
    Load Apps Configs  @{configs}
