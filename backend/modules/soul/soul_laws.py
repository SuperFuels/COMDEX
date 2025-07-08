import yaml
import os

SOUL_LAWS_PATH = "backend/modules/soul/soul_laws.yaml"

def get_soul_laws():
    if not os.path.exists(SOUL_LAWS_PATH):
        return []
    with open(SOUL_LAWS_PATH, "r") as f:
        data = yaml.safe_load(f)
        return data.get("soul_laws", [])
