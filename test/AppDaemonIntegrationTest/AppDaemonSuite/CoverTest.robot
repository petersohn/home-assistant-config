*** Settings ***

Resource       resources/AppDaemon.robot
Resource       resources/Config.robot
Resource       resources/HistoryWatcher.robot
Resource       resources/Http.robot
Test Setup     Initialize  Cover1
Test Teardown  Cleanup Apps Configs


*** Variables ***

${input_entity1}         sensor.test_cover_position1
${input_entity2}         sensor.test_cover_position2
${output_entity}         input_number.cover_position
${availablility_entity}  sensor.cover_available
${mode_switch}           input_select.test_cover_mode
${cover}                 cover.test_cover


*** Test Cases ***

Simple State Changes
    Set State  ${input_entity1}  50
    Wait For History
    ...    ${mode_switch}  auto
    ...    ${mode_switch}  stable
    Check History
    ...    ${mode_switch}  auto
    ...    ${output_entity}  50.0
    ...    ${mode_switch}  stable
    Set State  ${input_entity1}  open
    Wait For History
    ...    ${mode_switch}  auto
    ...    ${mode_switch}  stable
    Check History
    ...    ${mode_switch}  auto
    ...    ${output_entity}  100.0
    ...    ${mode_switch}  stable
    Set State  ${input_entity1}  closed
    Wait For History
    ...    ${mode_switch}  auto
    ...    ${mode_switch}  stable
    Check History
    ...    ${mode_switch}  auto
    ...    ${output_entity}  0.0
    ...    ${mode_switch}  stable


Reload While Stable
    Set State  ${input_entity1}  60
    Set State  ${input_entity2}  40
    Wait For History
    ...    ${mode_switch}  auto
    ...    ${mode_switch}  stable
    Check History
    ...    ${mode_switch}  auto
    ...    ${output_entity}  60.0
    ...    ${mode_switch}  stable
    Load Apps Configs  HistoryWatcher  Cover2  dummy1


Reload While Manual
    Select Option  ${mode_switch}  manual
    Set State  ${input_entity2}  40
    Load Apps Configs  HistoryWatcher  Cover2  dummy1
    Sleep  3
    State Should Be  ${mode_switch}  manual
    State Should Be  ${output_entity}  0.0


*** Keywords ***

Initialize Services
    Call Service  cover/close_cover  entity_id=${cover}
    Select Option  ${mode_switch}  stable
    Wait For State  ${output_entity}  0.0
    Wait For State  ${cover}  closed

Initialize
    [Arguments]  @{configs}
    Initialize States
    ...    ${input_entity1}=0
    ...    ${input_entity2}=0
    ...    ${availablility_entity}=on
    Run In Http Context  ${app_daemon_host}  Initialize Services
    Initialize Apps Configs  HistoryWatcher  @{configs}
