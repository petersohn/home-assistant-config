def convert_history_output(result: list[tuple[object, object]]) -> list[object]:
    return [i[1] for i in result]
