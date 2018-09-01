*** Settings ***

Resource       resources/Config.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize  00:00:00
Test Teardown  Cleanup AppDaemon


*** Variables ***

${motion_detector1} =  binary_sensor.motion_detector1
${motion_detector2} =  binary_sensor.motion_detector2
${switch} =            input_boolean.motion_light
${enabler1} =          test_enabler1
${enabler2} =          test_enabler2
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

Do Not Start If One Enabler Is Disabled
    Disable  ${enabler1}
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  off

Do Not Start If Other Enabler Is Disabled
    Disable  ${enabler2}
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  off

Do Not Start If All Enablers Are Disabled
    Disable  ${enabler1}
    Disable  ${enabler2}
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  off

Do Not Restart After Disabling
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler1}  disable
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min 20 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  off  1 min 10 sec
    State Should Not Change  ${switch}  timeout=30 sec

Do Not Restart After Disabling While In Motion
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler1}  disable
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  1 min 50 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  2 min
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  1 min 40 sec
    State Should Not Change  ${switch}  deadline=2 min

Do Not Restart After Movement While Disabled And On
    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  50 sec
    ...    call_on_app  ${enabler1}  disable
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  20 sec
    State Should Change At  ${switch}  off  1 min 30 sec
    State Should Not Change  ${switch}  deadline=2 min

Restart After Enabling
    Disable  ${enabler1}

    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  50 sec
    ...    call_on_app  ${enabler1}  enable
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min 20 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  1 min 10 sec
    State Should Change At  ${switch}  off  2 min 20 sec

Restart After Enabling While In Motion
    Disable  ${enabler1}

    Schedule Call At  20 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  30 sec
    ...    call_on_app  ${enabler1}  enable
    Schedule Call At  40 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call At  1 min
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call At  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change At  ${switch}  on  1 min
    State Should Change At  ${switch}  off  2 min 10 sec


*** Keywords ***

Disable
    [Arguments]  ${enabler}
    Call Function  call_on_app  ${enabler}  disable

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${motion_detector1}=off
    ...    ${motion_detector2}=off
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  motion_sensor  auto_switch  enabler
    ${app_configs} =  Create List  TestApp  MotionSensor
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
