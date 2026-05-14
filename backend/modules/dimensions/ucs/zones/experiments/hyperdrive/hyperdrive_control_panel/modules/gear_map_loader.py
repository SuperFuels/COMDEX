import os, json

GEAR_MAP_PATH = "backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/config/gear_map.json"

def load_gear_map():
    if not os.path.exists(GEAR_MAP_PATH):
        raise FileNotFoundError(f"⚠ Gear map config not found: {GEAR_MAP_PATH}")
    with open(GEAR_MAP_PATH, "r") as f:
        return json.load(f)

# ✅ Backward-compatible export for legacy imports
GEAR_MAP = load_gear_map()