import os
import time

import Directories


def get_output_directory(suite_name, case_name):
    suite_path = suite_name.split('.')
    return os.path.join(
        Directories.output_path,
        time.strftime('%Y-%m-%d %H:%M:%S'),
        *suite_path,
        case_name)
