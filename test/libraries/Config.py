import os

import Directories


def get_base_output_directory():
    n = 1
    while True:
        result = os.path.join(Directories.output_path, str(n))
        if not os.path.exists(result):
            return result
        n += 1


def get_output_directory(base, suite_name, case_name, suffix):
    suite_path = suite_name.split('.')
    result = os.path.join(base, *suite_path, case_name)
    if suffix:
        return os.path.join(result, suffix)
    else:
        return result
