# File: backend/modules/creative/creative_core.py
import time
import uuid
import asyncio
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

import os
password = os.environ.get("POSTGRES_PASSWORD")  # kept (no code loss)

# --- SQI drift import (canonical → legacy → scorer → stub) ---
try:
    # ✅ canonical path
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import (
        log_sqi_drift,
    )
except Exception:
    try:
        from backend.modules.sqi.sqi_reasoning_module import log_sqi_drift  # legacy
    except Exception:
        try:
            from backend.modules.sqi.sqi_scorer import log_sqi_drift  # fallback
        except Exception:
            def log_sqi_drift(container_id: str, wave_id: str, glow: float, pulse: float) -> None:
                print(f"[SQI] (stub) Drift {wave_id} in {container_id} → glow={glow:.2f}, pulse={pulse:.2f}Hz")

# --- Carrier type import with graceful fallback ---
try:
    from backend.modules.glyphwave.carrier.carrier_types import CarrierType  # canonical
except Exception:
    class CarrierType:  # type: ignore
        SIMULATED = "simulated"
        FORK = "fork"  # provide FORK since code references it

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.gwip.gwip_encoder import encode_gwip_packet
from backend.modules.websocket_manager import broadcast_event

from backend.modules.creative.symbolic_mutation_engine import mutate_symbolic_logic
from backend.modules.creative.innovation_scorer import compute_innovation_score
from backend.modules.creative.innovation_memory_tracker import log_event  # centralized tracker

from backend.modules.dna_chain.container_index_writer import add_innovation_score_entry
from backend.modules.glyphwave.qwave.qwave_transfer_sender import send_qwave_transfer  # retained (no loss)
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload  # retained (no loss)
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update  # retained (no loss)

# --- Codex collapse metric import (canonical → legacy → stub) ---
try:
    from backend.modules.codex.codex_metrics import log_collapse_metric  # ✅ canonical
except Exception:
    try:
        from backend.modules.codex.codex_metric import log_collapse_metric  # legacy singular
    except Exception:
        def log_collapse_metric(container_id, wave_id, score, state):
            print(f"[CodexMetric] (stub) Beam {wave_id} in {container_id} → score={score:.3f}, state={state}")

from backend.modules.dna_chain.dna_switch import (
    is_self_growth_enabled,
    get_growth_factor,
)

# Configuration
CREATIVE_BEAM_STYLE = getattr(CarrierType, "FORK", getattr(CarrierType, "SIMULATED", "simulated"))
MAX_FORKS = 5


# --- small utility to safely dispatch coroutines from sync code ---
def _fire_and_forget(coro):
    """
    Schedule an async coroutine without requiring callers to manage an event loop.
    - If we're inside a running loop → create_task
    - If not → run it to completion in a fresh loop (simple/contained)
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def emit_creative_fork(
    original_wave: WaveState,
    symbolic_tree: Dict[str, Any],
    container_id: str,
    reason: Optional[str] = None
) -> List[WaveState]:
    """
    Emits creative forks from the original wave using symbolic mutation and innovation scoring.
    Each fork is tracked and broadcast as a beam.
    """

    # ---- DNA self-growth gating ----
    if not is_self_growth_enabled(container_id):
        print("[CreativeCore] 🧬 self_growth OFF — aborting fork emission")
        return []

    # Optional scaling via DNA (clamped for safety)
    growth_factor = get_growth_factor(container_id)
    # e.g., growth_factor=1 → MAX_FORKS; gf=2 → 2*MAX_FORKS; hard cap at 12 total
    local_max_forks = max(1, min(int(growth_factor) * MAX_FORKS, 12))

    print(f"[CreativeCore] 🚀 Generating up to {local_max_forks} creative forks for container {container_id}...")

    try:
        mutated_versions = mutate_symbolic_logic(symbolic_tree, max_variants=local_max_forks)
    except Exception as e:
        print(f"[CreativeCore] ❌ Mutation failed: {e}")
        return []

    forks_emitted: List[WaveState] = []

    # Resolve original wave id robustly (wave_id preferred; fall back to id if present)
    original_wave_id = getattr(original_wave, "wave_id", getattr(original_wave, "id", None))

    for i, mutated_tree in enumerate(mutated_versions):
        fork_id = str(uuid.uuid4())

        # 🧠 Step 1: Score innovation
        try:
            score = compute_innovation_score(mutated_tree, mutated=True)
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Scoring failed for fork {i}: {e}")
            continue

        glow = round(score * 5, 2)        # Glow intensity scaling
        pulse = round(1 + (score * 4), 2) # Pulse frequency scaling

        # Derive safe constructor fields
        base_carrier = getattr(original_wave, "carrier_type", CREATIVE_BEAM_STYLE)
        base_mod = "divergent"
        base_glyph_id = getattr(original_wave, "glyph_id", "fork")
        base_origin = list(getattr(original_wave, "origin_trace", [])) + ["creative_fork"]
        base_metadata = {
            "parent_wave_id": original_wave_id,
            "reason": reason or "unknown",
            "innovation_score": score,
        }

        # 🛠️ Step 2: Build fork wave using ONLY supported kwargs for WaveState.__init__
        fork_wave = WaveState(
            wave_id=fork_id,
            glyph_data={"mutated": True, "variant_index": i},
            glyph_id=base_glyph_id,
            carrier_type=base_carrier,
            modulation_strategy=base_mod,
            delay_ms=0,
            origin_trace=base_origin,
            metadata=base_metadata,
            container_id=container_id,
        )

        # Post-init: attach optional attributes (constructor doesn't accept these)
        setattr(fork_wave, "source_wave_id", original_wave_id)
        setattr(fork_wave, "symbolic_tree", mutated_tree)
        setattr(fork_wave, "coherence", getattr(original_wave, "coherence", 1.0) * 0.95)
        setattr(fork_wave, "glow_intensity", glow)
        setattr(fork_wave, "pulse_frequency", pulse)
        setattr(fork_wave, "mutation_type", "creative_fork")
        setattr(fork_wave, "mutation_cause", reason or "unknown")

        # ✅ ADD EARLY: track emitted forks regardless of downstream encoding/broadcast failures
        forks_emitted.append(fork_wave)

        # ✅ Step 3.1: Log innovation memory event (centralized tracker)
        try:
            log_event(
                container_id=container_id,
                beam_id=getattr(fork_wave, "wave_id", getattr(fork_wave, "id", None)),
                mutation_cause=reason or "unknown",
                innovation_scores={"innovation_score": float(score)},
                symbolic_snapshot=mutated_tree,
                metadata={
                    "glow": glow,
                    "pulse": pulse,
                    "parent_wave_id": original_wave_id,
                },
            )
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to log innovation memory: {e}")

        # 🗂️ Step 3.5: Persist to container index
        try:
            add_innovation_score_entry(
                wave_id=getattr(fork_wave, "wave_id", getattr(fork_wave, "id", None)),
                parent_wave_id=original_wave_id,
                score=score,
                glow=glow,
                pulse=pulse,
                cause=reason or "unknown",
            )
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to add innovation index entry: {e}")

        # 📊 Step 4: Log Codex + SQI metrics
        try:
            log_collapse_metric(
                container_id,
                fork_id,
                score,
                getattr(fork_wave, "collapse_state", "entangled"),
            )
            log_sqi_drift(container_id, fork_id, glow, pulse)
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to log metrics: {e}")

        # 📡 Step 5: Encode for emission (remove unsupported delay_ms)
        try:
            packet = encode_gwip_packet(
                wave=fork_wave,
                carrier_type=base_carrier,
                modulation_strategy=base_mod,
            )
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Encoding failed: {e}")
            # We already counted the fork; continue with next
            continue

        # 📦 Step 6: Assemble broadcast payload
        broadcast_payload = {
            "type": "creative_fork_beam",
            "wave_id": getattr(fork_wave, "wave_id", getattr(fork_wave, "id", None)),
            "parent_wave_id": original_wave_id,
            "carrier_packet": packet,
            "glow": glow,
            "pulse": pulse,
            "score": score,
            "mutation_cause": reason,
            "timestamp": getattr(fork_wave, "timestamp", time.time()),
        }

        # ✅ Step 7: Emit via GlyphWave/WebSocket — fire-and-forget to avoid await in sync fn
        print(f"[CreativeCore] 📡 Emitting fork beam {fork_id} (score={score:.3f})")
        try:
            _fire_and_forget(broadcast_event("glyphwave.fork_beam", broadcast_payload))
        except Exception as e:
            print(f"[CreativeCore] ⚠️ WebSocket broadcast failed: {e}")

        # ✅ Step 7.5: Realtime QWave Transfer (via emitter) — single, canonical call
        try:
            from backend.modules.gglyphwave.emitters.qwave_emitter import emit_qwave_beam  # NOTE: correct path is backend.modules.glyphwave.emitters...
        except Exception:
            from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam  # fallback to your existing canonical

        try:
            _fire_and_forget(emit_qwave_beam(
                wave=fork_wave,
                container_id=container_id,
                source="creative_core",
                metadata={
                    "innovation_score": score,
                    "glow": glow,
                    "pulse": pulse,
                    "reason": reason,
                }
            ))
        except Exception as e:
            print(f"[CreativeCore] ⚠️ QWave emitter failed: {e}")

    return forks_emitted