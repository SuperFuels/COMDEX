# ──────────────────────────────────────────────
#  Tessaris * GHX Field Compiler (HQCE Stage 2+)
#  Computes ψ-κ-T tensor and coherence metrics
#  from holographic field snapshots (nodes + links)
#  Compatible with HSTGenerator + QuantumMorphicRuntime
# ──────────────────────────────────────────────

import uuid
import time
import numpy as np
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def compile_field_tensor(field_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute ψ (entropy), κ (curvature), T (temporal flux), and global coherence (C)
    from any GHX or HST field snapshot.

    Args:
        field_data: {
            "nodes": [ { "entropy": ..., "coherence": ..., "node_id": ... }, ... ],
            "links": [ { "a": ..., "b": ..., "phi": ... }, ... ],
            "tick_time": float,
            "field_decay": float
        }

    Returns:
        dict with keys: ψ, κ, T, coherence, gradient, stability, metadata
    """
    snapshot_id = f"tensor_{uuid.uuid4().hex[:10]}"
    try:
        nodes: List[Dict[str, Any]] = field_data.get("nodes", [])
        links: List[Dict[str, Any]] = field_data.get("links", [])
        tick_time = float(field_data.get("tick_time", field_data.get("tick_duration", 1.0)))
        field_decay = float(field_data.get("field_decay", 1e-6))

        if not nodes:
            logger.warning("[GHXFieldCompiler] No nodes detected.")
            return {
                "psi": 0.0, "kappa": 0.0, "T": 0.0, "coherence": 0.0,
                "gradient": 0.0, "stability": 0.0,
                "metadata": {"id": snapshot_id, "timestamp": time.time()}
            }

        # ψ - mean field entropy
        entropy_values = np.array([n.get("entropy", 0.5) for n in nodes], dtype=float)
        ψ = float(np.mean(entropy_values))

        # κ - curvature: node-connectivity * coherence variance attenuation
        node_degree = {n.get("node_id", str(i)): 0 for i, n in enumerate(nodes)}
        for link in links:
            a, b = link.get("a"), link.get("b")
            if a in node_degree:
                node_degree[a] += 1
            if b in node_degree:
                node_degree[b] += 1
        avg_degree = np.mean(list(node_degree.values())) if node_degree else 0.0

        coherence_values = np.array([n.get("coherence", 0.5) for n in nodes], dtype=float)
        coherence_var = np.var(coherence_values)
        κ = float(np.tanh(avg_degree / (1.0 + 10.0 * coherence_var)))

        # T - normalized temporal flux
        T = float(tick_time / max(field_decay, 1e-6))

        # C - global coherence mean
        C = float(np.mean(coherence_values))

        # ∇ψ - entropy gradient magnitude (field diversity)
        gradient = float(np.std(entropy_values))

        # stability index - coherence / (1 + gradient)
        stability = float(C / (1.0 + gradient))

        tensor = {
            "psi": ψ,
            "kappa": κ,
            "T": T,
            "coherence": C,
            "gradient": gradient,
            "stability": stability,
            "metadata": {
                "id": snapshot_id,
                "timestamp": time.time(),
                "node_count": len(nodes),
                "link_count": len(links),
            },
        }

        logger.debug(
            f"[GHXFieldCompiler] ψ={ψ:.4f} κ={κ:.4f} T={T:.4f} "
            f"C={C:.4f} ∇ψ={gradient:.4f} S={stability:.4f}"
        )
        return tensor

    except Exception as e:
        logger.error(f"[GHXFieldCompiler] Compilation failed: {e}")
        return {
            "psi": 0.0, "kappa": 0.0, "T": 0.0, "coherence": 0.0,
            "gradient": 0.0, "stability": 0.0,
            "metadata": {"id": snapshot_id, "timestamp": time.time()},
        }