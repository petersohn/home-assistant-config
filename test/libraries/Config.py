import os

import Directories


def get_base_output_directory():
    n = 1
    while True:
        result = os.path.join(Directories.output_path, str(n))
        if not os.path.exists(result):
            return result
        n += 1


def get_output_directory(base, suite_name, case_name):
    suite_path = suite_name.split('.')
    return os.path.join(base, *suite_path, case_name)
