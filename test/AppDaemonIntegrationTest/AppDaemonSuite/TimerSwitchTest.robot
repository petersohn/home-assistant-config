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
${switch3}         input_boolean.test_switch3


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

Only Reload Changed Apps
    [Setup]  Initialize  TimerSwitchControl  TimerSequenceNoEnabler1_1
    ...  TimerSequenceNoEnabler2
    Watch Entities  ${control_switch}  ${switch1}  ${switch2}  ${switch3}
    Start Control
    Wait For History  ${switch1}  on
    Load Apps Configs  TimerSwitchControl  TimerSequenceNoEnabler1_2
    ...  TimerSequenceNoEnabler2  dummy1
    Wait For Control
    Check History
    ...    ${control_switch}  on
    ...    ${switch2}  on
    ...    ${switch1}  on
    ...    ${switch1}  off
    ...    ${switch2}  off
    ...    ${control_switch}  off

    Start Control And Wait
    Check History
    ...    ${control_switch}  on
    ...    ${switch2}  on
    ...    ${switch3}  on
    ...    ${switch2}  off
    ...    ${switch3}  off
    ...    ${control_switch}  off


*** Keywords ***

Start Control
    Set State  ${start_sensor}  on
    Set State  ${start_sensor}  off
    State Should Be  ${control_switch}  on

Wait For Control
    Wait For History
    ...    ${control_switch}  on
    ...    ${control_switch}  off

Start Control And Wait
    Start Control
    Wait For Control

Initialize
    [Arguments]  @{configs}
    Initialize States
    ...    ${start_sensor}=off
    ...    ${enabler_switch}=off
    Initialize Apps Configs  @{configs}
