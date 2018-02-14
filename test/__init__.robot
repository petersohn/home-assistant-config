*** Settings ***

Library      libraries/Config.py
Suite Setup  Initialize Variables


*** Keywords ***

Initialize Variables
    Set Suite Variable  ${start_time}  2018-01-01 12:00:00  children=true
    ${base_output_directory} =  Get Base Output Directory
    Set Suite Variable  ${base_output_directory}  children=true
    Set Suite Variable  ${appdaemon_interval}  ${1}  children=true
