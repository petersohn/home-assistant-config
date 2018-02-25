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
${enabler} =           binary_sensor.motion_sensor_enable
${delay} =             1 min


*** Test Cases ***

Switch On For First Sensor
    Set State  ${motion_detector1}  on
    Set State  ${motion_detector1}  off
    State Should Be  ${switch}  on
    Unblock For  ${delay}
    State Should Be  ${switch}  off

Switch On For Second Sensor
    Set State  ${motion_detector2}  on
    Set State  ${motion_detector2}  off
    State Should Be  ${switch}  on
    Unblock For  ${delay}
    State Should Be  ${switch}  off


*** Keywords ***

Initialize
    [Arguments]  ${start_time}
    Clean States
    Initialize States
    ...    ${motion_detector1}=off
    ...    ${motion_detector2}=off
    ...    ${switch}=off
    ...    ${enabler}=on
    ${apps} =  Create List  TestApp  motion_sensor  auto_switch
    ${app_configs} =  Create List  TestApp  MotionSensor  DummyAutoSwitch
    Initialize AppDaemon  ${apps}  ${app_configs}  ${start_time}

