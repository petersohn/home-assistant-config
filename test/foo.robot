*** Settings ***
Resource       resources/Config.robot
Test Setup     Initialize
Test Teardown  Cleanup Environment

*** Test Cases ***

Foo
    List Directory  .
    Log  %{PWD}


*** Keywords ***

Initialize
    ${apps} =  Create List  TestApp
    ${app_configs} =  Create List  TestApp
    Initialize Environment  ${apps}  ${app_configs}
