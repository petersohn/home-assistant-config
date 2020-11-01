from robot.libraries import DateTime


def convert_history_input(args):
    return [
        (DateTime.convert_date(args[i], result_format='timestamp'),
            args[i + 1])
        for i in range(0, len(args), 2)]


def convert_history_output(result):
    return [
        (DateTime.convert_date(date, result_format='timestamp'), int(value))
        for date, value in result]


def is_expected_history_found(converted_input, converted_output):
    return all(i in converted_output for i in converted_input)
