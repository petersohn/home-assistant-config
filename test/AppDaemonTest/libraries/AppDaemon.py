import os
import yaml
import Directories


def create_appdaemon_configuration(
    target_directory, hass_host, api_port, apps, app_configs
):
    log_file = os.path.join(target_directory, "appdaemon.log")
    error_file = os.path.join(target_directory, "error.log")
    apps_dir = os.path.join(target_directory, "apps")
    apps_yaml = os.path.join(apps_dir, "apps.yaml")
    secrets_yaml = os.path.join(target_directory, "secrets.yaml")
    appdaemon_yaml = os.path.join(target_directory, "appdaemon.yaml")

    source_appdaemon_yaml = os.path.join(
        Directories.appdaemon_config_path, "appdaemon.yaml"
    )

    os.makedirs(apps_dir)
    os.symlink(source_appdaemon_yaml, appdaemon_yaml)

    for app in apps:
        file_name = app + ".py"
        source_file = os.path.join(Directories.appdaemon_config_path, "apps", file_name)
        target_file = os.path.join(apps_dir, file_name)
        os.symlink(source_file, target_file)

    content = {}
    global_modules = []
    for config in app_configs:
        source_file = os.path.join(
            Directories.appdaemon_config_path, "configs", config + ".yaml"
        )
        with open(source_file, "r") as source:
            content.update(yaml.safe_load(source))
        current_global = content.get("global_modules", [])
        if type(current_global) is list:
            global_modules.extend(current_global)
        else:
            global_modules.append(current_global)

    content["global_modules"] = global_modules
    content["test"]["dependencies"] = [
        name for name in content.keys() if name not in ["test", "global_modules"]
    ]

    with open(apps_yaml, "w") as target:
        yaml.dump(content, target)

    with open(secrets_yaml, "w") as secrets:
        yaml.dump(
            {
                "logfile": log_file,
                "errorfile": error_file,
                "url": "http://" + hass_host,
                "api_port": api_port,
            },
            secrets,
        )
