"""
beam_tick_loop.py
==================

Core scheduler loop for the A9 QWave Beam-Native Execution System.
Handles beam ingestion, SQI kernel processing, collapse/mutation,
GHX replay, symbolic tree projection, and re-entry support for
symbolic state machines with container injection and HUD sync.
"""

import time
import logging
import asyncio
from typing import List

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.runtime.beam_queue import get_active_beams, update_beam_state
from backend.modules.sqi.sqi_beam_kernel import process_beams
from backend.modules.codex.beam_callbacks import register_beam_callbacks
from backend.modules.glyphwave.core.beam_logger import log_beam_prediction
from backend.modules.runtime.container_injector import inject_beam_into_container
# from backend.modules.hud.codex_hud_interface import broadcast_beam_to_HUD
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree
from backend.modules.sqi.metrics.collapse_timeline_writer import log_collapse_event
from backend.modules.holograms.ghx_replay_broadcast import stream_symbolic_tree_replay

logger = logging.getLogger(__name__)

__all__ = ["beam_tick_loop", "get_last_tick_time"]

TICK_DURATION_SEC = 0.05
last_tick_time = 0.0  # For HUD sync, performance monitoring, etc.

def should_inject(beam: WaveState) -> bool:
    """Determines if a beam should be injected into a container."""
    return beam.status in ("pending", "ready", "mutated", "reinject")

def should_visualize(beam: WaveState) -> bool:
    """Determines if a beam should be visualized in the HUD."""
    return beam.status not in ("dormant", "archived")

def beam_tick_loop(beams: List[WaveState] = None, max_ticks: int = 1000, delay: float = TICK_DURATION_SEC, container_id: str = None):
    """
    Main symbolic QWave execution loop.

    For each tick:
    - Retrieve active beams
    - Process through SQI kernel
    - Update beam state (mutation, collapse, re-entry)
    - Inject into containers
    - Project to HUD
    - Emit symbolic tree via GHX
    - Log timeline collapse events
    """
    global last_tick_time
    logger.info("[QWave] 🚀 Starting beam tick loop")

    register_beam_callbacks()
    all_processed = []

    for tick in range(max_ticks):
        try:
            current_beams = beams if beams else get_active_beams()
            if not current_beams:
                time.sleep(delay)
                continue

            logger.debug(f"[QWave] 🔄 Tick {tick}: {len(current_beams)} active beams")
            processed = process_beams(current_beams)

            for beam in processed:
                beam.coherence = max(0.0, min(1.0, beam.coherence))  # Clamp

                update_beam_state(beam)
                log_beam_prediction(beam.to_dict())
                all_processed.append(beam)

                if should_inject(beam):
                    inject_beam_into_container(beam)

                # HUD projection (disabled unless module restored)
                try:
                    broadcast_beam_to_HUD(beam)  # Will be no-op unless module is restored
                except NameError:
                    pass

                # 🛰️ Emit GHX Replay
                try:
                    symbolic_tree = SymbolicMeaningTree.from_beam(beam)
                    if symbolic_tree:
                        asyncio.create_task(
                            stream_symbolic_tree_replay(symbolic_tree, beam.container_id or container_id or "test")
                        )
                except Exception as e:
                    logger.warning(f"[GHX] ⚠️ Failed to emit symbolic replay: {e}")

                # 🌌 Log collapse timeline
                try:
                    log_collapse_event(beam, tick, beam.container_id or container_id or "test")
                except Exception as e:
                    logger.warning(f"[Timeline] ⚠️ Failed to log collapse timeline: {e}")

            last_tick_time = time.time()
            time.sleep(delay)

        except KeyboardInterrupt:
            logger.warning("[QWave] ⏹️ Beam tick loop interrupted by user")
            break
        except Exception as e:
            logger.error(f"[QWave] ❌ Tick {tick} failed: {e}", exc_info=True)

    logger.info("[QWave] ✅ Beam tick loop complete")
    return all_processed

def get_last_tick_time() -> float:
    """Return last tick time (for metrics, HUD sync, or profiling)."""
    return last_tick_time