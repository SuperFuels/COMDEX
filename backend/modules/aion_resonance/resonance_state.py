# ==========================================================
# 🌐 AION Resonance State - Φ-state persistence layer
# ----------------------------------------------------------
# Safely loads/saves symbolic Φ metrics (coherence, entropy,
# flux, load) used by the cognitive feedback grid.
# ==========================================================

import json
import os
import time
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

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
def _store(
    *,
    state_path: str | Path | None = None,
    vault_store: AionLearningVaultStore | None = None,
) -> tuple[Path, AionLearningVaultStore]:
    path = Path(state_path or _STATE_PATH)
    return path, vault_store or AionLearningVaultStore(
        auto_configure=state_path is None
    )


def load_phi_state(
    *,
    state_path: str | Path | None = None,
    vault_store: AionLearningVaultStore | None = None,
):
    """Load the current Φ-state from disk safely, or restore defaults if corrupted."""
    path, store = _store(state_path=state_path, vault_store=vault_store)

    try:
        if store.enabled:
            data = store.get_state("aion_phi_state", None)
            if data is None:
                return _DEFAULT_STATE.copy()
        else:
            if not path.exists():
                return _DEFAULT_STATE.copy()
            with open(path, "r") as f:
                data = json.load(f)

        # Validate type and essential keys
        if not isinstance(data, dict) or not all(k in data for k in ["Φ_coherence", "Φ_entropy"]):
            raise ValueError("Invalid Φ-state structure")

        return data

    except json.JSONDecodeError as e:
        # Corrupted file - backup and restore defaults
        print(f"⚠️ Corrupted Φ-state: {e} - restoring default values.")
        try:
            backup_path = path.with_suffix(".corrupt.json")
            os.rename(path, backup_path)
            print(f"🩹 Saved corrupted backup -> {backup_path}")
        except Exception as rename_err:
            print(f"⚠️ Failed to backup corrupted Φ-state: {rename_err}")
        return _DEFAULT_STATE.copy()

    except Exception as e:
        print(f"⚠️ load_phi_state() failed: {e}")
        return _DEFAULT_STATE.copy()


# ──────────────────────────────────────────────────────────
# 💾 Atomic + robust save
# ──────────────────────────────────────────────────────────
def save_phi_state(
    phi_signature: dict,
    last_command: str = None,
    *,
    state_path: str | Path | None = None,
    vault_store: AionLearningVaultStore | None = None,
):
    """Atomically save the Φ signature with metadata, ensuring no partial writes."""
    path, store = _store(state_path=state_path, vault_store=vault_store)

    # Merge and enrich the state
    state = {**_DEFAULT_STATE, **phi_signature}
    state["last_command"] = last_command
    state["timestamp"] = time.time()

    if store.enabled:
        store.put_state("aion_phi_state", state)
        return state

    os.makedirs(path.parent, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")

    try:
        # Write atomically
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, path)
        return state

    except Exception as e:
        print(f"⚠️ Failed to save Φ-state: {e}")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return None


# ──────────────────────────────────────────────────────────
# 🔁 Manual reset / reinitialization
# ──────────────────────────────────────────────────────────
def reset_phi_state(
    *,
    state_path: str | Path | None = None,
    vault_store: AionLearningVaultStore | None = None,
):
    """Reset Φ metrics to their default balanced state."""
    save_phi_state(
        _DEFAULT_STATE.copy(),
        last_command="reset",
        state_path=state_path,
        vault_store=vault_store,
    )
    print("🧠 Φ-state reset to defaults.")
    return _DEFAULT_STATE.copy()
