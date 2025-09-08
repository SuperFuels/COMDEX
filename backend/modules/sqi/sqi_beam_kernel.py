"""
sqi_beam_kernel.py
===================

Advanced Symbolic Quantum Intelligence (SQI) kernel processor for QWave beams.
Handles symbolic beam collapse, mutation, entanglement, scoring, and SoulLaw validation.
Optimized for GPU/SIMD parallelism with optional batch processing.
"""

import logging
from typing import List

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

# Optional: Enable GPU acceleration or SIMD backend
USE_PARALLELISM = True


def process_beams(beams: List[Beam]) -> List[Beam]:
    """
    Main entry point for beam processing:
    - Collapse wave state
    - Apply mutations
    - Score with SQI
    - Validate against SoulLaw
    - Broadcast or store results

    Returns processed list of beams with updated state.
    """
    processed_beams = []

    for beam in beams:
        try:
            logger.debug(f"[SQI] ⚛️ Processing beam: {beam.id}")

            # --- Collapse Phase ---
            collapse_result = collapse_wave_superposition(beam, use_gpu=USE_PARALLELISM)
            beam.collapsed_state = collapse_result
            beam.status = "collapsed"

            # --- Mutation Phase ---
            mutated_beam = mutate_beam(beam)
            mutated_beam.status = "mutated"

            # --- SQI Scoring Phase ---
            updated_container = inject_sqi_scores_into_container(mutated_beam.to_dict())

            # Overwrite mutated_beam.glyphs with updated ones (to get `sqi_score` added)
            mutated_beam.glyphs = updated_container.get("glyphs", [])

            # Set overall beam-level score (optional: average over all electrons)
            if mutated_beam.glyphs:
                scores = [g.get("sqi_score", 0.0) for g in mutated_beam.glyphs if g.get("type") == "electron"]
                mutated_beam.sqi_score = sum(scores) / len(scores) if scores else 0.0
            else:
                mutated_beam.sqi_score = 0.0

            # --- Drift Analysis ---
            drift_report = analyze_drift_patterns(mutated_beam.to_dict())
            mutated_beam.drift_signature = drift_report.get("signature")
            mutated_beam.drift_cost = drift_report.get("cost")

            # --- Entropy Calculation ---
            entropy = compute_entropy_metrics(mutated_beam)
            mutated_beam.entropy = entropy

            # --- SoulLaw Validation ---
            soul_validator = SoulLawValidator()
            avatar_state = getattr(mutated_beam, "avatar_state", {})
            container_metadata = getattr(mutated_beam, "container_metadata", {})

            avatar_allowed = soul_validator.validate_avatar_with_context(
                avatar_state, context={"beam_id": mutated_beam.id}
            )
            container_allowed = soul_validator.validate_container(container_metadata)

            mutated_beam.soullaw_status = "allowed" if (avatar_allowed and container_allowed) else "blocked"
            mutated_beam.soullaw_violations = [] if mutated_beam.soullaw_status == "allowed" else ["avatar", "container"]

            # --- Metadata + Hooks ---
            attach_symbolic_metadata(mutated_beam.to_dict())
            apply_qscore_hooks(mutated_beam.to_dict())

            # --- Collapse Logging + Registry ---
            register_beam_collapse(mutated_beam, mutated_beam.collapsed_state)
            store_collapsed_beam(mutated_beam, mutated_beam.to_dict())

            # --- HUD + Broadcast ---
            broadcast_beam_event(mutated_beam)

            # Prepare formatted values safely
            drift_str = f"{mutated_beam.drift_cost:.2f}" if mutated_beam.drift_cost is not None else "N/A"
            entropy_str = f"{entropy:.2f}" if entropy is not None else "N/A"
            sqi_score_str = f"{mutated_beam.sqi_score:.4f}" if hasattr(mutated_beam, "sqi_score") else "N/A"

            # Log beam processing summary
            logger.info(
                f"[SQI] ✅ Beam processed: {beam.id}, SQI={sqi_score_str}, "
                f"Drift={drift_str}, Entropy={entropy_str}, SoulLaw={mutated_beam.soullaw_status}"
            )

            processed_beams.append(mutated_beam)

        except Exception as e:
            logger.error(f"[SQI] ❌ Beam processing failed: {beam.id} — {e}", exc_info=True)
            beam.status = "error"
            processed_beams.append(beam)

    return processed_beams