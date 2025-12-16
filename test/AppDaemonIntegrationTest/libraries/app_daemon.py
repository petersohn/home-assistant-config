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

    modules: set[str] = set()

    def add_module(name: str) -> None:
        nonlocal modules

        assert type(name) == str
        modules.add(name + ".py")

    for data in content.values():
        if type(data) is not dict:
            continue

        global_dependencies = data.get("global_dependencies", [])
        if type(global_dependencies) is list:
            for module in global_dependencies:
                add_module(module)
        else:
            add_module(global_dependencies)

        module = data.get("module")
        if module is not None:
            add_module(module)

    for file_name in os.listdir(apps_dir):
        if not file_name.endswith(".py"):
            continue
        if not file_name in modules:
            os.remove(os.path.join(apps_dir, file_name))

    apps_path = os.path.join(directories.appdaemon_config_path, "apps")
    for file_name in modules:
        target_file = os.path.join(apps_dir, file_name)
        if os.path.exists(target_file):
            continue
        source_file = os.path.join(apps_path, file_name)
        os.symlink(source_file, target_file)

    all_apps = [
        name for name in content.keys() if name not in ["test", "locker"]
    ]

    with open(apps_yaml, "w") as target:
        yaml.dump(content, target)

    return all_apps
