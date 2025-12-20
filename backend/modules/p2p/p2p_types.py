from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

P2PMsgType = Literal[
    "HELLO",
    "CONNECT",
    "PEERS",
    "TX_RELAY",
    "BLOCK_ANNOUNCE",
    "BLOCK_REQ",
    "BLOCK_RESP",
    "PROPOSAL",
    "VOTE",
    "STATUS",
    "SYNC_REQ",
    "SYNC_RESP",
]


class P2PEnvelope(BaseModel):
    type: P2PMsgType
    from_node_id: str
    chain_id: str
    ts_ms: float
    payload: Dict[str, Any] = {}
    hops: int = 0

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

    # PR5: identity binding (set by signed /api/p2p/hello)
    pubkey_hex: Optional[str] = None
    hello_ok: bool = False
    last_hello_ms: Optional[float] = None