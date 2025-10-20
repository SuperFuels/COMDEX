import json, os, time
from pathlib import Path

_STATE_PATH = Path(__file__).resolve().parents[2] / "state" / "resonance_state.json"

def load_phi_state():
    if not _STATE_PATH.exists():
        return {"Φ_load": 0.0, "Φ_flux": 0.0, "Φ_entropy": 0.0, "Φ_coherence": 1.0}
    with open(_STATE_PATH, "r") as f:
        return json.load(f)

def save_phi_state(phi_signature: dict, last_command: str = None):
    state = {**phi_signature, "last_command": last_command, "timestamp": time.time()}
    os.makedirs(_STATE_PATH.parent, exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    return state