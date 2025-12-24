# ============================================================
# 📁 backend/modules/sqi/sqi_beam_kernel.py
# ============================================================

"""
SQIBeamKernel - symbolic quantum intelligence beam processing kernel.
Provides class-based orchestration for wave collapse, mutation, scoring,
SoulLaw validation, and QFC broadcast synchronization.
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.creative.symbolic_mutation_engine import mutate_beam
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.codex.beam_history import register_beam_collapse
from backend.modules.glyphwave.kernels.interference_kernel_core import collapse_wave_superposition
from backend.modules.codex.symbolic_entropy import compute_entropy_metrics
from backend.modules.glyphvault.beam_registry import store_collapsed_beam
from backend.modules.qfield.qfc_ws_broadcast import broadcast_beam_event
from backend.modules.codex.symbolic_metadata import attach_symbolic_metadata
from backend.modules.codex.symbolic_qscore_hooks import apply_qscore_hooks
from backend.modules.sqi.sqi_drift_analyzer import analyze_drift_patterns
from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container
from backend.modules.codex.beam_model import Beam

logger = logging.getLogger(__name__)

USE_PARALLELISM = True


# ──────────────────────────────────────────────
#  Functional implementation (for backward compat)
# ──────────────────────────────────────────────
def process_beams(beams: List[Beam]) -> List[Beam]:
    kernel = SQIBeamKernel()
    return kernel.process_batch(beams)


# ──────────────────────────────────────────────
#  Class Wrapper for QQC Integration
# ──────────────────────────────────────────────
class SQIBeamKernel:
    """
    Manages full SQI beam lifecycle:
    collapse -> mutate -> score -> validate -> broadcast.
    """

    def __init__(self, parallel: bool = True):
        self.parallel = parallel
        self.reasoner = SQIReasoningEngine()
        logger.info(f"[SQIBeamKernel] Initialized (parallel={self.parallel})")

    def propagate(self, beam_data: Dict[str, Any], sqi_score: Optional[float] = None) -> Dict[str, Any]:
        """
        QQC interface method.
        Accepts a symbolic beam dict, processes it internally,
        and returns a summarized beam state.
        """
        try:
            # --- 🔧 Auto-wrap legacy telemetry into physics ---
            if any(k in beam_data for k in ["beam_id", "coherence", "phase_shift", "entropy_drift", "gain", "timestamp"]):
                physics_block = {
                    "beam_id": beam_data.pop("beam_id", None),
                    "coherence": beam_data.pop("coherence", None),
                    "phase_shift": beam_data.pop("phase_shift", None),
                    "entropy_drift": beam_data.pop("entropy_drift", None),
                    "gain": beam_data.pop("gain", None),
                    "timestamp": beam_data.pop("timestamp", None),
                }
                beam_data["physics"] = physics_block

            # --- 🪶 Safe Beam construction ---
            beam = (
                Beam.from_dict(beam_data)
                if hasattr(Beam, "from_dict")
                else Beam(
                    id=f"beam-{uuid.uuid4()}",
                    logic_tree={},
                    glyphs=[],
                    phase=0.0,
                    amplitude=1.0,
                    coherence=1.0,
                    origin_trace="kernel:init"
                )
            )

            # --- ✅ Attach avatar + container context for SoulLaw ---
            ctx = beam_data.get("context", {})
            if not isinstance(ctx, dict):
                ctx = {}

            meta = beam_data.get("metadata", {})
            if isinstance(meta, dict) and isinstance(meta.get("context"), dict):
                # prefer metadata.context if present
                ctx = {**ctx, **meta["context"]}

            # Avatar state (what SoulLaw expects)
            try:
                from backend.modules.aion_core.avatar_state import AVATAR_STATE as CORE_AVATAR_STATE
            except Exception:
                CORE_AVATAR_STATE = {"id": "AION_CORE", "role": "root_cognitive_agent"}

            avatar_state = {
                **(CORE_AVATAR_STATE if isinstance(CORE_AVATAR_STATE, dict) else {}),
                "id": ctx.get("avatar_id")
                      or (CORE_AVATAR_STATE.get("id") if isinstance(CORE_AVATAR_STATE, dict) else "AION_CORE"),
                "avatar_state": ctx.get("avatar_state"),
                "avatar_state_ts": ctx.get("avatar_state_ts"),
                "container_id": ctx.get("container_id"),
            }

            # Container metadata (what SoulLaw expects)
            container_metadata = ctx.get("container_meta") if isinstance(ctx.get("container_meta"), dict) else {}
            if not container_metadata and ctx.get("container_id"):
                container_metadata = {
                    "id": ctx.get("container_id"),
                    "kind": ctx.get("container_kind", "qqc"),
                    "source": ctx.get("container_source", "qqc_kernel_boot"),
                }

            # Ensure attrs exist on Beam for _validate_soullaw()
            setattr(beam, "avatar_state", avatar_state)
            setattr(beam, "container_metadata", container_metadata)

            # --- Continue as usual ---
            results = self.process_batch([beam])
            processed = results[0] if results else None

            if processed:
                logger.info(
                    f"[SQIBeamKernel] ↯ Beam {processed.id} propagated "
                    f"(SQI={getattr(processed, 'sqi_score', 'N/A')})"
                )

                # --- ⚛️ Preserve internal physics but strip before Codex export ---
                beam_state = processed.to_dict() if hasattr(processed, "to_dict") else vars(processed)
                codex_payload = dict(beam_state)
                codex_payload.pop("physics", None)  # remove full physics block
                for k in ("amplitude", "coherence", "entropy", "phase", "drift_cost", "drift_signature"):
                    codex_payload.pop(k, None)

                # Optionally preserve snapshot for debug
                codex_payload["_physics_snapshot"] = beam_state.get("physics", {})

                return codex_payload

            return {"status": "empty"}

        except Exception as e:
            logger.error(f"[SQIBeamKernel] ❌ Beam propagation failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def process_batch(self, beams: List[Beam]) -> List[Beam]:
        """
        Main batch-processing logic for a list of beams.
        """
        processed_beams: List[Beam] = []
        for beam in beams:
            try:
                logger.debug(f"[SQI] ⚛️ Processing beam: {beam.id}")

                # --- Collapse Phase ---
                collapse_result = collapse_wave_superposition(beam, use_gpu=self.parallel)
                beam.collapsed_state = collapse_result
                beam.status = "collapsed"

                # --- Mutation Phase ---
                mutated = mutate_beam(beam)
                mutated.status = "mutated"

                # --- SQI Scoring Phase ---
                updated_container = inject_sqi_scores_into_container(mutated.to_dict())
                mutated.glyphs = updated_container.get("glyphs", [])
                mutated.sqi_score = self._average_sqi(mutated.glyphs)

                # --- Drift + Entropy ---
                drift_report = analyze_drift_patterns(mutated.to_dict())
                mutated.drift_signature = drift_report.get("signature")
                mutated.drift_cost = drift_report.get("cost")
                mutated.entropy = compute_entropy_metrics(mutated)

                # --- SoulLaw Validation ---
                self._validate_soullaw(mutated)

                # --- Metadata + Hooks ---
                attach_symbolic_metadata(mutated.to_dict())
                apply_qscore_hooks(mutated.to_dict())

                # --- Collapse Logging + Registry ---
                register_beam_collapse(mutated, mutated.collapsed_state)
                store_collapsed_beam(mutated, mutated.to_dict())

                # --- HUD + Broadcast ---
                broadcast_beam_event(mutated)

                logger.info(
                    f"[SQI] ✅ Beam processed: {beam.id} | "
                    f"SQI={(mutated.sqi_score or 0.0):.4f}, Drift={(mutated.drift_cost or 0.0):.2f}, "
                    f"Entropy={mutated.entropy:.2f}, SoulLaw={mutated.soullaw_status}"
                )

                processed_beams.append(mutated)

            except Exception as e:
                logger.error(f"[SQI] ❌ Beam processing failed: {beam.id} - {e}", exc_info=True)
                beam.status = "error"
                processed_beams.append(beam)

        return processed_beams

    # ──────────────────────────────
    #  Internal Utility Methods
    # ──────────────────────────────
    def _average_sqi(self, glyphs: List[Dict[str, Any]]) -> float:
        """Compute average SQI score for electron-type glyphs."""
        scores = [g.get("sqi_score", 0.0) for g in glyphs if g.get("type") == "electron"]
        return sum(scores) / len(scores) if scores else 0.0

    def _validate_soullaw(self, beam: Beam) -> None:
        """Run SoulLaw validation and annotate beam state."""
        import os

        # ✅ Dev-mode: always allow
        if os.getenv("SOULLAW_DEV_MODE") == "1":
            beam.soullaw_status = "allowed"
            beam.soullaw_violations = []
            return

        validator = SoulLawValidator()

        avatar_state = getattr(beam, "avatar_state", {})
        if not isinstance(avatar_state, dict):
            avatar_state = {}

        container_metadata = getattr(beam, "container_metadata", {})
        if not isinstance(container_metadata, dict):
            container_metadata = {}

        avatar_ok = validator.validate_avatar_with_context(
            avatar_state,
            context={"beam_id": beam.id, "container_id": container_metadata.get("id")},
        )
        container_ok = validator.validate_container(container_metadata)

        beam.soullaw_status = "allowed" if (avatar_ok and container_ok) else "blocked"
        beam.soullaw_violations = [] if beam.soullaw_status == "allowed" else ["avatar", "container"]