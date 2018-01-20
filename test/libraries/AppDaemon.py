import os
import Directories


def create_appdaemon_configuration(target_directory, apps, app_configs):
    target = os.path.join(target_directory, 'appdaemon.yaml')
    apps_dir = os.path.join(target_directory, 'apps')
    with open(target, 'w') as config_file:
        pass

