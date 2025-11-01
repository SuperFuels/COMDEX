# ===============================
# 📁 backend/modules/atomsheets/symatics_extension.py
# ===============================
from __future__ import annotations
from typing import Dict, Any
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms
from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU

# Defensive imports for Symatics core (if present)
try:
    from backend.modules.symatics.sym_wave_engine import compute_resonance_metrics
except Exception:
    def compute_resonance_metrics(cell):
        # fallback dummy metrics
        return {
            "Φ_mean": 1.0, "ψ_mean": 1.0,
            "correlation": 1.0,
            "phase_diff": 0.0,
            "resonance_index": 1.0,
            "coherence_energy": 1.0,
        }

# Optional GHX telemetry hook (if available)
try:
    from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY
except Exception:
    GHX_TELEMETRY = None


class SymaticQPU(CodexVirtualQPU):
    """
    Extension of CodexVirtualQPU that injects Φ-ψ resonance metrics
    into each execution cycle. Can be used as a drop-in replacement.
    """

    async def resonate_sheet(self, cells, ctx: Dict[str, Any]):
        results = await super().execute_sheet(cells, ctx)

        for c in cells:
            try:
                Φψ = compute_resonance_metrics(c)
                c.Φ_mean = Φψ.get("Φ_mean", 1.0)
                c.ψ_mean = Φψ.get("ψ_mean", 1.0)
                c.resonance_index = Φψ.get("resonance_index", 1.0)
                c.coherence_energy = Φψ.get("coherence_energy", 1.0)

                CODEX_METRICS.push(
                    "phi_psi_resonance",
                    domain="symatics/resonance_coupling",
                    payload=Φψ
                )
                if GHX_TELEMETRY:
                    GHX_TELEMETRY.emit("sheet_resonance", Φψ)

            except Exception as e:
                from backend.modules.patterns.pattern_trace_engine import record_trace
                record_trace("symatics", f"[ResonanceMetric Warn] {e}")

        return results


def compute_resonant_metrics_bulk(cells: Dict[str, Any]) -> None:
    """
    Compute and attach Φ-ψ resonance metrics to all cells.
    """
    for c in cells.values():
        try:
            Φψ = compute_resonance_metrics(c)
            setattr(c, "Φ_mean", Φψ.get("Φ_mean", 1.0))
            setattr(c, "ψ_mean", Φψ.get("ψ_mean", 1.0))
            setattr(c, "resonance_index", Φψ.get("resonance_index", 1.0))
            setattr(c, "coherence_energy", Φψ.get("coherence_energy", 1.0))
        except Exception:
            pass


def make_resonance_beam(sheet_id: str, Φψ: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a standardized sheet-level resonance beam.
    """
    return {
        "beam_id": f"beam_{sheet_id}_resonance_{now_utc_ms()}",
        "stage": "collapse",
        "token": "∇",
        "resonance": {
            "Φ_mean": Φψ.get("Φ_mean"),
            "ψ_mean": Φψ.get("ψ_mean"),
            "coherence_energy": Φψ.get("coherence_energy"),
        },
        "timestamp": now_utc_iso(),
    }