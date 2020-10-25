*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Teardown  Cleanup AppDaemon


*** Variables ***

${motion_detector} =   binary_sensor.motion_detector
${switch} =            input_boolean.test_switch
${switch2} =           input_boolean.test_switch2
${enabler} =           test_enabler
${time_entity} =       sensor.timer_switch_time


*** Test Cases ***

Switch On And Off Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Switch On And Off

Switch On And Off Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Switch On And Off

Switch Off After Motion Restarts Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Switch Off After Motion Restarts

Switch Off After Motion Restarts Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Switch Off After Motion Restarts

Do Not Start If Enabler Is Disabled Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Do Not Start If Enabler Is Disabled

Do Not Start If Enabler Is Disabled Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Do Not Start If Enabler Is Disabled

Switch Off When Enabler Is Disabled Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Switch Off When Enabler Is Disabled

Switch Off When Enabler Is Disabled Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Switch Off When Enabler Is Disabled

Switch On When Enabler Is Enabled While In Motion Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Switch On When Enabler Is Enabled While In Motion

Switch On When Enabler Is Enabled While In Motion Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Switch On When Enabler Is Enabled While In Motion

Stop At Disabling And Restart After Enabling Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Stop At Disabling And Restart After Enabling

Stop At Disabling And Restart After Enabling Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Stop At Disabling And Restart After Enabling

Stop At Disabling And Restart At Enabling While In Motion Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal
    Stop At Disabling And Restart At Enabling While In Motion

Stop At Disabling And Restart At Enabling While In Motion Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr
    Stop At Disabling And Restart At Enabling While In Motion

Start When Motion At Initialization Normal
    [Setup]  Initialize  00:00:00  TimerSwitchNormal  on
    Start When Motion At Initialization

Start When Motion At Initialization Expr
    [Setup]  Initialize  00:00:00  TimerSwitchExpr  on
    Start When Motion At Initialization

Timer Sequence
    [Setup]  Initialize  00:00:00  TimerSequence
    Set Enabled State  ${enabler}  disable
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  40 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  1 min 20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  1 min 40 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  3 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  5 min
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  5 min 30 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  5 min 40 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  6 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  6 min 10 sec
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   1 min 20 sec
    State Should Change At  ${switch}  off  2 min 20 sec
    State Should Change At  ${switch}  on   3 min
    State Should Change At  ${switch}  off  4 min
    State Should Change At  ${switch}  on   5 min 30 sec
    State Should Change At  ${switch}  off  6 min 30 sec

Multi Timer Sequence
    [Setup]  Initialize  00:00:00  TimerSequenceMultiSequence

    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  4 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  4 min 10 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  5 min 30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  5 min 40 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  6 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  6 min 10 sec
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At   ${switch}  on    20 sec
    State Should Change At   ${switch}  off   1 min 20 sec
    State Should Change Now  ${switch2}  on
    State Should Change At   ${switch2}  off  3 min 20 sec
    State Should Change At   ${switch}  on    4 min
    State Should Change At   ${switch}  off   5 min
    State Should Change Now  ${switch2}  on
    State Should Change At   ${switch2}  off  5 min 30 sec
    State Should Change At   ${switch}  on    6 min
    State Should Change At   ${switch}  off   7 min
    State Should Change Now  ${switch2}  on
    State Should Change At   ${switch2}  off  9 min

Other Target State
    [Setup]  Initialize  00:00:00  TimerSwitchInverted  on
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector}  on

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  1 min 50 s

Indirect Time
    [Setup]  Initialize  00:00:00  TimerSwitchIndirectTime
    Set State  ${time_entity}  1.5
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  3 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  3 min 20 sec
    ...    set_sensor_state  ${time_entity}  2
    Schedule Call At  3 min 30 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  6 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  6 min 10 s
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  6 min 20 sec
    ...    set_sensor_state  ${time_entity}  1
    Schedule Call At  9 min
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  9 min 10 s
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  2 min
    State Should Change At  ${switch}  on   3 min
    State Should Change At  ${switch}  off  5 min 30 sec
    State Should Change At  ${switch}  on   6 min
    State Should Change At  ${switch}  off  8 min 10 sec
    State Should Change At  ${switch}  on   9 min
    State Should Change At  ${switch}  off  10 min 10 sec


*** Keywords ***

Switch On And Off
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  1 min

Switch Off After Motion Restarts
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  2 min

Do Not Start If Enabler Is Disabled
    Set Enabled State  ${enabler}  disable
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  off

Switch Off When Enabler Is Disabled
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  disable

    State Should Change At  ${switch}  on  30 sec
    State Should Change At  ${switch}  off  1 min

Switch On When Enabler Is Enabled While In Motion
    Set Enabled State  ${enabler}  disable
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  50 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  on  50 sec
    State Should Change At  ${switch}  off  2 min

Stop At Disabling And Restart After Enabling
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  1 min 20 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  2 min 30 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  2 min 40 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  2 min 50 sec
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   2 min 40 sec
    State Should Change At  ${switch}  off  3 min 50 sec

Stop At Disabling And Restart At Enabling While In Motion
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min 30 sec
    ...    set_sensor_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   1 min
    State Should Change At  ${switch}  off  2 min 30 sec

Start When Motion At Initialization
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  off

    State Should Be  ${switch}  on
    State Should Change At  ${switch}  off  1 min 30 sec 30 sec

Initialize
    [Arguments]  ${start_time}  ${config}  ${sensor_state}=off
    Clean States
    Initialize States
    ...    ${motion_detector}=${sensor_state}
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  timer_switch
    ...                     auto_switch  enabler  expression
    ${app_configs} =  Create List  TestApp  TimerSwitchBase  ${config}
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
