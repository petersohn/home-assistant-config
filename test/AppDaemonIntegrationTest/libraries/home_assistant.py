import json
import os
import yaml
import directories
from typing import Any


def create_home_assistant_configuration(target_directory: str, port: int):
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


def create_service_data(entity_id: str, value: str) -> tuple[str, str]:
    domain = entity_id[0 : entity_id.find(".")]
    data: dict[str, Any] = {"entity_id": entity_id}
    if domain in ["input_boolean", "switch"]:
        assert value in ["off", "on"]
        return "services/{}/turn_{}".format(domain, value), json.dumps(data)
    if domain == "input_select":
        data["option"] = value
        return "services/input_select/select_option", json.dumps(data)
    if domain in ["input_number", "input_text"]:
        data["value"] = value
        return "services/{}/set_value".format(domain), json.dumps(data)

    assert domain in ["sensor", "binary_sensor"]
    return "states/{}".format(entity_id), json.dumps({"state": value})
