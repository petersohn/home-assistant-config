*** Settings ***

Library        libraries/HistoryUtil.py
Library        Collections


*** Keywords ***

History Should Be
    [Arguments]  ${app}  @{expected_values}
    ${converted_expected_values} =  Convert History Input  ${expected_values}
    ${values} =  Call On App  ${app}  get_history
    ${converted_values} =  Convert History Output  ${values}
    Lists Should Be Equal  ${converted_values}  ${converted_expected_values}

Create History Manager
    [Arguments]  ${name}  ${entity}
    &{max_interval} =  Create Dictionary  hours=${1}
    ${history_manager} =  Create App  history  HistoryManager  ${name}
    ...    entity=${entity}  max_interval=${max_interval}
    RETURN  ${history_manager}
