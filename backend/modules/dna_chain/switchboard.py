# File: backend/modules/dna_chain/switchboard.py

import json
import os
import datetime
from datetime import datetime, timezone

# ===== 🧠 Core DNA SWITCH Implementation =====

SWITCH_INDEX_PATH = os.path.join(os.path.dirname(__file__), "dna_switch_index.json")  # ✅ FIXED PATH
SWITCHBOARD_PATH = os.path.join(os.path.dirname(__file__), "modules_path_switch.json")

# In-memory registry
DNA_REGISTRY = {}

class DNASwitch:
    def __init__(self):
        self.registry = DNA_REGISTRY

    def register(self, file_path, type_hint="unspecified"):
        file_path = file_path.replace("\\", "/")
        now = datetime.now(timezone.utc).isoformat()
        dna_id = file_path.replace("/", ".").replace(".py", "").replace(".tsx", "")

        self.registry[file_path] = {
            "type": type_hint,
            "dna_id": dna_id,
            "registered": True,
            "last_modified": now,
            "switch": True,
        }

        self._write_registry()

    def _write_registry(self):
        with open(SWITCH_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=4)

    def get_registry(self):
        return self.registry

# ✅ Global DNA Switch Singleton
DNA_SWITCH = DNASwitch()

# ===== 🔁 Path Switchboard Utilities =====

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

# ===== ✅ FRONTEND DNA AUTO-REGISTRY =====

def register_frontend(tsx_path):
    DNA_SWITCH.register(tsx_path, type_hint="frontend_ui")

def auto_register_frontend_components(directory="frontend"):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".tsx"):
                path = os.path.join(root, file).replace("\\", "/")
                register_frontend(path)

# ✅ Trigger frontend auto-registration once
auto_register_frontend_components()