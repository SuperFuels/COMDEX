# File: backend/modules/runtime/pattern_engine_repair.py
"""
pattern_engine_repair.py
=========================

F3 Pattern Engine - Symbolic Resonance & Repair Layer
-----------------------------------------------------
Responsible for detecting coherence drift, resolving entangled container forks,
and restoring stable ψ-κ-T equilibrium in the UCS runtime.

Integrates:
    * UCSRuntime (container registry & atom index)
    * EntangledRuntimeForker (for branch lineage detection)
    * ObserverPathSelector (for collapse decisioning)
    * SQI Kernel metrics (for coherence scoring)
    * QQC Scheduler (for reinjection of stabilized beams)

Repair Cycle Phases:
    1. Detect drift (SQI < threshold or ψ-κ-T delta > ε)
    2. Identify entangled forks via lineage metadata
    3. Collapse or merge branches using ⟲ resonance
    4. Reinstate coherent container state in UCS
    5. Reinjection to QQC runtime (optional)
"""

import time
import logging
from typing import Dict, Any, List, Optional

from backend.modules.runtime.entangled_runtime_forker import EntangledRuntimeForker
from backend.modules.runtime.observer_path_selector import select_path_from_superposition
from backend.modules.runtime.beam_scheduler import global_scheduler
from backend.modules.runtime.beam_queue import add_beam
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime

logger = logging.getLogger("PatternRepair")


class PatternEngineRepair:
    def __init__(self, sqi_threshold: float = 0.85, psi_delta_threshold: float = 0.05):
        self.sqi_threshold = sqi_threshold
        self.psi_delta_threshold = psi_delta_threshold
        self.ucs = get_ucs_runtime()

    # ───────────────────────────────────────────────
    # 🔍 Detection
    # ───────────────────────────────────────────────
    def detect_drift(self, coherence: float, field_signature: Dict[str, Any]) -> bool:
        """
        Determine if symbolic coherence has dropped or ψ-κ-T drifted beyond tolerance.
        """
        psi_val = field_signature.get("psi", 0.0)
        drift_detected = coherence < self.sqi_threshold or abs(psi_val) > self.psi_delta_threshold
        if drift_detected:
            logger.warning(f"[Repair] Drift detected - coherence={coherence:.3f}, ψ={psi_val:.3f}")
        return drift_detected

    # ───────────────────────────────────────────────
    # 🧬 Fork Resolution
    # ───────────────────────────────────────────────
    def resolve_entangled_forks(self) -> List[Dict[str, Any]]:
        """
        Scan UCS containers for entangled forks and collapse them using observer bias.
        Returns list of merged container summaries.
        """
        repairs = []
        for cid, container in list(self.ucs.containers.items()):
            if not container.get("entangled"):
                continue

            origin = container.get("origin")
            glyph = container.get("glyph")
            coord = container.get("created_from")

            if not origin or not glyph:
                continue

            # Find sibling fork
            sibling_id = f"{origin}__qpath_{'1' if cid.endswith('0') else '0'}"
            sibling = self.ucs.containers.get(sibling_id)
            if not sibling:
                continue

            logger.info(f"[Repair] Found entangled pair: {cid} ↔ {sibling_id}")

            qglyph_pair = {
                "id": glyph,
                "left": container["cubes"][coord]["glyph"],
                "right": sibling["cubes"][coord]["glyph"],
            }

            decision = select_path_from_superposition(qglyph_pair, context={"origin": origin})
            chosen = decision.get("collapsed", container["cubes"][coord]["glyph"])

            # Collapse and recombine
            merged = self._merge_forks(origin, coord, glyph, chosen, [container, sibling])
            self.ucs.containers[origin] = merged
            repairs.append(merged)

            # Cleanup forked instances
            for fid in [cid, sibling_id]:
                if fid in self.ucs.containers:
                    self.ucs.remove_container(fid)

            logger.info(f"[Repair] Recombined forks into origin {origin} -> {chosen}")

        return repairs

    # ───────────────────────────────────────────────
    # 🌀 Merge Logic (⟲ Resonance)
    # ───────────────────────────────────────────────
    def _merge_forks(
        self,
        origin_id: str,
        coord: str,
        glyph: str,
        chosen: str,
        branches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Combine two entangled branches into a single coherent container using ⟲ resonance.
        """
        base = branches[0]
        merged = dict(base)
        merged["entangled"] = False
        merged["cubes"][coord]["glyph"] = chosen
        merged["metadata"]["repaired_from"] = [b["id"] for b in branches]
        merged["metadata"]["repaired_at"] = time.time()
        merged["metadata"]["repair_mode"] = "⟲ resonance"
        merged["coherence"] = 0.9
        return merged

    # ───────────────────────────────────────────────
    # ♻️ Reinjection
    # ───────────────────────────────────────────────
    def reinject_stabilized_beam(self, repaired_container: Dict[str, Any]) -> None:
        """
        Convert repaired container into a reinjected symbolic beam for reprocessing.
        Also registers beam in ENTANGLED_WAVE_STORE and emits GHX/QFC visualization event.
        """
        try:
            from backend.modules.glyphwave.core.wave_state import (
                WaveState,
                register_entangled_wave,
                ENTANGLED_WAVE_STORE,
            )
            from backend.modules.visualization.ghx_emitter import emit_ghx_event  # optional, safe import

            # 🧬 Construct repaired beam
            beam = WaveState(
                wave_id=f"beam_{repaired_container['id']}__r{int(time.time())}",
                coherence=repaired_container.get("coherence", 0.9),
                state="repaired",
                origin_trace=["pattern_repair"],
                metadata={
                    "source": "pattern_engine_repair",
                    "container_id": repaired_container["id"],
                    "repaired_at": time.time(),
                    "repair_mode": repaired_container.get("metadata", {}).get("repair_mode", "⟲ resonance"),
                },
                collapse_state="collapsed",
            )

            # ♻️ Add to beam queue + scheduler
            add_beam(beam)
            global_scheduler.schedule_beam(beam, priority=1)

            # 💾 Register in entangled wave memory for symbolic HUD sync
            register_entangled_wave(repaired_container["id"], beam)

            # 🌌 Optional GHX / QFC visualization event
            try:
                emit_ghx_event(
                    event_type="repair_reinjection",
                    payload={
                        "container_id": repaired_container["id"],
                        "beam_id": beam.wave_id,
                        "state": beam.state,
                        "coherence": beam.coherence,
                        "timestamp": beam.timestamp,
                    },
                )
            except Exception:
                pass  # GHX visualizer not active in test mode

            logger.info(f"[Repair] ♻️ Reinjected repaired beam {beam.wave_id}")
        except Exception as e:
            logger.error(f"[Repair] Failed to reinject beam: {e}")

    # ───────────────────────────────────────────────
    # 🧩 Full Cycle
    # ───────────────────────────────────────────────
    def run_repair_cycle(self, last_txn: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute full repair pass:
            - Detect drift
            - Resolve forks
            - Reinjection
        """
        try:
            coherence = (last_txn or {}).get("C_total", 1.0)
            field = (last_txn or {}).get("field_signature", {"psi": 0.0})

            if not self.detect_drift(coherence, field):
                return {"status": "stable", "repaired": False}

            forks = self.resolve_entangled_forks()
            for container in forks:
                self.reinject_stabilized_beam(container)

            if forks:
                logger.info(f"[Repair] Completed resonance repair for {len(forks)} forks")
                return {"status": "repaired", "count": len(forks), "restored": True}
            else:
                logger.warning("[Repair] No forks found during repair cycle")
                return {"status": "drift_detected", "restored": False}

        except Exception as e:
            logger.error(f"[Repair] Critical failure during repair cycle: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}