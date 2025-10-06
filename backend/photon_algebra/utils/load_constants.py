import json, os

def load_constants(version="v1.2"):
    path = f"backend/modules/knowledge/constants_{version}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Constants file {path} not found. Run update_constants_registry.py first.")
    with open(path, "r") as f:
        data = json.load(f)
    return data["constants"]