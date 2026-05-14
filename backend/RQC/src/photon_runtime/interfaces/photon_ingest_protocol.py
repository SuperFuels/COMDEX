"""
Photon Runtime - Ingest Protocol Interface
──────────────────────────────────────────────
Defines a unified interface for ingesting Photon glyph packets
across the Tessaris cognitive stack (QQC, AION, RQC).

Responsibilities:
- Normalize glyph packets (Φ, R, S, γ, ψ, κ, T)
- Decode ε-glyph numeric compression
- Dispatch updates into local resonance/state engines
- Provide consistent logging and validation across all bridges
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

# ────────────────────────────────────────────────
# Optional Photon decoder import
# ────────────────────────────────────────────────
try:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import photon_decode
except Exception:
    photon_decode = None

logger = logging.getLogger("PhotonIngestProtocol")
logger.setLevel(logging.INFO)

# ────────────────────────────────────────────────
# Utility: Decode ε-numbers back into floats
# ────────────────────────────────────────────────
def decode_epsilon_number(symbol: str) -> Optional[float]:
    """
    Convert compact ε-symbolic numbers (εx) back to float approximation.
    Example: "ε0" -> 1.0, "ε5000000000" -> 0.995
    """
    if not isinstance(symbol, str) or not symbol.startswith("ε"):
        return None
    try:
        exp = int(symbol[1:])
        if exp == 0:
            return 1.0
        # Inverse of glyph_math compression logic
        return 1.0 - (exp / 1e12)
    except Exception:
        return None

# ────────────────────────────────────────────────
# Base Abstract Class
# ────────────────────────────────────────────────
class PhotonIngestProtocol(ABC):
    """Abstract base class for Photon glyph ingestion bridges."""

    def __init__(self, name: str):
        self.name = name
        self.log = logging.getLogger(name)
        self.log.setLevel(logging.INFO)

    # ───────────────────────────────
    # Core ingest pipeline
    # ───────────────────────────────
    def ingest_packet(self, packet: str) -> Optional[Dict]:
        """Unified entrypoint: decode and normalize a Photon glyph packet."""
        try:
            # Attempt Photon decode
            if photon_decode:
                data = photon_decode(packet)
            else:
                data = json.loads(packet)
        except Exception:
            data = {"raw": packet}

        normalized = self._normalize_fields(data)
        self.on_ingest(normalized)
        return normalized

    # ───────────────────────────────
    # Field normalization
    # ───────────────────────────────
    def _normalize_fields(self, data: Dict) -> Dict:
        """Ensure consistent field naming and epsilon decoding."""
        normalized = {}
        for k, v in data.items():
            # Decode ε-values if present
            if isinstance(v, str) and v.startswith("ε"):
                decoded = decode_epsilon_number(v)
                normalized[k] = decoded if decoded is not None else v
            else:
                normalized[k] = v
        return normalized

    # ───────────────────────────────
    # Hooks to override per subsystem
    # ───────────────────────────────
    @abstractmethod
    def on_ingest(self, data: Dict):
        """Handle decoded Photon data (to be implemented by subclass)."""
        pass

    # ───────────────────────────────
    # Logging helper
    # ───────────────────────────────
    def log_event(self, label: str, data: Dict):
        """Standardized log message for ingestion events."""
        self.log.info(f"[{self.name}] {label}: Φ={data.get('Φ')} R={data.get('R')} S={data.get('S')} γ={data.get('γ')}")