# ──────────────────────────────────────────────
#  Tessaris • Knowledge Pack Generator (GHX + HQCE Ready)
#  Integrates symbolic hologram generation with ψ–κ–T tensor augmentation.
# ──────────────────────────────────────────────

import uuid
import time
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.symbolic_entangler import get_entangled_links
from backend.modules.codex.codex_metrics import (
    calculate_glyph_cost,
    entropy_level,
    goal_alignment_score,
)
from backend.modules.hologram.ghx_encoder import glyph_intensity_map
from backend.modules.glyphnet.glyphnet_ws import GlyphWebSocketManager


# ──────────────────────────────────────────────
#  Symbolic Classification + Color Mapping
# ──────────────────────────────────────────────
def classify_logic_type(symbol: str) -> str:
    if symbol in ("⧖", "⬁"):
        return "collapse"
    elif symbol in ("🧬", "⬁"):
        return "mutate"
    elif symbol in ("🛰️", "🧠"):
        return "push"
    elif symbol in ("🎞", "🪞"):
        return "replay"
    else:
        return "unknown"


def gradient_color(entropy: float, cost: float) -> str:
    """
    Map entropy/cost to RGBA gradient: low = green, high = red/purple
    """
    r = min(255, int(255 * entropy))
    g = min(255, int(255 * (1 - entropy)))
    b = max(0, 180 - int(80 * cost))
    alpha = max(0.4, min(1.0, 1.0 - 0.3 * cost))
    return f"rgba({r},{g},{b},{alpha:.2f})"


# ──────────────────────────────────────────────
#  HQCE Stage 1 — ψ–κ–T Tensor Augmentation
# ──────────────────────────────────────────────
def curvature_estimate(links: List[Dict[str, Any]]) -> float:
    """Simple curvature proxy from link density."""
    n = len(links)
    return float(np.tanh(n / 50.0))  # compressive mapping


def compute_psikappaT(nodes: List[Dict[str, Any]], links: List[Dict[str, Any]],
                      tick_time: float = 1.0, coherence_decay: float = 1e-3) -> Dict[str, float]:
    """Compute the ψ–κ–T tensor signature for this holographic frame."""
    if nodes:
        psi = float(np.mean([n.get("entropy_score", 0.0) for n in nodes]))
    else:
        psi = 0.0
    kappa = curvature_estimate(links)
    T = float(tick_time / max(coherence_decay, 1e-6))
    return {"psi": psi, "kappa": kappa, "T": T}


# ──────────────────────────────────────────────
#  Core Pack Generation
# ──────────────────────────────────────────────
def generate_knowledge_pack(glyph_tree: List[Dict[str, Any]], container_id: str) -> Dict[str, Any]:
    """
    Bundle a recursive logic tree into a portable GHX hologram pack.
    Includes HQCE ψ–κ–T tensor augmentation for field analysis.
    """
    projection = []
    links = []

    for glyph in glyph_tree:
        gid = glyph.get("id", str(uuid.uuid4()))
        symbol = glyph["symbol"]
        label = glyph.get("label", "")
        timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())
        entangled = glyph.get("entangled", []) or get_entangled_links(gid)
        replay = trace_glyph_execution_path(gid)
        cost = calculate_glyph_cost(symbol)
        entropy = entropy_level(symbol)
        goal_score = goal_alignment_score(glyph)
        logic_type = classify_logic_type(symbol)
        color = gradient_color(entropy, cost)
        intensity = glyph_intensity_map(symbol)

        projection.append({
            "glyph_id": gid,
            "symbol": symbol,
            "label": label,
            "color": color,
            "light_intensity": intensity,
            "trigger_state": "idle",
            "animation": "pulse",
            "collapse_trace": logic_type == "collapse",
            "logic_type": logic_type,
            "entangled": entangled,
            "replay": replay,
            "cost": cost,
            "entropy_score": entropy,
            "goal_match_score": goal_score,
            "timestamp": timestamp
        })

        for target in entangled:
            links.append({
                "source": gid,
                "target": target,
                "type": "entanglement",
                "color": "#aa00ff",
                "animated": True
            })

    # ─── Assemble GHX Pack ─────────────────────
    ghx_pack = {
        "projection_id": str(uuid.uuid4()),
        "rendered_at": datetime.utcnow().isoformat(),
        "container_id": container_id,
        "physics": "symbolic-quantum",
        "dimensions": 4,
        "nodes": projection,
        "links": links,
        "metadata": {
            "ghx_version": "1.1",
            "replay_enabled": True,
            "recursive_pack": True
        }
    }

    # ─── Compute ψ–κ–T Signature (HQCE v0.1) ────
    psi_kappa_T = compute_psikappaT(projection, links)
    ghx_pack["psi_kappa_T_signature"] = psi_kappa_T

    # ─── Auto-Broadcast to WebSocket Clients ────
    try:
        GlyphWebSocketManager.broadcast_ghx_pack(ghx_pack)
    except Exception as e:
        print(f"[GHX Broadcast Warning] Failed to broadcast: {e}")

    return ghx_pack