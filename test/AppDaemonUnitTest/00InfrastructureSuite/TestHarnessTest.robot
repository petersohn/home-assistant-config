*** Settings ***

Library         DateTime
Resource        resources/TestHarness.robot
Resource        resources/DateTime.robot
Test Setup      Initialize  ${start_time}
Test Teardown   Cleanup Test Harness


*** Variables ***

${test_sensor} =                 sensor.test_sensor
${test_sensor2} =                sensor.test_sensor2
${test_sensor_value} =           sensor state
${intermediate_sensor_value} =   intermediate sensor state
${new_sensor_value} =            new sensor state
${start_time} =                  01:00:00
${alternate_start_time} =        21:30:00


*** Test Cases ***

Start Time
    Current Time Should Be  ${start_time}

Different Start Time
    [Setup]  Initialize  ${alternate_start_time}
    Current Time Should Be  ${alternate_start_time}

Set State
    Set State  ${test_sensor}  ${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

Set Attribute
    Set State  ${test_sensor}  foobar  a=attr1  b=attr2
    State Should Be  ${test_sensor}  foobar
    Attribute Should Be  ${test_sensor}  a  attr1
    Attribute Should Be  ${test_sensor}  b  attr2

Step
    Step
    Current Time Should Be  01:00:10
    Step
    Current Time Should Be  01:00:20

Advance Time
    Advance Time  2 min
    Current Time Should Be  01:02:00
    Advance Time  5 min
    Current Time Should Be  01:07:00

Advance Time To
    Advance Time To  01:05:00
    Current Time Should Be  01:05:00
    Advance Time To  01:10:00
    Current Time Should Be  01:10:00

Advance Time To Date Time
    ${unblock_time} =  Set Variable  2018-01-01 01:05:00
    Advance Time To Date Time  ${unblock_time}
    Current Time Should Be  01:05:00

Schedule State Change In Some Time
    Schedule Call In  2:00
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Advance Time  1:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Step
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Some Time
    Schedule Call At  01:10:00
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Advance Time To  01:09:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Step
    State Should Be  ${test_sensor}  ${new_sensor_value}

Schedule State Change At Exact Time
    Schedule Call At Date Time  2018-01-01 01:10:00
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Advance Time To  01:09:50
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Step
    State Should Be  ${test_sensor}  ${new_sensor_value}

Wait For State Change
    ${change_time} =  Set Variable  01:02:10
    Schedule Call At  ${change_time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Wait For State Change  ${test_sensor}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${change_time}

Wait For Later State Change
    ${change_time1} =  Set Variable  01:01:10
    ${change_time2} =  Set Variable  01:01:30
    Schedule Call At  ${change_time1}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Schedule Call At  ${change_time2}
    ...    set_state  ${test_sensor2}  ${new_sensor_value}
    Wait For State Change  ${test_sensor2}
    State Should Be  ${test_sensor2}  ${new_sensor_value}
    Current Time Should Be  ${change_time2}

Wait For State Change With Timeout
    Schedule Call In  1:50
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Wait For State Change  ${test_sensor}  timeout=1 min
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Current Time Should Be  01:01:00
    Wait For State Change  ${test_sensor}  timeout=1 min
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:01:50

Wait For State Change With Deadline
    Schedule Call At  01:01:50
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Wait For State Change  ${test_sensor}  deadline=01:01:00
    State Should Be  ${test_sensor}  ${test_sensor_value}
    Current Time Should Be  01:01:00
    Wait For State Change  ${test_sensor}  deadline=01:02:00
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:01:50

Wait For State Change With New State
    Schedule Call At  01:00:20
    ...    set_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:40
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Wait For State Change  ${test_sensor}  new=${new_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:40

Wait For State Change With Old State
    Schedule Call At  01:00:20
    ...    set_state  ${test_sensor}  ${intermediate_sensor_value}
    Schedule Call At  01:00:40
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Wait For State Change  ${test_sensor}  old=${intermediate_sensor_value}
    State Should Be  ${test_sensor}  ${new_sensor_value}

State Should Not Change For Some Time
    Schedule Call In  30 sec
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change For  ${test_sensor}  20 sec
    Current Time Should Be  01:00:20

State Should Not Change Until Some Time
    Schedule Call In  30 sec
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Not Change Until  ${test_sensor}  01:00:20
    Current Time Should Be  01:00:20

State Should Change In Some Time
    ${time} =  Set Variable  30 sec
    Schedule Call In  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Change In  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:30

State Should Change At Some Time
    ${time} =  Set Variable  01:01:00
    Schedule Call At  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${time}

State Should Change Next Day
    [Setup]  Initialize  ${alternate_start_time}  10 min
    ${time} =  Set Variable  01:00:00
    Schedule Call At  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Date Time Should Be  2018-01-02 ${time}

State Should Change In One Time Frame
    ${time} =  Set Variable  ${appdaemon_interval}
    Schedule Call In  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Change In  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  01:00:10

State Should Change At Next Time Frame
    ${time} =  Set Variable  01:00:10
    Schedule Call At  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    State Should Change At  ${test_sensor}  ${new_sensor_value}  ${time}
    State Should Be  ${test_sensor}  ${new_sensor_value}
    Current Time Should Be  ${time}

State Changes Too Early
    ${time} =  Set Variable  01:00:10
    ${expected} =  Add Time To Time  ${time}  ${appdaemon_interval}
    Schedule Call At  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Run Keyword And Expect Error  ${new_sensor_value} != ${test_sensor_value}
    ...    State Should Change At  ${test_sensor}  ${new_sensor_value}
    ...    ${expected}

State Changes Too Late
    ${expected} =  Set Variable  01:00:10
    ${time} =  Add Time To Time  ${expected}  ${appdaemon_interval}
    Schedule Call At  ${time}
    ...    set_state  ${test_sensor}  ${new_sensor_value}
    Run Keyword And Expect Error
    ...    *${test_sensor_value} != ${new_sensor_value}
    ...    State Should Change At  ${test_sensor}  ${new_sensor_value}
    ...    ${expected}

Converted State Expectations
    Set State  ${test_sensor}  12
    State Should Be As  ${test_sensor}  int  ${12}
#
*** Keywords ***

Initialize
    [Arguments]  ${start_time}  ${interval}=10 s
    Create Test Harness  start_time=${start_time}  interval=${interval}
    Set State  ${test_sensor}  ${test_sensor_value}
