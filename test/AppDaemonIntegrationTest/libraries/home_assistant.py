# import json
import os
import yaml
import directories


def create_home_assistant_configuration(target_directory, port):
    source_file = os.path.join(
        directories.hass_config_path, "configuration.yaml"
    )
    with open(source_file) as source:
        content = yaml.safe_load(source)
    content["http"]["server_port"] = port
    os.makedirs(target_directory)
    target_file = os.path.join(target_directory, "configuration.yaml")
    with open(target_file, "w") as target:
        yaml.dump(content, target)
