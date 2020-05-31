import os


def get_output_directory(base, suite_name, case_name, suffix):
    suite_path = suite_name.split('.')
    result = os.path.join(base, *suite_path, case_name)
    if suffix:
        return os.path.join(result, suffix)
    else:
        return result
