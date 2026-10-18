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
    "SNAPSHOT_REQ",
]


class P2PEnvelope(BaseModel):
    type: P2PMsgType
    from_node_id: str = Field(min_length=1, max_length=240)
    chain_id: str = Field(min_length=1, max_length=240)
    ts_ms: float
    payload: Dict[str, Any] = {}
    hops: int = Field(default=0, ge=0, le=16)

    from_val_id: Optional[str] = Field(default=None, max_length=240)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    role: Optional[str] = Field(default=None, max_length=40)


class PeerInfo(BaseModel):
    node_id: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)  # e.g. http://127.0.0.1:8081
    val_id: Optional[str] = None
    last_seen_ms: Optional[float] = None
    banned: bool = False
    role: str = "peer"  # "validator" | "peer"
    relay_url: Optional[str] = None  # signed-discovery route for outbound-only nodes

    # PR5: identity binding (set by signed /api/p2p/hello)
    pubkey_hex: Optional[str] = None
    hello_ok: bool = False
    last_hello_ms: Optional[float] = None
    # Signed protocol compatibility advertisement from HELLO.
    protocol: Dict[str, Any] = Field(default_factory=dict)
