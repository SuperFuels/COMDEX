from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

VoteType = Literal["PREVOTE", "PRECOMMIT"]


class Proposal(BaseModel):
    # allow p2p envelope payload extras like sig_hex without crashing the engine
    model_config = ConfigDict(extra="allow")

    height: int
    round: int = 0
    proposer: str
    block_id: str
    # engine creates block={}, so don't default to None
    block: Dict[str, Any] = Field(default_factory=dict)
    ts_ms: float = Field(default=0.0)

    # p2p payloads in tests use sig_hex; keep it optional
    sig_hex: Optional[str] = None


class Vote(BaseModel):
    model_config = ConfigDict(extra="allow")

    height: int
    round: int = 0
    voter: str
    vote_type: VoteType
    block_id: str
    ts_ms: float = Field(default=0.0)

    # keep your existing placeholder, but also accept sig_hex from p2p tests
    signature: Optional[str] = None  # slashing later
    sig_hex: Optional[str] = None


class QC(BaseModel):
    model_config = ConfigDict(extra="allow")

    height: int
    round: int = 0
    # QC should only ever represent PRECOMMIT aggregation
    vote_type: Literal["PRECOMMIT"]
    block_id: str
    voters: List[str]
    ts_ms: float = Field(default=0.0)