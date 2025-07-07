import json
import os

SWITCHBOARD_PATH = os.path.join(os.path.dirname(__file__), "modules_path_switch.json")

def load_path_switch():
    if not os.path.exists(SWITCHBOARD_PATH):
        return {}
    with open(SWITCHBOARD_PATH, "r") as f:
        return json.load(f)

def get_module_path(key):
    switch = load_path_switch()
    return switch.get(key)

def write_module_file(key, new_code):
    path = get_module_path(key)
    if not path:
        raise FileNotFoundError(f"No path found for key: {key}")
    
    # Backup existing file
    backup_path = path.replace(".py", "_OLD.py")
    if os.path.exists(path):
        with open(path, "r") as f:
            original_code = f.read()
        with open(backup_path, "w") as f:
            f.write(original_code)
    
    # Overwrite file with new code
    with open(path, "w") as f:
        f.write(new_code)

def read_module_file(key):
    path = get_module_path(key)
    if not path:
        raise FileNotFoundError(f"No path found for key: {key}")
    with open(path, "r") as f:
        return f.read()