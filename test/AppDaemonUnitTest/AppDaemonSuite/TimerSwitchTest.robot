*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot
Resource       resources/History.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Create Test Harness
Test Teardown  Cleanup Test Harness


*** Variables ***

${motion_detector} =   binary_sensor.motion_detector
${sensor} =            sensor.test_sensor
${switch} =            input_boolean.test_switch
${switch2} =           input_boolean.test_switch2
${switch3} =           input_boolean.test_switch3
${time_entity} =       sensor.timer_switch_time


*** Test Cases ***

Switch On And Off Normal
    Switch On And Off  sensor=${motion_detector}

Switch On And Off Expr
    Switch On And Off  expr=v.${motion_detector}

Switch Off After Motion Restarts Normal
    Switch Off After Motion Restarts  sensor=${motion_detector}

Switch Off After Motion Restarts Expr
    Switch Off After Motion Restarts  expr=v.${motion_detector}

Do Not Start If Enabler Is Disabled Normal
    Do Not Start If Enabler Is Disabled  sensor=${motion_detector}

Do Not Start If Enabler Is Disabled Expr
    Do Not Start If Enabler Is Disabled  expr=v.${motion_detector}

Switch Off When Enabler Is Disabled Normal
    Switch Off When Enabler Is Disabled  sensor=${motion_detector}

Switch Off When Enabler Is Disabled Expr
    Switch Off When Enabler Is Disabled  expr=v.${motion_detector}

Switch On When Enabler Is Enabled While In Motion Normal
    Switch On When Enabler Is Enabled While In Motion  sensor=${motion_detector}

Switch On When Enabler Is Enabled While In Motion Expr
    Switch On When Enabler Is Enabled While In Motion  expr=v.${motion_detector}

Stop At Disabling And Restart After Enabling Normal
    Stop At Disabling And Restart After Enabling  sensor=${motion_detector}

Stop At Disabling And Restart After Enabling Expr
    Stop At Disabling And Restart After Enabling  expr=v.${motion_detector}

Stop At Disabling And Restart At Enabling While In Motion Normal
    Stop At Disabling And Restart At Enabling While In Motion  sensor=${motion_detector}

Stop At Disabling And Restart At Enabling While In Motion Expr
    Stop At Disabling And Restart At Enabling While In Motion  expr=v.${motion_detector}

Start When Motion At Initialization Normal
    Start When Motion At Initialization  sensor=${motion_detector}

Start When Motion At Initialization Expr
    Start When Motion At Initialization  expr=v.${motion_detector}

Delay Normal
    Delay  sensor=${motion_detector}

Delay Expr
    Delay  expr=v.${motion_detector}

Timer Sequence
    Create Auto Switch  auto_switch  ${switch}
    @{targets} =  Create List  auto_switch
    &{item} =  Create Dictionary  targets=${targets}  time=1
    @{sequence} =  Create List  ${item}
    ${enabler} =  Create Timer Sequence
    ...    sensor=${motion_detector}  sequence=${sequence}

    Set Enabled State  ${enabler}  disable
    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  40 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  50 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  1 min 20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  1 min 40 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  3 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  5 min
    ...    set_state  ${motion_detector}  off
    Schedule Call At  5 min 30 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  5 min 40 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  6 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  6 min 10 sec
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   1 min 20 sec
    State Should Change At  ${switch}  off  2 min 20 sec
    State Should Change At  ${switch}  on   3 min
    State Should Change At  ${switch}  off  4 min
    State Should Change At  ${switch}  on   5 min 30 sec
    State Should Change At  ${switch}  off  6 min 30 sec

Multi Timer Sequence
    Create Auto Switch  auto_switch1  ${switch}
    Create Auto Switch  auto_switch2  ${switch2}
    Create Auto Switch  auto_switch3  ${switch3}
    @{targets1} =  Create List  auto_switch1  auto_switch3
    &{item1} =  Create Dictionary  targets=${targets1}  time=1
    &{item2} =  Create Dictionary  time=3
    @{targets2} =  Create List  auto_switch2
    &{item3} =  Create Dictionary  targets=${targets2}  time=2
    @{sequence} =  Create List  ${item1}  ${item2}  ${item3}
    ${enabler} =  Create Timer Sequence
    ...    sensor=${motion_detector}  sequence=${sequence}


    ${switch1_history} =  Create History Manager  history1  ${switch}
    ${switch2_history} =  Create History Manager  history2  ${switch2}
    ${switch3_history} =  Create History Manager  history3  ${switch3}

    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  7 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  7 min 10 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  11 min 30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  11 min 40 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  12 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  12 min 10 sec
    ...    set_state  ${motion_detector}  off

    Advance Time To  19 min
    History Should Be  ${switch1_history}
    ...    2018-01-01 00:00:20  ${1}
    ...    2018-01-01 00:01:20  ${0}
    ...    2018-01-01 00:07:00  ${1}
    ...    2018-01-01 00:08:00  ${0}
    ...    2018-01-01 00:12:00  ${1}
    ...    2018-01-01 00:13:00  ${0}
    History Should Be  ${switch2_history}
    ...    2018-01-01 00:04:20  ${1}
    ...    2018-01-01 00:06:20  ${0}
    ...    2018-01-01 00:11:00  ${1}
    ...    2018-01-01 00:11:30  ${0}
    ...    2018-01-01 00:16:00  ${1}
    ...    2018-01-01 00:18:00  ${0}
    History Should Be  ${switch3_history}
    ...    2018-01-01 00:00:20  ${1}
    ...    2018-01-01 00:01:20  ${0}
    ...    2018-01-01 00:07:00  ${1}
    ...    2018-01-01 00:08:00  ${0}
    ...    2018-01-01 00:12:00  ${1}
    ...    2018-01-01 00:13:00  ${0}

Other Target State
    Set State  ${motion_detector}  on
    Create Timer Switch  time=${1}  sensor=${motion_detector}  target_state=off
    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  50 sec
    ...    set_state  ${motion_detector}  on

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  1 min 50 s

Indirect Time
    Create Timer Switch  time=${time_entity}  sensor=${motion_detector}
    Set State  ${time_entity}  1.5
    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  3 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  3 min 20 sec
    ...    set_state  ${time_entity}  2
    Schedule Call At  3 min 30 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  6 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  6 min 10 s
    ...    set_state  ${motion_detector}  off
    Schedule Call At  6 min 20 sec
    ...    set_state  ${time_entity}  1
    Schedule Call At  9 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  9 min 10 s
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  2 min
    State Should Change At  ${switch}  on   3 min
    State Should Change At  ${switch}  off  5 min 30 sec
    State Should Change At  ${switch}  on   6 min
    State Should Change At  ${switch}  off  8 min 10 sec
    State Should Change At  ${switch}  on   9 min
    State Should Change At  ${switch}  off  10 min 10 sec

Source State
    Create Auto Switch  auto_switch  ${switch}
    @{targets} =  Create List  auto_switch
    &{item} =  Create Dictionary  targets=${targets}  time=1
    @{sequence} =  Create List  ${item}
    ${enabler} =  Create Timer Sequence
    ...    sensor=${sensor}
    ...    sequence=${sequence}
    ...    source_state=foo
    ...    target_state=bar

    Set Enabled State  ${enabler}  enable
    Schedule Call At  20 sec
    ...    set_state  ${sensor}  foobar
    Schedule Call At  1 min
    ...    set_state  ${sensor}  bar
    Schedule Call At  2 min
    ...    set_state  ${sensor}  foo
    Schedule Call At  2 min 30 sec
    ...    set_state  ${sensor}  bar
    Schedule Call At  5 min
    ...    set_state  ${sensor}  foo
    Schedule Call At  6 min
    ...    set_state  ${sensor}  bar
    Schedule Call At  8 min
    ...    set_state  ${sensor}  foo
    Schedule Call At  8 min 10 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  8 min 20 sec
    ...    set_state  ${sensor}  foo
    Schedule Call At  8 min 30 sec
    ...    set_state  ${sensor}  bar
    Schedule Call At  8 min 50 sec
    ...    set_state  ${sensor}  foo
    Schedule Call At  9 min
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  10 min
    ...    set_state  ${sensor}  bar
    Schedule Call At  12 min
    ...    set_state  ${sensor}  foo
    Schedule Call At  13 min
    ...    set_state  ${sensor}  ${Empty}
    Schedule Call At  14 min
    ...    set_state  ${sensor}  bar
    Schedule Call At  15 min
    ...    set_state  ${sensor}  foo
    Schedule Call At  17 min
    ...    set_state  ${sensor}  bar

    State Should Change At  ${switch}  on   2 min 30 sec
    State Should Change At  ${switch}  off  3 min 30 sec
    State Should Change At  ${switch}  on   6 min
    State Should Change At  ${switch}  off  7 min
    State Should Change At  ${switch}  on   10 min
    State Should Change At  ${switch}  off  11 min
    State Should Change At  ${switch}  on   17 min
    State Should Change At  ${switch}  off  18 min

*** Keywords ***

Create Auto Switch
    [Arguments]  ${name}  ${target}
    ${auto_switch} =  Create App  auto_switch  AutoSwitch  ${name}
    ...    reentrant=${True}  target=${target}

Create Timer Switch
    [Arguments]  &{args}
    Create Auto Switch  auto_switch  ${switch}
    ${enabler} =  Create App  enabler  ScriptEnabler  enabler
    @{targets} =  Create List  auto_switch
    Create App  timer_switch  TimerSwitch  timer_switch
    ...    enabler=enabler  targets=${targets}  &{args} 
    RETURN  ${enabler}

Create Timer Sequence
    [Arguments]  &{args}
    ${enabler} =  Create App  enabler  ScriptEnabler  enabler
    Create App  timer_switch  TimerSequence  timer_sequence
    ...    enabler=enabler  &{args} 
    RETURN  ${enabler}

Switch On And Off
    [Arguments]  &{args}
    Create Timer Switch  time=${1}  &{args}

    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  1 min

Switch Off After Motion Restarts
    [Arguments]  &{args}
    Create Timer Switch  time=${1}  &{args}
    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  50 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  1 min
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  2 min

Do Not Start If Enabler Is Disabled
    [Arguments]  &{args}
    ${enabler} =  Create Timer Switch  time=${1}  &{args}

    Set Enabled State  ${enabler}  disable
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  off

Switch Off When Enabler Is Disabled
    [Arguments]  &{args}
    ${enabler} =  Create Timer Switch  time=${1}  &{args}

    Schedule Call At  30 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  40 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  disable

    State Should Change At  ${switch}  on  30 sec
    State Should Change At  ${switch}  off  1 min

Switch On When Enabler Is Enabled While In Motion
    [Arguments]  &{args}
    ${enabler} =  Create Timer Switch  time=${1}  &{args}
    Set Enabled State  ${enabler}  disable

    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  50 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on  50 sec
    State Should Change At  ${switch}  off  2 min

Stop At Disabling And Restart After Enabling
    [Arguments]  &{args}
    ${enabler} =  Create Timer Switch  time=${1}  &{args}

    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min 10 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  1 min 20 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  2 min 30 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  2 min 40 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  2 min 50 sec
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   2 min 40 sec
    State Should Change At  ${switch}  off  3 min 50 sec

Stop At Disabling And Restart At Enabling While In Motion
    [Arguments]  &{args}
    ${enabler} =  Create Timer Switch  time=${1}  &{args}

    Schedule Call At  20 sec
    ...    set_state  ${motion_detector}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min 30 sec
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   1 min
    State Should Change At  ${switch}  off  2 min 30 sec

Start When Motion At Initialization
    [Arguments]  &{args}
    Set State  ${motion_detector}  on
    Create Timer Switch  time=${1}  &{args}

    Schedule Call At  30 sec
    ...    set_state  ${motion_detector}  off

    State Should Be  ${switch}  on
    State Should Change At  ${switch}  off  1 min 30 sec

Delay
    [Arguments]  &{args}
    Create Timer Switch  time=${1}  delay=${30}  &{args}
    Schedule Call At  1 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  1 min 40 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  4 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  4 min 20 sec
    ...    set_state  ${motion_detector}  off
    Schedule Call At  5 min
    ...    set_state  ${motion_detector}  on
    Schedule Call At  6 min
    ...    set_state  ${motion_detector}  off

    State Should Change At  ${switch}  on   1 min 30 sec
    State Should Change At  ${switch}  off  2 min 40 sec
    State Should Change At  ${switch}  on   5 min 30 sec
    State Should Change At  ${switch}  off  7 min
