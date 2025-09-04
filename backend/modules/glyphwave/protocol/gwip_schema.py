# backend/modules/glyphwave/protocol/gwip_schema.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from backend.modules.glyphwave.carrier.carrier_types import CarrierType


class GWIPMetadata(BaseModel):
    """Metadata fields for GWave Information Packet (GWIP)."""
    packet_id: str
    source_container: str
    target_container: str

    # 📡 New Carrier Layer Fields
    carrier_type: CarrierType = Field(default=CarrierType.SIMULATED)
    latency_ms: Optional[float] = Field(default=None, description="Transmission delay estimate")
    coherence: Optional[float] = Field(default=None, description="Carrier coherence score [0.0–1.0]")

    # 📦 Security Layer
    qkd_required: Optional[bool] = Field(default=False)
    gkey_id: Optional[str] = Field(default=None)
    encrypted: Optional[bool] = Field(default=False)

    # 🌐 Transport Layer (future extensions)
    modulation_strategy: Optional[str] = Field(default=None)
    tamper_detected: Optional[bool] = Field(default=None)