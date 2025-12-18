from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


MsgType = Literal[
    "HELLO",
    "PEERS",
    "TX_RELAY",
    "BLOCK_ANNOUNCE",
    "BLOCK_REQ",
    "BLOCK_RESP",
]


class P2PEnvelope(BaseModel):
    # Strict msg typing (better than P2PType=str)
    type: MsgType

    # Required identity fields
    from_node_id: str = Field(..., min_length=1)
    chain_id: str = Field(..., min_length=1)

    # Timestamp (dev)
    ts_ms: float = 0.0

    # Message payload
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Prevent loops in dev
    hops: int = 0

    # Optional metadata (dev convenience) — keep optional for back-compat
    from_val_id: Optional[str] = None
    base_url: Optional[str] = None
    role: Optional[str] = None


class PeerInfo(BaseModel):
    node_id: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)  # e.g. http://127.0.0.1:8081
    val_id: Optional[str] = None
    last_seen_ms: Optional[float] = None
    banned: bool = False
    role: str = "peer"  # "validator" | "peer"