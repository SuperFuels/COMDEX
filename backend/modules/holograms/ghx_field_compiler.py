# ──────────────────────────────────────────────
#  HQCE Stage 2 — Field Tensor Compiler (Stub)
# ──────────────────────────────────────────────
import numpy as np

def compile_field_tensor(ghx_packet):
    """Extract minimal ψ–κ–T field tensor from GHX packet."""
    nodes = ghx_packet.get("nodes", [])
    links = ghx_packet.get("links", [])
    psi = np.mean([n.get("entropy", 0.0) for n in nodes]) if nodes else 0.0
    kappa = len(links) / max(len(nodes), 1)
    tick_duration = ghx_packet.get("tick_duration", 1.0)
    field_decay = ghx_packet.get("field_decay", 1e-6)
    T = tick_duration / max(field_decay, 1e-6)
    coherence = 1.0 - 0.5 * psi
    return {"psi": psi, "kappa": kappa, "T": T, "coherence": coherence}