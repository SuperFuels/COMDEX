"""
📘 GWIP Schema — Unified Validation Layer (SRK-9)
Combines:
 - Pydantic model validation for structured metadata (compile-time)
 - JSON Schema validation for runtime packet integrity (coherence, hash, signature)
"""

import json
from pathlib import Path
from typing import Optional, Literal

import jsonschema
from jsonschema import validate
from pydantic import BaseModel, Field

from backend.modules.glyphwave.carrier.carrier_types import CarrierType


# ────────────────────────────────────────────────────────────────
# 📦 Pydantic Model — Metadata Structure
# ----------------------------------------------------------------
class GWIPMetadata(BaseModel):
    """Metadata fields for a GlyphWave Information Packet (GWIP)."""

    packet_id: str
    source_container: str
    target_container: str

    # 📡 Carrier Layer
    carrier_type: CarrierType = Field(
        default=CarrierType.SIMULATED,
        description="Carrier type: optical, RF, simulated, etc."
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Transmission delay estimate (ms)"
    )
    coherence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Carrier coherence score [0.0–1.0]"
    )

    # 🔐 Security Layer
    qkd_required: Optional[bool] = Field(
        default=False,
        description="If true, QKD verification is mandatory for this packet"
    )
    gkey_id: Optional[str] = Field(
        default=None,
        description="ID of associated GKey (if encrypted)"
    )
    encrypted: Optional[bool] = Field(
        default=False,
        description="Indicates whether payload is QKD-encrypted"
    )

    # 🌐 Transport Layer
    modulation_strategy: Optional[str] = Field(
        default=None,
        description="Specifies modulation or photon encoding scheme"
    )
    tamper_detected: Optional[bool] = Field(
        default=None,
        description="True if integrity checks failed or QKD mismatch detected"
    )


# ────────────────────────────────────────────────────────────────
# 🧩 JSON Schema Validation — Full GWIP Packet Structure
# ----------------------------------------------------------------
# ✅ Corrected schema path (matches actual file location)
SCHEMA_PATH = Path(__file__).resolve().parent / "gwip_packet_schema_v3.json"


def validate_gwip_schema(packet: dict) -> None:
    """
    Validate a GWIP packet against the canonical JSON Schema.

    This ensures structural, numerical, and type correctness
    before QKD or compression layers process the packet.

    Raises:
        jsonschema.ValidationError: if validation fails.
    """
    try:
        with open(SCHEMA_PATH, "r") as f:
            schema = json.load(f)
        validate(instance=packet, schema=schema)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            f"[GWIP Validation Error] {e.message} at path: {'/'.join(map(str, e.path))}"
        ) from e
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found at: {SCHEMA_PATH}")


# ────────────────────────────────────────────────────────────────
# 🧠 Combined Validator Utility
# ----------------------------------------------------------------
def validate_gwip_packet(packet: dict) -> GWIPMetadata:
    """
    Run dual-layer validation:
     - JSON Schema for packet envelope integrity
     - Pydantic model for metadata consistency

    Returns:
        GWIPMetadata: validated metadata instance
    """
    validate_gwip_schema(packet)
    meta = packet.get("envelope", {}).copy()
    return GWIPMetadata(**meta)