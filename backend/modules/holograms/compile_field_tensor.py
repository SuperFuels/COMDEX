# ──────────────────────────────────────────────
#  Tessaris * Field Tensor Compiler (SLE->HQCE Bridge)
#  Converts SLE telemetry & collapse traces -> normalized ψ-κ-T tensors
# ──────────────────────────────────────────────

import numpy as np
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Core Field Tensor Compiler
# ──────────────────────────────────────────────
def compile_field_tensor(telemetry: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Convert a block of SLE / collapse telemetry into a ψ-κ-T tensor signature.

    Expected telemetry fields:
      - drift_entropy: float       -> entropy drift per tick
      - resonance_curve: List[float] or float -> beam coherence curve
      - collapse_count: int        -> # of beam collapses in window
      - avg_coherence: float       -> mean field coherence
      - tick_time: float           -> runtime tick interval (s)
      - field_decay: float         -> coherence decay constant

    Returns:
        { "psi": ψ, "kappa": κ, "T": T, "coherence": C }
    """
    if not telemetry:
        logger.warning("[FieldTensorCompiler] No telemetry data provided.")
        return None

    drift_entropy = float(telemetry.get("drift_entropy", 0.0))
    collapse_count = float(telemetry.get("collapse_count", 0.0))
    avg_coherence = float(telemetry.get("avg_coherence", 0.5))
    tick_time = float(telemetry.get("tick_time", 1.0))
    field_decay = float(telemetry.get("field_decay", 1e-3))

    # Handle resonance curves from SLE if available
    resonance_curve = telemetry.get("resonance_curve", [])
    if isinstance(resonance_curve, (int, float)):
        resonance_curve = [float(resonance_curve)]
    resonance_curve = np.array(resonance_curve) if resonance_curve else np.zeros(1)
    curvature_estimate = np.tanh(len(resonance_curve) / 50.0)

    # ψ - symbolic wave energy (entropy-field)
    psi = max(0.0, min(1.0, 1.0 - drift_entropy))
    # κ - morphic curvature (from entanglement/resonance density)
    kappa = curvature_estimate * (1.0 - avg_coherence)
    # T - temporal coherence lifetime
    T = float(tick_time / max(field_decay, 1e-6))

    coherence = avg_coherence
    tensor = {"psi": psi, "kappa": kappa, "T": T, "coherence": coherence}

    logger.info(
        f"[FieldTensorCompiler] ψ={psi:.4f}, κ={kappa:.4f}, T={T:.4f}, C={coherence:.4f}"
    )
    return tensor

# ──────────────────────────────────────────────
#  Batch Telemetry Parser
# ──────────────────────────────────────────────
def compile_from_log(path: str) -> List[Dict[str, float]]:
    """
    Parse an SLE telemetry log (.json or .jsonl) into a sequence of ψ-κ-T tensors.
    Each line or entry represents one tick's telemetry snapshot.
    """
    tensors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".jsonl"):
                for line in f:
                    try:
                        telemetry = json.loads(line)
                        tensor = compile_field_tensor(telemetry)
                        if tensor:
                            tensors.append(tensor)
                    except Exception as e:
                        logger.warning(f"[FieldTensorCompiler] Skipping line: {e}")
            else:
                data = json.load(f)
                if isinstance(data, list):
                    for block in data:
                        tensor = compile_field_tensor(block)
                        if tensor:
                            tensors.append(tensor)
                else:
                    tensor = compile_field_tensor(data)
                    if tensor:
                        tensors.append(tensor)
    except FileNotFoundError:
        logger.error(f"[FieldTensorCompiler] Telemetry log not found: {path}")
    except Exception as e:
        logger.error(f"[FieldTensorCompiler] Error parsing log: {e}")

    logger.info(f"[FieldTensorCompiler] Compiled {len(tensors)} tensor frames from {path}")
    return tensors

# ──────────────────────────────────────────────
#  Example Integration Snippet
# ──────────────────────────────────────────────
"""
Example usage within QuantumMorphicRuntime after SLE->HST coupling:

    from backend.modules.holograms.compile_field_tensor import compile_field_tensor
    from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

    sle_data = sle_runtime.get_recent_telemetry()
    psi_kappa_T = compile_field_tensor(sle_data)

    feedback = morphic_feedback.regulate(psi_kappa_T, field_nodes)
    runtime_state['feedback'] = feedback
"""