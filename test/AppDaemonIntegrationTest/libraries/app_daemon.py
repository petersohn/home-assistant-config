import os
import yaml
import directories
from typing import Any


def create_appdaemon_configuration(
    target_directory: str, hass_host: str, api_port: int
) -> None:
    log_file = os.path.join(target_directory, "appdaemon.log")
    error_file = os.path.join(target_directory, "error.log")
    secrets_yaml = os.path.join(target_directory, "secrets.yaml")
    appdaemon_yaml = os.path.join(target_directory, "appdaemon.yaml")

    source_appdaemon_yaml = os.path.join(
        directories.appdaemon_config_path, "appdaemon.yaml"
    )

    os.symlink(source_appdaemon_yaml, appdaemon_yaml)

    with open(secrets_yaml, "w") as secrets:
        yaml.dump(
            {
                "logfile": log_file,
                "errorfile": error_file,
                "hass_url": "http://" + hass_host,
                "api_url": "http://127.0.0.1:{}".format(api_port),
            },
            secrets,
        )

    apps_target_dir = os.path.join(target_directory, "apps")
    apps_source_dir = os.path.join(directories.appdaemon_config_path, "apps")
    os.makedirs(apps_target_dir, exist_ok=True)
    for file_name in os.listdir(apps_source_dir):
        if not file_name.endswith(".py"):
            continue

        target_file = os.path.join(apps_target_dir, file_name)
        source_file = os.path.join(apps_source_dir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(source_file, target_file)


def create_appdaemon_apps_config(
    target_directory: str, *app_configs: str
) -> list[str]:
    apps_dir = os.path.join(target_directory, "apps")
    apps_yaml = os.path.join(apps_dir, "apps.yaml")

    os.makedirs(apps_dir, exist_ok=True)

    content: dict[str, Any] = {}
    for config in app_configs:
        source_file = os.path.join(
            directories.appdaemon_config_path, "configs", config + ".yaml"
        )
        with open(source_file, "r") as source:
            content.update(yaml.safe_load(source))

    all_apps = [
        name for name in content.keys() if name not in ["test", "locker"]
    ]

    with open(apps_yaml, "w") as target:
        yaml.dump(content, target)

    return all_apps
