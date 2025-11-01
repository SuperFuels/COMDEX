"""
AION Cognitive Fabric - Resonance Fusion Layer
────────────────────────────────────────────
Receives normalized ψ-κ-T-Φ packets (optionally carrying γ′ feedback gain)
from the Photon Ingest bridge, accumulates them into a transient fusion buffer,
and produces a live fusion tensor. This layer now provides cross-process visibility
via a shared JSON file for AION's Morphic Fabric coupling logic.
"""

import logging
import time
import math
import json
import os
from typing import Dict, List, Optional

logger = logging.getLogger("AIONFabric")
logger.setLevel(logging.INFO)

# ────────────────────────────────────────────────
# Shared state
# ────────────────────────────────────────────────
_FABRIC_BUFFER: List[Dict] = []
FUSION_FILE = "/tmp/aion_fusion_tensor.json"

# ────────────────────────────────────────────────
# Ingestion Logic
# ────────────────────────────────────────────────
def resonance_ingest(packet: Dict, timestamp: Optional[float] = None):
    """
    Accepts an incoming ψ-κ-T-Φ cognitive packet (optionally with γ′),
    validates it, and stores it in the AION Morphic buffer.
    """
    if not isinstance(packet, dict):
        logger.warning(f"[AIONFabric] Ignored invalid packet: {packet}")
        return False

    ts = timestamp or time.time()
    enriched = {**packet, "timestamp": ts}

    # Default γ′ if not provided
    if "γ′" not in enriched:
        enriched["γ′"] = 1.0

    _FABRIC_BUFFER.append(enriched)

    logger.info(
        f"[AIONFabric] Ingested ψ={packet.get('ψ')} κ={packet.get('κ')} "
        f"T={packet.get('T')} Φ={packet.get('Φ')} γ′={enriched.get('γ′')} "
        f"(S={packet.get('stability')})"
    )
    return True


def get_fusion_buffer() -> List[Dict]:
    """Return a copy of the current fusion buffer (for monitoring/testing)."""
    return list(_FABRIC_BUFFER)


def clear_fusion_buffer():
    """Reset the resonance buffer - used in tests or during reload."""
    _FABRIC_BUFFER.clear()

# ────────────────────────────────────────────────
# Phase II - Tensor Fusion Logic (γ′-weighted stability)
# ────────────────────────────────────────────────
def fuse_resonance_window(window_size: int = 10) -> Optional[Dict]:
    """
    Compute a ψ-κ-T-Φ-γ′ fusion tensor from the most recent N packets.
    Performs temporal averaging and derives a γ′-weighted stability index.

    Returns a dict like:
      {"ψ̄": <mean>, "κ̄": <mean>, "T̄": <mean>, "Φ̄": <mean>, "γ̄′": <mean>, "σ": <stability>}
    or None if insufficient data.
    """
    if not _FABRIC_BUFFER:
        logger.info("[AIONFabric] Fusion skipped (empty buffer)")
        return None

    recent = _FABRIC_BUFFER[-window_size:]
    n = len(recent)
    if n == 0:
        return None

    mean_psi = sum(p.get("ψ") or 0 for p in recent) / n
    mean_kappa = sum(p.get("κ") or 0 for p in recent) / n
    mean_T = sum(p.get("T") or 0 for p in recent) / n
    mean_Phi = sum(p.get("Φ") or 0 for p in recent) / n
    mean_gamma = sum(p.get("γ′") or 1.0 for p in recent) / n

    # Compute γ′-weighted variance and stability
    var_sum = sum(
        (p.get("γ′", 1.0)) * (
            (p.get("ψ", 0) - mean_psi) ** 2 +
            (p.get("κ", 0) - mean_kappa) ** 2 +
            (p.get("T", 0) - mean_T) ** 2
        )
        for p in recent
    )

    stability = max(0.0, 1.0 - math.sqrt(var_sum / (3 * n)))

    fused = {
        "ψ̄": round(mean_psi, 6),
        "κ̄": round(mean_kappa, 6),
        "T̄": round(mean_T, 6),
        "Φ̄": round(mean_Phi, 6),
        "γ̄′": round(mean_gamma, 6),
        "σ": round(stability, 6),
        "count": n,
    }

    logger.info(
        f"[AIONFabric] Fused {n} packets -> ψ̄={fused['ψ̄']} κ̄={fused['κ̄']} "
        f"T̄={fused['T̄']} γ̄′={fused['γ̄′']} σ={fused['σ']}"
    )

    # Store to global + disk for emitter visibility
    update_latest_fusion_tensor(fused)
    return fused

# ────────────────────────────────────────────────
# Fusion Buffer and Cross-Process Retrieval
# ────────────────────────────────────────────────
_latest_fusion_tensor: Optional[Dict] = None


def update_latest_fusion_tensor(tensor: dict):
    """Store the latest fusion tensor both in memory and JSON file."""
    global _latest_fusion_tensor
    _latest_fusion_tensor = tensor

    try:
        with open(FUSION_FILE, "w", encoding="utf-8") as f:
            json.dump(tensor, f)
    except Exception as e:
        logger.warning(f"[AIONFabric] Failed to write fusion tensor to file: {e}")


def get_latest_fusion_tensor() -> Optional[dict]:
    """Retrieve the most recent fusion tensor (from memory or JSON file)."""
    global _latest_fusion_tensor

    if _latest_fusion_tensor:
        return _latest_fusion_tensor

    if not os.path.exists(FUSION_FILE):
        return None
    try:
        with open(FUSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None