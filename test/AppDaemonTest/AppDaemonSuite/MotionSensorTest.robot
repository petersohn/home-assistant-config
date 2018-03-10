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

Do Not Start At Daylight
    [Setup]  Initialize  ${before_sunset}

    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  off

Do Not Restart After Sun Rises
    [Setup]  Initialize  ${before_sunrise}
    Unblock Until Sunrise  -30 sec

    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  on
    Schedule Call In  1 min
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change In  ${switch}  off  1 min
    State Should Not Change  ${switch}  timeout=30 sec

Do Not Restart After Sun Rises While In Motion
    [Setup]  Initialize  ${before_sunrise}
    Unblock Until Sunrise  -30 sec

    Schedule Call In  10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call In  1 min 40 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  1 min 50 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change In  ${switch}  on  10 sec
    State Should Change In  ${switch}  off  1 min 20 sec
    State Should Not Change  ${switch}  timeout=1 min

Do Not Restart On Movement After Sun Rises While On
    [Setup]  Initialize  ${before_sunrise}
    Unblock Until Sunrise  -40 sec

    Schedule Call In  10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call In  1 min
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change In  ${switch}  on  10 sec
    State Should Change In  ${switch}  off  1 min 20 sec
    State Should Not Change  ${switch}  timeout=1 min

Restart After Sun Sets
    [Setup]  Initialize  ${before_sunset}
    Unblock Until Sunset  -40 sec

    Schedule Call In  10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  20 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call In  1 min
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  1 min 10 sec
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change In  ${switch}  on  1 min
    State Should Change In  ${switch}  off  1 min 10 sec

Restart After Sun Sets While In Motion
    [Setup]  Initialize  ${before_sunset}
    Unblock Until Sunset  -20 sec

    Schedule Call In  10 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  30 sec
    ...    set_sensor_state  ${motion_detector1}  off
    Schedule Call In  50 sec
    ...    set_sensor_state  ${motion_detector1}  on
    Schedule Call In  1 min
    ...    set_sensor_state  ${motion_detector1}  off

    State Should Change In  ${switch}  on  50 sec
    State Should Change In  ${switch}  off  1 min 10 sec


*** Keywords ***

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${motion_detector1}=off
    ...    ${motion_detector2}=off
    ...    ${switch}=off
    ${apps} =  Create List  TestApp  motion_sensor  auto_switch
    ${app_configs} =  Create List  TestApp  MotionSensor
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}
    Unblock For  ${appdaemon_interval}
