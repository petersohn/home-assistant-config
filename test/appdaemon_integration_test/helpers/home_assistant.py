import json
import os
import yaml
from appdaemon_integration_test.helpers import directories


def create_home_assistant_configuration(target_directory: str, port: int) -> None:
    source_file = os.path.join(
        directories.hass_config_path, "configuration.yaml"
    )
    with open(source_file) as source:
        content = yaml.safe_load(source)
    os.makedirs(target_directory)
    target_file = os.path.join(target_directory, "configuration.yaml")
    with open(target_file, "w") as target:
        yaml.dump(content, target)

    # Seed the internal HTTP config store with the server port. The http: YAML
    # config section is deprecated in Home Assistant and will break in future
    # versions, so the server port is configured through .storage/http instead.
    # The stable slot holds the full HTTP storage schema (defaults filled in),
    # because the http component indexes into the active config directly.
    storage_dir = os.path.join(target_directory, ".storage")
    os.makedirs(storage_dir, exist_ok=True)
    http_store = {
        "version": 2,
        "minor_version": 2,
        "key": "http",
        "data": {
            "stable": {
                "server_port": port,
                "cors_allowed_origins": ["https://cast.home-assistant.io"],
                "login_attempts_threshold": -1,
                "ip_ban_enabled": True,
                "ssl_profile": "modern",
                "use_x_frame_options": True,
            },
            "pending": None,
            "yaml_migration_done": True,
        },
    }
    http_store_file = os.path.join(storage_dir, "http")
    with open(http_store_file, "w") as target:
        json.dump(http_store, target)


def create_service_data(entity_id: str, value: str) -> tuple[str, str]:
    domain = entity_id[0 : entity_id.find(".")]
    data: dict[str, object] = {"entity_id": entity_id}
    if domain in ["input_boolean", "switch"]:
        assert value in ["off", "on"]
        return f"services/{domain}/turn_{value}", json.dumps(data)
    if domain == "input_select":
        data["option"] = value
        return "services/input_select/select_option", json.dumps(data)
    if domain in ["input_number", "input_text"]:
        data["value"] = value
        return f"services/{domain}/set_value", json.dumps(data)

    assert domain in ["sensor", "binary_sensor"]
    return f"states/{entity_id}", json.dumps({"state": value})
