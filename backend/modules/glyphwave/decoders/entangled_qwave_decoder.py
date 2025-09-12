# File: backend/modules/glyphwave/decoders/entangled_qwave_decoder.py

from typing import Dict, Any
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.sqi.sqi_scorer import score_all_electrons
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
from backend.modules.glyphwave.core.wave_state_store import WaveStateStore
from backend.modules.glyphwave.holographic.ghx_replay_broadcast import emit_entangled_replay

wave_store = WaveStateStore()


def decode_entangled_wave(entangled: EntangledWave, container_id: str, enable_qkd: bool = True) -> Dict[str, Any]:
    """
    Decode and collapse a full EntangledWave structure.
    Computes SQI, executes CodexLang if needed, and broadcasts QFC + GHX updates.
    """
    # Step 1: Collapse all waves using vectorized GPU kernel
    result = entangled.collapse_all()
    metrics = result.get("collapse_metrics", {})
    
    # Step 2: Score all electrons via SQI
    score_payload = score_all_electrons(entangled.waves)
    
    # Step 3: Execute CodexLang logic if present in each wave
    executor = CodexExecutor()
    predictions = []
    for wave in entangled.waves:
        if "codex" in wave.metadata:
            exec_result = executor.execute_expression(wave.metadata["codex"])
            predictions.append(exec_result)
            wave_store.cache_prediction(
                wave_id=wave.id,
                sqi_score=score_payload.get(wave.id, {}).get("sqi_score", 0.0),
                collapse_state=wave.collapse_state,
                prediction=exec_result
            )
        wave_store.add_wave(wave, carrier_type="entangled", modulation=entangled.mode)

    # Step 4: Emit visual replay and beam update
    emit_entangled_replay(entangled)
    qfc_payload = entangled.to_graph()
    broadcast_qfc_update(container_id, {
        "source": "entangled_qwave_decoder",
        "payload": {
            "type": "entangled_graph_update",
            "graph": qfc_payload,
            "collapse_metrics": metrics,
        }
    })

    return {
        "status": "decoded",
        "container_id": container_id,
        "collapse_metrics": metrics,
        "sqi_scores": score_payload,
        "predictions": predictions,
        "num_waves": len(entangled.waves),
    }