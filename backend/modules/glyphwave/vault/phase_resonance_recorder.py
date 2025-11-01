# backend/modules/vault/phase_resonance_recorder.py
"""
💡 Tessaris SRK-13.D4 - Phase-Locked Resonance Recorder
Records time-evolving photonic field metrics (amplitude, phase, coherence)
and persists them to GlyphVault or Photon Memory Grid (PMG).

This module forms the "light memory" foundation that feeds into the
Resonance Ledger (SRK-14) for temporal coherence analysis.
"""

import time
import json
import asyncio
import hashlib
from typing import Dict, Any, List
from backend.modules.encryption.glyph_vault import GlyphVault


class PhaseResonanceRecorder:
    def __init__(self, vault_dir: str = "vault/data"):
        self.records: List[Dict[str, Any]] = []
        self.vault = GlyphVault(vault_dir=vault_dir)
        self.start_time = None

    # ───────────────────────────────────────────────
    # Recording lifecycle
    # ───────────────────────────────────────────────
    def start(self):
        """Begin a new resonance recording session."""
        self.records.clear()
        self.start_time = time.time()

    def record_sample(self, amplitude: float, phase: float, coherence: float):
        """Capture one sample of the resonance state."""
        if self.start_time is None:
            self.start()
        t = time.time() - self.start_time
        self.records.append({
            "t": round(t, 6),
            "A": amplitude,
            "φ": phase,
            "C": coherence,
        })

    def stop(self) -> List[Dict[str, Any]]:
        """End recording and return the in-memory dataset."""
        data = self.records.copy()
        self.records.clear()
        self.start_time = None
        return data

    # ───────────────────────────────────────────────
    # Persistence and export
    # ───────────────────────────────────────────────
    async def persist_to_vault(self, capsule_id: str):
        """Asynchronously save recorded samples into GlyphVault."""
        if not self.records:
            return None

        payload = {
            "capsule_id": capsule_id,
            "timestamp": time.time(),
            "record_count": len(self.records),
            "resonance_trace": self.records,
        }
        encoded = json.dumps(payload, sort_keys=True).encode()
        checksum = hashlib.sha3_512(encoded).hexdigest()

        await asyncio.sleep(0.01)  # Simulated async persistence latency
        self.vault.save(capsule_id, {"payload": payload, "checksum": checksum})
        return {"capsule_id": capsule_id, "checksum": checksum, "count": len(self.records)}

    # ───────────────────────────────────────────────
    # Access helpers
    # ───────────────────────────────────────────────
    def load_trace(self, capsule_id: str) -> Dict[str, Any]:
        """Reload a previously saved resonance trace from the vault."""
        try:
            data = self.vault.load(capsule_id)
            return data.get("payload", {})
        except FileNotFoundError:
            return {}

    def latest_sample(self) -> Dict[str, Any]:
        """Return the most recent recorded sample, if any."""
        return self.records[-1] if self.records else {}