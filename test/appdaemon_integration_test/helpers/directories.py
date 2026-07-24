import os

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_path, "config")
hass_config_path = os.path.join(config_path, "hass")
appdaemon_config_path = os.path.join(config_path, "appdaemon")
