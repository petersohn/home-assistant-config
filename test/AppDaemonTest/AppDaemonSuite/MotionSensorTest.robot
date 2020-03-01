*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Teardown  Cleanup AppDaemon


*** Variables ***

${motion_detector} =   binary_sensor.motion_detector
${switch} =            input_boolean.test_switch
${enabler} =           test_enabler
${delay} =             1 min


*** Test Cases ***

Switch On And Off
    [Setup]  Initialize  00:00:00  MotionSensorNormal
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  ${delay}

Switch Off After Motion Restarts
    [Setup]  Initialize  00:00:00  MotionSensorNormal
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
    [Setup]  Initialize  00:00:00  MotionSensorNormal
    Set Enabled State  ${enabler}  disable
    Set State  ${motion_detector}  on
    Set State  ${motion_detector}  off
    State Should Be  ${switch}  off

Switch Off When Enabler Is Disabled
    [Setup]  Initialize  00:00:00  MotionSensorNormal
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector}  on
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector}  off
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  disable

    State Should Change At  ${switch}  on  30 sec
    State Should Change At  ${switch}  off  1 min

Switch On When Enabler Is Enabled While In Motion
    [Setup]  Initialize  00:00:00  MotionSensorNormal
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
    [Setup]  Initialize  00:00:00  MotionSensorNormal
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
    [Setup]  Initialize  00:00:00  MotionSensorNormal
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

Edge Trigger
    [Setup]  Initialize  00:00:00  MotionSensorEdgeTrigger
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

    State Should Change At  ${switch}  on   1 min 20 sec
    State Should Change At  ${switch}  off  2 min 20 sec
    State Should Change At  ${switch}  on   3 min
    State Should Change At  ${switch}  off  4 min


*** Keywords ***

Initialize
    [Arguments]  ${start_time}  ${config}
    Clean States
    Initialize States
    ...    ${motion_detector}=off
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  motion_sensor
    ...                     auto_switch  enabler
    ${app_configs} =  Create List  TestApp  MotionSensorBase  ${config}
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
