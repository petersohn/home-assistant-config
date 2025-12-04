*** Settings ***

Resource       resources/TestHarness.robot
Resource       resources/Enabler.robot
Test Setup     Initialize
Test Teardown  Cleanup Test Harness


*** Variables ***

${output1} =  input_boolean.test_switch
${output2} =  input_boolean.test_switch2
${enabler} =  test_enabler


*** Test Cases ***

Start With Off
    ${switch1}  ${switch2}  ${enabler}  ${enabled_switch} =
    ...    Create Basic Enabled Switch  ${False}
    State Should Be  ${output1}  off
    State Should Be  ${output2}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${output1}  on
    State Should Be  ${output2}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${output1}  off
    State Should Be  ${output2}  off

Start With On
    ${switch1}  ${switch2}  ${enabler}  ${enabled_switch} =
    ...    Create Basic Enabled Switch  ${True}
    State Should Be  ${output1}  on
    State Should Be  ${output2}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${output1}  off
    State Should Be  ${output2}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${output1}  on
    State Should Be  ${output2}  on

Guards
    ${on_guard}  ${off_guard}  ${switch}  ${enabler}  ${enabled_switch} =
    ...    Create Enabled Switch With Guards
    State Should Be  ${output1}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${output1}  off
    Set Enabled State  ${on_guard}  enable
    State Should Be  ${output1}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${output1}  on
    Set Enabled State  ${off_guard}  enable
    State Should Be  ${output1}  off
    Set Enabled State  ${enabler}  enable
    State Should Be  ${output1}  on
    Set Enabled State  ${enabler}  disable
    State Should Be  ${output1}  off

Turn Guards On And Off
    ${on_guard}  ${off_guard}  ${switch}  ${enabler}  ${enabled_switch} =
    ...    Create Enabled Switch With Guards
    State Should Be  ${output1}  off
    Set Enabled State  ${on_guard}  enable
    State Should Be  ${output1}  off
    Set Enabled State  ${on_guard}  disable
    State Should Be  ${output1}  off
    Set Enabled State  ${off_guard}  enable
    State Should Be  ${output1}  off
    Set Enabled State  ${off_guard}  disable
    State Should Be  ${output1}  off
    Set Enabled State  ${on_guard}  enable
    Set Enabled State  ${enabler}  enable
    State Should Be  ${output1}  on
    Set Enabled State  ${on_guard}  disable
    State Should Be  ${output1}  on
    Set Enabled State  ${off_guard}  enable
    State Should Be  ${output1}  on
    Set Enabled State  ${off_guard}  disable
    State Should Be  ${output1}  on
    Set Enabled State  ${off_guard}  enable
    Set Enabled State  ${enabler}  disable
    State Should Be  ${output1}  off


*** Keywords ***

Initialize
    Create Test Harness
    Set State  ${output1}  off
    Set State  ${output2}  off


Create Enabler And Switch
    [Arguments]  ${initial}  &{args}
    ${enabler} =  Create App  enabler  ScriptEnabler  enabler  initial=${initial}
    ${enabled_switch} =  Create App  enabled_switch  EnabledSwitch  enabled_switch
    ...    enabler=enabler  &{args}
    RETURN  ${enabler}  ${enabled_switch}


Create Basic Enabled Switch
    [Arguments]  ${initial}
    ${switch1} =  Create App  auto_switch  AutoSwitch  switch1  target=${output1}
    ${switch2} =  Create App  auto_switch  AutoSwitch  switch2  target=${output2}
    ${targets} =  Create List  switch1  switch2
    @{result} =  Create Enabler And Switch  ${initial}  targets=${targets}
    RETURN  ${switch1}  ${switch2}  @{result}


Create Enabled Switch With Guards
    ${on_guard} =  Create App  enabler  ScriptEnabler  on_guard  initial=${False}
    ${off_guard} =  Create App  enabler  ScriptEnabler  off_guard  initial=${False}
    ${switch} =  Create App  auto_switch  AutoSwitch  switch  target=${output1}
    ${targets} =  Create List  switch
    @{result} =  Create Enabler And Switch  ${False}
    ...    targets=${targets}  on_guard=on_guard  off_guard=off_guard
    RETURN  ${on_guard}  ${off_guard}  ${switch}  @{result}
