# File: backend/modules/aion_resonance/phi_drift_log.py
# 🧠 AION Φ-Drift Logger - tracks the temporal evolution of resonance fields.

import json, os, time
from datetime import datetime

DRIFT_PATH = "data/phi_drift_log.json"
MAX_ENTRIES = 5000  # prevent runaway growth


def _load_log():
    if not os.path.exists(DRIFT_PATH):
        return []
    try:
        with open(DRIFT_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_log(data):
    os.makedirs(os.path.dirname(DRIFT_PATH), exist_ok=True)
    with open(DRIFT_PATH, "w") as f:
        json.dump(data[-MAX_ENTRIES:], f, indent=2)


def record_phi_drift(keyword: str, phi_vector: dict):
    """Append a resonance snapshot to the drift log."""
    entry = {
        "timestamp": time.time(),
        "timestamp_readable": datetime.utcnow().isoformat(),
        "keyword": keyword,
        "Φ_load": phi_vector.get("Φ_load"),
        "Φ_flux": phi_vector.get("Φ_flux"),
        "Φ_entropy": phi_vector.get("Φ_entropy"),
        "Φ_coherence": phi_vector.get("Φ_coherence"),
    }
    data = _load_log()
    data.append(entry)
    _save_log(data)
    return entry


def get_drift_history(keyword: str = None, limit: int = 100):
    """Return the most recent drift entries, optionally filtered by keyword."""
    data = _load_log()
    if keyword:
        data = [d for d in data if d["keyword"] == keyword]
    return data[-limit:]