# ──────────────────────────────────────────────
#  Tessaris * Cognitive Fabric Metrics Bridge
#  Stage 13.3 - Φ-ψ Coherence Telemetry Expansion
#  Adds derived coherence_energy + resonance tracking
#  Mirrors into CFA bus (guarded to avoid recursion)
# ──────────────────────────────────────────────

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class CodexMetrics:
    """
    Unified metrics recorder for Tessaris / Symatics systems.
    Writes JSONL telemetry and mirrors to the CFA bus.
    """

    def __init__(self, base_path: str = "data/metrics"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        self.metrics_path = os.path.join(self.base_path, "codex_metrics.jsonl")
        self.enable_logging = True
        self._in_commit = False         # recursion guard
        self._cache: List[Dict[str, Any]] = []

        logger.info(f"[CodexMetrics] Initialized -> {self.metrics_path}")

    # ──────────────────────────────────────────────
    #  Core Recording Interface
    # ──────────────────────────────────────────────
    def record_event(
        self,
        event: str,
        payload: Optional[Dict[str, Any]] = None,
        domain: str = "symatics/telemetry",
        tags: Optional[list[str]] = None,
    ) -> None:
        """
        Record a structured telemetry event locally and mirror to CFA bus.
        Automatically computes Φ-ψ coherence metrics if present,
        and ensures all data are JSON-serializable (NumPy / complex safe).
        """
        try:
            import numpy as np

            payload = payload or {}
            tags = tags or []
            ts = time.time()

            # 🔹 Derived metrics (Φ-ψ coherence)
            phi = payload.get("Φ_mean") or payload.get("phi_mean")
            psi = payload.get("ψ_mean") or payload.get("psi_mean")
            corr = payload.get("correlation")
            phase = payload.get("phase_diff")
            resi = payload.get("resonance_index")

            coherence_energy = (
                round(phi * psi * corr, 8)
                if all(v is not None for v in [phi, psi, corr])
                else None
            )

            record: Dict[str, Any] = {
                "timestamp": ts,
                "event": event,
                "domain": domain,
                "tags": tags,
                "payload": payload,
                "Φ_mean": phi,
                "ψ_mean": psi,
                "correlation": corr,
                "phase_diff": phase,
                "resonance_index": resi,
                "coherence_energy": coherence_energy,
            }

            # ──────────────────────────────────────────────
            # Safe serialization (NumPy + complex -> JSON-safe)
            # ──────────────────────────────────────────────
            def safe_convert(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, complex):
                    return {"real": obj.real, "imag": obj.imag}
                return obj

            with open(self.metrics_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=safe_convert) + "\n")

            # Cache retention
            self._cache.append(record)
            if len(self._cache) > 1000:
                self._cache.pop(0)

            if self.enable_logging:
                logger.debug(
                    f"[CodexMetrics] +{event} -> EΦψ={coherence_energy} ({domain})"
                )

            # 🧠 Mirror into CFA bus (guarded)
            if not self._in_commit:
                self._in_commit = True
                try:
                    from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

                    # sanitize None values before sending to CFA
                    cfa_payload = {
                        k: v for k, v in {
                            **payload,
                            "coherence_energy": coherence_energy,
                            "Φ_mean": phi,
                            "ψ_mean": psi,
                            "phase_diff": phase,
                            "resonance_index": resi,
                        }.items() if v is not None
                    }

                    CFA.commit(
                        source="CODEX_METRICS",
                        intent=event,
                        payload=cfa_payload,
                        domain=domain,
                        tags=tags or ["metrics", "telemetry"],
                    )

                except Exception as e:
                    logger.warning(f"[CodexMetrics] CFA commit failed: {e}")
                finally:
                    self._in_commit = False

        except Exception as e:
            logger.error(f"[CodexMetrics] Failed to record event: {e}")

    # ──────────────────────────────────────────────
    #  Backward-compatible Push Interface
    # ──────────────────────────────────────────────
    def push(self, operator: str, payload: Dict[str, Any]) -> None:
        """
        Compatibility alias used by ResonanceBridge and photonic operators (⊕, ⟲, ↔).
        Wraps record_event() for unified telemetry publishing.
        """
        try:
            event_name = f"RQC::{operator}"
            self.record_event(event_name, payload=payload, domain="photon_runtime")
            if self.enable_logging:
                logger.debug(f"[CodexMetrics] push({operator}) -> OK")
        except Exception as e:
            logger.warning(f"[CodexMetrics] push() failed for {operator}: {e}")

    # ──────────────────────────────────────────────
    #  Utility Methods
    # ──────────────────────────────────────────────
    def load_all(self) -> list[Dict[str, Any]]:
        """Return all stored metrics."""
        if not os.path.exists(self.metrics_path):
            return []
        with open(self.metrics_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def latest(self) -> Optional[Dict[str, Any]]:
        """Return the most recent metric event."""
        entries = self.load_all()
        return entries[-1] if entries else None

    def recent(self, n: int = 10) -> list[Dict[str, Any]]:
        """Return the last n events from memory cache."""
        return self._cache[-n:]


# ──────────────────────────────────────────────
#  Singleton Instance (for global CFA linkage)
# ──────────────────────────────────────────────
CODEX_METRICS = CodexMetrics()