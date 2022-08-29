*** Settings ***

Resource       resources/Config.robot
Library        Collections
Test Setup     Initialize
Test Teardown  Cleanup AppDaemon


*** Variables ***

${sensor} =    binary_sensor.test_input
${switch} =    input_boolean.test_switch
${off_icon} =  mdi:lightbulb-off
${on} =        mdi:lightbulb


*** Test Cases ***

Test Custom Icon


*** Keywords ***

Initialize
    Clean States And History
    Initialize States
    ...    ${sensor}=off
    ...    ${enabler}=off
    ${apps} =  Create List  TestApp  custom_icon
    ${app_configs} =  Create List  TestApp  CustomIcon
    Initialize AppDaemon  ${apps}  ${app_configs}
    Unblock For  ${appdaemon_interval}
