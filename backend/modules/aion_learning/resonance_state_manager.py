#!/usr/bin/env python3
"""
Resonance State Manager
────────────────────────
Handles persistence for Gradient Correction Layer (GCL) state.
Stores running averages of resonance deltas and decay factors.

Path: data/predictive/resonance_state.json
"""

import json, time
from pathlib import Path

from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
from backend.modules.aion_learning.vault_store import AionLearningVaultStore

STATE_PATH = Path("data/predictive/resonance_state.json")

DEFAULT_STATE = {
    "avg_strength": 0.0,
    "decay_rate": 0.98,
    "update_count": 0,
    "timestamp": None,
}


class ResonanceStateManager:
    def __init__(
        self,
        path: Path | str | None = None,
        *,
        vault_store: AionLearningVaultStore | None = None,
        workspace_id: str | None = None,
    ):
        explicit_path = path is not None
        self.path = Path(path or STATE_PATH)
        self.vault_store = vault_store
        if vault_store is None and not explicit_path and guardian_mode_requested():
            self.vault_store = AionLearningVaultStore(workspace_id=workspace_id)
        self.state = DEFAULT_STATE.copy()
        self.load()

    # ─────────────────────────────────────────────
    # Load & Save
    # ─────────────────────────────────────────────
    def load(self):
        if self.vault_store is not None:
            payload = self.vault_store.get_state("resonance_state", DEFAULT_STATE.copy())
            self.state = payload if isinstance(payload, dict) else DEFAULT_STATE.copy()
        elif self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self.state = json.load(f)
            except Exception:
                print("⚠️ Corrupt resonance_state.json - using defaults.")
                self.state = DEFAULT_STATE.copy()

    def save(self):
        self.state["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.vault_store is not None:
            self.vault_store.put_state("resonance_state", self.state)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.state, f, indent=2)

    # ─────────────────────────────────────────────
    # Update Helpers
    # ─────────────────────────────────────────────
    def update(self, avg_strength: float, decay_rate: float):
        self.state["avg_strength"] = avg_strength
        self.state["decay_rate"] = decay_rate
        self.state["update_count"] += 1
        self.save()
