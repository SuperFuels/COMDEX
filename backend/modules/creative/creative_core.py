import time
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

import os
password = os.environ.get("POSTGRES_PASSWORD")

from backend.modules.creative.symbolic_mutation_engine import mutate_symbolic_logic
from backend.modules.creative.innovation_scorer import compute_innovation_score
from backend.modules.creative.innovation_memory_tracker import track_innovation, log_event

from backend.modules.sqi.sqi_reasoning_module import log_sqi_drift
from backend.modules.codex.codex_metric import log_collapse_metric

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.carrier.carrier_types import CarrierType
from backend.modules.glyphwave.gwip.gwip_encoder import encode_gwip_packet
from backend.modules.websocket_manager import broadcast_event

from backend.modules.dna_chain.container_index_writer import add_innovation_score_entry

# Configuration
CREATIVE_BEAM_STYLE = CarrierType.FORK
MAX_FORKS = 5


def emit_creative_fork(
    original_wave: WaveState,
    symbolic_tree: Dict[str, Any],
    container_id: str,
    reason: Optional[str] = None
) -> List[WaveState]:
    """
    Emits creative forks from the original wave using symbolic mutation and innovation scoring.
    Each fork is tracked and broadcasted as a beam.
    """
    print(f"[CreativeCore] 🚀 Generating up to {MAX_FORKS} creative forks for container {container_id}...")

    try:
        mutated_versions = mutate_symbolic_logic(symbolic_tree, max_variants=MAX_FORKS)
    except Exception as e:
        print(f"[CreativeCore] ❌ Mutation failed: {e}")
        return []

    forks_emitted = []

    for i, mutated_tree in enumerate(mutated_versions):
        fork_id = str(uuid.uuid4())

        # 🧠 Step 1: Score innovation (using full compute function)
        try:
            score = compute_innovation_score(mutated_tree, mutated=True)
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Scoring failed for fork {i}: {e}")
            continue

        glow = round(score * 5, 2)        # Glow intensity scaling
        pulse = round(1 + (score * 4), 2) # Pulse frequency scaling

        # 🛠️ Step 2: Build fork wave
        fork_wave = WaveState(
            id=fork_id,
            container_id=container_id,
            source_wave_id=original_wave.id,
            mutation_type="creative_fork",
            mutation_cause=reason or "unknown",
            timestamp=time.time(),
            symbolic_tree=mutated_tree,
            coherence=original_wave.coherence * 0.95,
            glow_intensity=glow,
            pulse_frequency=pulse,
            carrier_type=CREATIVE_BEAM_STYLE,
            modulation_strategy="divergent"
        )

        # 🧬 Step 3: Track innovation lineage
        track_innovation(
            parent_wave=original_wave,
            fork_wave=fork_wave,
            score=score,
            cause=reason or "unknown"
        )

        # ✅ Step 3.1: Log innovation memory event
        try:
            log_event({
                "wave_id": fork_wave.id,
                "parent_wave_id": original_wave.id,
                "score": score,
                "container_id": container_id,
                "glow": glow,
                "pulse": pulse,
                "mutation_cause": reason or "unknown",
                "timestamp": fork_wave.timestamp
            })
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to log innovation memory: {e}")

        # 🗂️ Step 3.5: Persist to container index
        try:
            add_innovation_score_entry(
                wave_id=fork_wave.id,
                parent_wave_id=original_wave.id,
                score=score,
                glow=glow,
                pulse=pulse,
                cause=reason or "unknown",
            )
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to add innovation index entry: {e}")

        # 📊 Step 4: Log Codex + SQI metrics
        try:
            log_collapse_metric(container_id, fork_id, score, fork_wave.collapse_state)
            log_sqi_drift(container_id, fork_id, glow, pulse)
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Failed to log metrics: {e}")

        # 📡 Step 5: Encode for emission
        try:
            packet = encode_gwip_packet(
                wave=fork_wave,
                carrier_type=fork_wave.carrier_type,
                modulation_strategy=fork_wave.modulation_strategy,
                delay_ms=0
            )
        except Exception as e:
            print(f"[CreativeCore] ⚠️ Encoding failed: {e}")
            continue

        # 📦 Step 6: Assemble broadcast payload
        broadcast_payload = {
            "type": "creative_fork_beam",
            "wave_id": fork_wave.id,
            "parent_wave_id": original_wave.id,
            "carrier_packet": packet,
            "glow": glow,
            "pulse": pulse,
            "score": score,
            "mutation_cause": reason,
            "timestamp": fork_wave.timestamp,
        }

        forks_emitted.append(fork_wave)
        print(f"[CreativeCore] 📡 Emitting fork beam {fork_wave.id} (score={score:.3f})")

        # 🌐 Step 7: Send to GHX/WebSocket
        try:
            broadcast_event("glyphwave.fork_beam", broadcast_payload)
        except Exception as e:
            print(f"[CreativeCore] ⚠️ WebSocket broadcast failed: {e}")

    return forks_emitted