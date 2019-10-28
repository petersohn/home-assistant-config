*** Settings ***

Resource       resources/Config.robot
Resource       resources/Enabler.robot
Library        DateTime
Library        libraries/DateTimeUtil.py
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***
${in} =      sensor.furnace_in
${out} =     sensor.furnace_out
${target} =  input_boolean.temperature_controller_pump


*** Test Cases ***

Basic
    Set State  ${out}  ${25}
    State Should Be  ${target}  off
    Set State  ${out}  ${28}
    State Should Be  ${target}  off
    Set State  ${out}  ${30}
    State Should Be  ${target}  on
    Set State  ${out}  ${40}
    State Should Be  ${target}  on
    Set State  ${in}   ${33}
    State Should Be  ${target}  on
    Set State  ${in}   ${35}
    State Should Be  ${target}  on
    Set State  ${in}   ${37}
    State Should Be  ${target}  off
    Set State  ${out}  ${41}
    State Should Be  ${target}  off
    Set State  ${out}  ${42}
    State Should Be  ${target}  off
    Set State  ${out}  ${44}
    State Should Be  ${target}  on
    Set State  ${out}  ${79}
    State Should Be  ${target}  on
    Set State  ${in}   ${79}
    State Should Be  ${target}  off
    Set State  ${out}  ${80}
    State Should Be  ${target}  on
    Set State  ${in}   ${20}
    State Should Be  ${target}  on
    Set State  ${out}  ${28}
    State Should Be  ${target}  off


*** Keywords ***

Initialize
    Clean States
    Initialize States
    ...    ${in}=20
    ...    ${out}=20
    ...    ${target}=off
    ${apps} =  Create List  TestApp  locker  mutex_graph  temperature_basic
    ${app_configs} =  Create List  TestApp  TemperatureBasic
    Initialize AppDaemon  ${apps}  ${app_configs}  00:00:00
    Unblock For  ${appdaemon_interval}
