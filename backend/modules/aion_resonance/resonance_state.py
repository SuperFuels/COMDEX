# ==========================================================
# 🌐 AION Resonance State — Φ-state persistence layer
# ----------------------------------------------------------
# Safely loads/saves symbolic Φ metrics (coherence, entropy,
# flux, load) used by the cognitive feedback grid.
# ==========================================================

import json
import os
import time
from pathlib import Path

_STATE_PATH = Path(__file__).resolve().parents[2] / "state" / "resonance_state.json"

_DEFAULT_STATE = {
    "Φ_load": 0.0,
    "Φ_flux": 0.0,
    "Φ_entropy": 0.0,
    "Φ_coherence": 1.0,
    "last_command": None,
    "timestamp": None,
}


# ──────────────────────────────────────────────────────────
# 🧩 Safe loader with corruption detection + recovery
# ──────────────────────────────────────────────────────────
def load_phi_state():
    """Load the current Φ-state from disk safely, or restore defaults if corrupted."""
    if not _STATE_PATH.exists():
        return _DEFAULT_STATE.copy()

    try:
        with open(_STATE_PATH, "r") as f:
            data = json.load(f)

        # Validate type and essential keys
        if not isinstance(data, dict) or not all(k in data for k in ["Φ_coherence", "Φ_entropy"]):
            raise ValueError("Invalid Φ-state structure")

        return data

    except json.JSONDecodeError as e:
        # Corrupted file — backup and restore defaults
        print(f"⚠️ Corrupted Φ-state: {e} — restoring default values.")
        try:
            backup_path = _STATE_PATH.with_suffix(".corrupt.json")
            os.rename(_STATE_PATH, backup_path)
            print(f"🩹 Saved corrupted backup → {backup_path}")
        except Exception as rename_err:
            print(f"⚠️ Failed to backup corrupted Φ-state: {rename_err}")
        return _DEFAULT_STATE.copy()

    except Exception as e:
        print(f"⚠️ load_phi_state() failed: {e}")
        return _DEFAULT_STATE.copy()


# ──────────────────────────────────────────────────────────
# 💾 Atomic + robust save
# ──────────────────────────────────────────────────────────
def save_phi_state(phi_signature: dict, last_command: str = None):
    """Atomically save the Φ signature with metadata, ensuring no partial writes."""
    os.makedirs(_STATE_PATH.parent, exist_ok=True)

    # Merge and enrich the state
    state = {**_DEFAULT_STATE, **phi_signature}
    state["last_command"] = last_command
    state["timestamp"] = time.time()

    tmp_path = _STATE_PATH.with_suffix(".tmp")

    try:
        # Write atomically
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, _STATE_PATH)
        return state

    except Exception as e:
        print(f"⚠️ Failed to save Φ-state: {e}")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return None


# ──────────────────────────────────────────────────────────
# 🔁 Manual reset / reinitialization
# ──────────────────────────────────────────────────────────
def reset_phi_state():
    """Reset Φ metrics to their default balanced state."""
    os.makedirs(_STATE_PATH.parent, exist_ok=True)
    save_phi_state(_DEFAULT_STATE.copy(), last_command="reset")
    print("🧠 Φ-state reset to defaults.")
    return _DEFAULT_STATE.copy()