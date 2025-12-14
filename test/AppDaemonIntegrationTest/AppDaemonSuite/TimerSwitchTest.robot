*** Settings ***

Resource  resources/AppDaemon.robot
Resource  resources/HomeAssistant.robot
Resource  resources/Config.robot
Test Teardown  Cleanup Apps Configs


*** Variables ***

${start_sensor}    binary_sensor.start
${enabler_switch}  binary_sensor.enabler_switch
${control_switch}  input_boolean.control_switch
${switch1}         input_boolean.test_switch1
${switch2}         input_boolean.test_switch2


*** Test Cases ***

Control
    [Setup]  Initialize  TimerSwitchControl
    Watch Entities  ${control_switch}
    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${control_switch}  off

Reload Because Of Dependency
    [Setup]  Initialize  TimerSwitchControl  TimerSequences  SwitchEnabler1
    Watch Entities  ${control_switch}  ${switch1}  ${switch2}
    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${switch2}  on
    ...    ${switch2}  off
    ...    ${control_switch}  off
    Set State  ${enabler_switch}  on
    Sleep  1
    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${switch1}  on
    ...    ${switch1}  off
    ...    ${control_switch}  off
    Set State  ${enabler_switch}  off
    Sleep  1
    Load Apps Configs  TimerSwitchControl  TimerSequences  SwitchEnabler2  dummy1
    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${switch1}  on
    ...    ${switch1}  off
    ...    ${control_switch}  off
    Set State  ${enabler_switch}  on
    Sleep  1
    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${switch2}  on
    ...    ${switch2}  off
    ...    ${control_switch}  off
    Set State  ${enabler_switch}  off


*** Keywords ***

Start Control And Wait
    Set State  ${start_sensor}  on
    Set State  ${start_sensor}  off
    State Should Be  ${control_switch}  on
    Wait For History
    ...    ${control_switch}  on
    ...    ${control_switch}  off

Initialize
    [Arguments]  @{configs}
    Initialize States
    ...    ${start_sensor}=off
    ...    ${enabler_switch}=off
    Initialize Apps Configs  @{configs}
