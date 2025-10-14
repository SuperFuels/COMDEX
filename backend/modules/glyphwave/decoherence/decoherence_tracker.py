"""
🌀 Decoherence Tracker — SRK-13 Upgrade
Tracks coherence decay (ΔC), entropy drift (ΔS), and SQI dynamics for entangled wave systems.
"""

import hashlib
import time
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event


class DecoherenceTracker:
    def __init__(self):
        self.last_fingerprint = None
        self.last_coherence = {}
        self.history = {}

    # ───────────────────────────────────────────────
    def fingerprint(self, wave_state: dict) -> str:
        """Compute SHA3-512 fingerprint using amplitude, phase, and coherence."""
        key = f"{wave_state.get('amplitude')}|{wave_state.get('phase')}|{wave_state.get('coherence', 1.0)}|{wave_state.get('timestamp', time.time())}"
        fp = hashlib.sha3_512(key.encode()).hexdigest()
        self.last_fingerprint = fp
        return fp

    # ───────────────────────────────────────────────
    def track(self, entanglement_id: str, coherence: float):
        """
        Track coherence evolution for a given entanglement.
        Computes ΔC (drift) since last sample and logs SQI drift.
        """
        prev_c = self.last_coherence.get(entanglement_id, coherence)
        delta_c = round(coherence - prev_c, 6)
        self.last_coherence[entanglement_id] = coherence

        sqi_drift = (1 - coherence) ** 2
        self.history[entanglement_id] = {"ΔC": delta_c, "SQI_drift": sqi_drift, "timestamp": time.time()}

        log_soullaw_event(
            {
                "type": "decoherence_track",
                "entanglement_id": entanglement_id,
                "coherence": coherence,
                "ΔC": delta_c,
                "SQI_drift": sqi_drift,
                "timestamp": time.time(),
            },
            glyph=None,
        )

    # ───────────────────────────────────────────────
    def register_collapse(self, entanglement_id: str, coherence: float):
        """
        Register a collapse event when coherence drops below threshold.
        Computes ΔS from SQI history and emits a final decay signature.
        """
        record = self.history.get(entanglement_id, {})
        delta_s = abs(record.get("ΔC", 0.0)) * 0.01
        fingerprint = hashlib.sha3_512(f"{entanglement_id}|{coherence}|{delta_s}".encode()).hexdigest()

        log_soullaw_event(
            {
                "type": "collapse_event",
                "entanglement_id": entanglement_id,
                "final_coherence": coherence,
                "ΔS": delta_s,
                "fingerprint": fingerprint,
                "timestamp": time.time(),
            },
            glyph=None,
        )
        self.last_fingerprint = fingerprint