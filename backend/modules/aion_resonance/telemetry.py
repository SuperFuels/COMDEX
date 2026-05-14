import json, time
from pathlib import Path
LOG_FILE = Path(__file__).parent / "telemetry.log"

def log_phi_event(label, phi):
    record = {
        "timestamp": time.time(),
        "label": label,
        **phi
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")