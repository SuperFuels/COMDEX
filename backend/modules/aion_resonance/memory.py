import json
from pathlib import Path
RKM_FILE = Path(__file__).parent / "boot_config.json"

def store_phi_mapping(intent, phi):
    try:
        data = json.load(open(RKM_FILE))
    except FileNotFoundError:
        data = {}
    data[intent] = phi
    json.dump(data, open(RKM_FILE, "w"), indent=2)