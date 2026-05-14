# backend/modules/chain_sim/tx_models.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional, List, Literal
from pydantic import BaseModel, Field

TxType = Literal[
    "BANK_MINT",
    "BANK_TRANSFER",
    "BANK_BURN",
    "STAKING_DELEGATE",
    "STAKING_UNDELEGATE",
]

class TxEnvelope(BaseModel):
    from_addr: str = Field(..., min_length=1)
    nonce: int = Field(..., ge=0)
    tx_type: TxType
    payload: Dict[str, Any] = Field(default_factory=dict)

class TxRecord(BaseModel):
    tx_id: str
    tx_hash: str
    height: int
    created_at_ms: int
    fee_pho: int = 0
    status: Literal["accepted", "rejected"] = "accepted"
    error: Optional[str] = None
    envelope: TxEnvelope

class BlockHeader(BaseModel):
    height: int
    created_at_ms: int
    state_root: str
    trace_root: Optional[str] = None
    transport_attestation_hash: Optional[str] = None
    tx_count: int

class Block(BaseModel):
    header: BlockHeader
    tx_ids: List[str]