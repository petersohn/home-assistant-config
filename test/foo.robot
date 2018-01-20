*** Settings ***
Resource       resources/Config.robot
Test Setup     Initialize Environment
Test Teardown  Cleanup Environment

*** Test Cases ***

Foo
    List Directory  .
    Log  %{PWD}
