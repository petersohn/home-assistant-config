import os
import tempfile
import yaml
from appdaemon_integration_test.helpers import directories
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
                "url": "http://" + hass_host,
                "api_port": api_port,
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

    # Top-level .py modules at the root of the runtime apps dir (symlink to
    # prod). These are shared base modules imported by the app modules in
    # apps/, e.g. hass.py and callback_provider.py.
    for file_name in os.listdir(directories.prod_app_dir):
        if not file_name.endswith(".py"):
            continue
        target_file = os.path.join(apps_dir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(
            os.path.join(directories.prod_app_dir, file_name), target_file
        )

    # apps/ subdir — symlink each prod .py module
    apps_subdir = os.path.join(apps_dir, "apps")
    os.makedirs(apps_subdir, exist_ok=True)
    prod_apps_subdir = os.path.join(directories.prod_app_dir, "apps")
    for file_name in os.listdir(prod_apps_subdir):
        if not file_name.endswith(".py"):
            continue
        target_file = os.path.join(apps_subdir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(os.path.join(prod_apps_subdir, file_name), target_file)

    # test_apps/ subdir — symlink the test helper apps
    test_apps_subdir = os.path.join(apps_dir, "test_apps")
    os.makedirs(test_apps_subdir, exist_ok=True)
    for file_name in os.listdir(directories.test_apps_path):
        if not file_name.endswith(".py") or file_name == "__init__.py":
            continue
        target_file = os.path.join(test_apps_subdir, file_name)
        if os.path.exists(target_file):
            os.remove(target_file)
        os.symlink(
            os.path.join(directories.test_apps_path, file_name), target_file
        )

    all_apps = [
        name
        for name in content.keys()
        if name not in ["test", "locker"]
    ]

    fd, tmp = tempfile.mkstemp(
        dir=apps_dir, prefix=".apps.", suffix=".yaml"
    )
    with os.fdopen(fd, "w") as target:
        yaml.dump(content, target)
    os.replace(tmp, apps_yaml)

    return all_apps
