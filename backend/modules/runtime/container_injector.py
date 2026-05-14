# File: backend/modules/runtime/container_injector.py

"""
container_injector.py
======================

Injects QWave beams into live containers (.dc format).
Handles symbolic merges, metadata embedding, and container re-entry logic.

Supports:
- Collapsed beam payload injection
- Reinjection hooks (for looping logic)
- Beam metadata tagging (origin, SQI score, timestamp)
- SoulLaw filter enforcement (if applicable)
"""

import logging
from datetime import datetime
from typing import Optional

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.dimensions.containers.container_loader import load_container_by_id
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.dna_chain.container_index_writer import get_active_container_ids

logger = logging.getLogger(__name__)


def inject_beam_into_container(beam: WaveState, container_id: Optional[str] = None) -> bool:
    """
    Injects beam into the specified container or selects one from the active pool.
    Returns True if successful.
    """
    try:
        # Determine target container
        cid = container_id or _resolve_target_container(beam)
        if not cid:
            logger.warning(f"[Injector] ⚠️ No target container found for beam {beam.id}")
            return False

        container = load_container_by_id(cid)
        if not container:
            logger.error(f"[Injector] ❌ Failed to load container {cid}")
            return False

        logger.debug(f"[Injector] 🧬 Injecting beam {beam.id} into container {cid}")

        # Prepare symbolic payload
        payload = {
            "beam_id": beam.id,
            "collapsed": beam.collapsed_state,
            "sqi_score": beam.sqi_score,
            "entropy": beam.entropy,
            "source": beam.origin or "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "status": beam.status,
            "soullaw": beam.soullaw_status,
        }

        # ✅ Inject into container prediction trace
        get_kg_writer().inject_prediction_trace(container, prediction_result=payload, origin="beam")

        # ✅ Enforce SoulLaw again post-injection (optional runtime pass)
        SoulLawValidator().validate_container(container)

        # ✅ Inject to Knowledge Graph (for fusion)
        inject_knowledge_graph_entry(beam.to_dict(), context={"container": cid})

        logger.info(f"[Injector] ✅ Beam {beam.id} injected into container {cid}")
        return True

    except Exception as e:
        logger.error(f"[Injector] ❌ Injection failed for beam {beam.id}: {e}", exc_info=True)
        return False


def _resolve_target_container(beam: WaveState) -> Optional[str]:
    """
    Heuristic to resolve best-fit container:
    - Use `beam.target_container_id` if specified
    - Otherwise choose from active containers
    """
    if hasattr(beam, "target_container_id"):
        return beam.target_container_id

    active = get_active_container_ids()
    if not active:
        return None
    return active[0]  # TODO: Improve with scoring / matching logic