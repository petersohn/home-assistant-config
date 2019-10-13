*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${motion_detector1} =  binary_sensor.motion_detector1
${motion_detector2} =  binary_sensor.motion_detector2
${switch} =            input_boolean.test_switch
${switch2} =            input_boolean.test_switch2
${enabler} =           test_enabler
${delay} =             1 min


*** Test Cases ***

Switch On For First Sensor
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  ${delay}

Switch On For Second Sensor
    Set State  ${motion_detector2}  on
    Set State  ${motion_detector2}  off
    State Should Be  ${switch}  on
    State Should Change In  ${switch}  off  ${delay}

Switch Off After All Motion Stops
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector2}  on
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector2}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  1 min 50 sec

Switch Off After Motion Restarts
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  2 min

Do Not Start If Enabler Is Disabled
    Set Enabled State  ${enabler}  disable
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  off

Switch Off When Enabler Is Disabled
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  disable

    State Should Change At  ${switch}  on  30 sec
    State Should Change At  ${switch}  off  1 min

Switch On When Enabler Is Enabled While In Motion
    Set Enabled State  ${enabler}  disable
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  50 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  50 sec
    State Should Change At  ${switch}  off  2 min

Stop At Disabling And Restart After Enabling
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min 20 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  2 min 30 sec
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  2 min 40 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  2 min 50 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   2 min 40 sec
    State Should Change At  ${switch}  off  3 min 50 sec

Stop At Disabling And Restart At Enabling While In Motion
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler}  disable
    Schedule Call At  1 min
    ...    call_on_app  ${enabler}  enable
    Schedule Call At  1 min 30 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on   20 sec
    State Should Change At  ${switch}  off  30 sec
    State Should Change At  ${switch}  on   1 min
    State Should Change At  ${switch}  off  2 min 30 sec

Do Not Start On Disabled Sensor
    Set Enabled State  sensor_enabler1  disable
    Set Enabled State  sensor_enabler2  enable
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector2}  on
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector2}  off
    Schedule Call At  50 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch2}  on  30 sec
    State Should Change At  ${switch2}  off  1 min 40 sec

Start And Stop On Sensor Enabled Change
    Set Enabled State  sensor_enabler1  disable
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    call_on_app  sensor_enabler1  enable
    Schedule Call At  50 sec
    ...    call_on_app  sensor_enabler1  disable
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch2}  on  30 sec
    State Should Change At  ${switch2}  off  1 min 50 sec

Start And Stop On Sensor Enabled Change 2
    Set Enabled State  sensor_enabler1  disable
    Schedule Call At  20 sec
    ...    call_on_app  sensor_enabler1  enable
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  50 sec
    ...    call_on_app  sensor_enabler1  disable

    State Should Change At  ${switch2}  on  30 sec
    State Should Change At  ${switch2}  off  1 min 50 sec


*** Keywords ***

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${motion_detector1}=off
    ...    ${motion_detector2}=off
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  motion_sensor
    ...                     auto_switch  enabler
    ${app_configs} =  Create List  TestApp  MotionSensor
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
