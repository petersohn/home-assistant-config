*** Settings ***

Library         libraries/Config.py
Resource        resources/Config.robot
Suite Setup     Run Keywords
...             Initialize Variables
...             Initialize Home Assistant
Suite Teardown  Cleanup Home Assistant


*** Keywords ***

Initialize Variables
    Set Suite Variable  ${appdaemon_interval}  ${1}  children=true
    Set Suite Variable  ${start_time}  2018-01-01 12:00:00  children=true
    ${base_output_directory} =  Get Base Output Directory
    Set Suite Variable  ${base_output_directory}  children=true
