# ──────────────────────────────────────────────
#  Tessaris • GHX Field Compiler (HQCE Stage 2+)
#  Computes ψ–κ–T tensor and coherence metrics
#  from holographic field snapshots (nodes + links)
# ──────────────────────────────────────────────
import numpy as np
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def compile_field_tensor(field_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute ψ (entropy), κ (curvature), T (temporal flux), and coherence (C)
    from any GHX or HST field snapshot.

    Compatible with existing HSTGenerator + QuantumMorphicRuntime.
    """
    try:
        nodes: List[Dict[str, Any]] = field_data.get("nodes", [])
        links: List[Dict[str, Any]] = field_data.get("links", [])
        tick_time = float(field_data.get("tick_time", field_data.get("tick_duration", 1.0)))
        field_decay = float(field_data.get("field_decay", 1e-6))

        if not nodes:
            logger.warning("[GHXFieldCompiler] No nodes detected.")
            return {"psi": 0.0, "kappa": 0.0, "T": 0.0, "coherence": 0.0}

        # ψ — average entropy across nodes
        entropy_values = np.array([n.get("entropy", 0.5) for n in nodes], dtype=float)
        ψ = float(np.mean(entropy_values))

        # κ — curvature approximation using node connectivity + coherence variance
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

        # T — temporal flux (normalized tick / field decay)
        T = float(tick_time / max(field_decay, 1e-6))

        # C — global coherence (mean)
        C = float(np.mean(coherence_values))

        tensor = {"psi": ψ, "kappa": κ, "T": T, "coherence": C}
        logger.debug(f"[GHXFieldCompiler] ψ={ψ:.4f} κ={κ:.4f} T={T:.4f} C={C:.4f}")
        return tensor

    except Exception as e:
        logger.error(f"[GHXFieldCompiler] Compilation failed: {e}")
        return {"psi": 0.0, "kappa": 0.0, "T": 0.0, "coherence": 0.0}