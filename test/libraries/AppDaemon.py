import os
import Directories


def create_appdaemon_configuration(target_directory, apps, app_configs):
    log_file = os.path.join(target_directory, 'appdaemon.log')
    error_file = os.path.join(target_directory, 'error.log')
    apps_dir = os.path.join(target_directory, 'apps')
    apps_yaml = os.path.join(target_directory, 'apps.yaml')
    secrets_yaml = os.path.join(target_directory, 'secrets.yaml')
    appdaemon_yaml = os.path.join(target_directory, 'appdaemon.yaml')

    source_appdaemon_yaml = os.path.join(
        Directories.appdaemon_config_path, 'appdaemon.yaml')

    os.makedirs(apps_dir)
    os.symlink(source_appdaemon_yaml, appdaemon_yaml)

    for app in apps:
        file_name = app + '.py'
        source_file = os.path.join(
            Directories.appdaemon_config_path, 'apps', file_name)
        target_file = os.path.join(apps_dir, file_name)
        os.symlink(source_file, target_file)

    with open(apps_yaml, 'w') as target:
        for config in app_configs:
            source_file = os.path.join(
                Directories.appdaemon_config_path, 'configs', config + '.yaml')
            with open(source_file, 'r') as source:
                target.write(source.read())

    with open(secrets_yaml, 'w') as secrets:
        secrets.write(
            'logfile: "' + log_file + '"\n'
            'errorfile: "' + error_file + '"\n')
