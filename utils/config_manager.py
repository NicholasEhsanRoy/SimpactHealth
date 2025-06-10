# utils/config_manager.py
import os
import yaml

CONFIGS_DIR = ".configs"

def ensure_configs_dir():
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)

def save_config(config_name, transitions_data):
    ensure_configs_dir()
    file_path = os.path.join(CONFIGS_DIR, f"{config_name}.yaml")
    with open(file_path, 'w') as f:
        yaml.dump(transitions_data, f, default_flow_style=False)

def load_config(config_name):
    ensure_configs_dir()
    file_path = os.path.join(CONFIGS_DIR, f"{config_name}.yaml")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    return None

def get_available_configs():
    ensure_configs_dir()
    return [f.replace('.yaml', '') for f in os.listdir(CONFIGS_DIR) if f.endswith('.yaml')]