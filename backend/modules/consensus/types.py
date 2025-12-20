from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


VoteType = Literal["PREVOTE", "PRECOMMIT"]


class Proposal(BaseModel):
    height: int
    round: int = 0
    proposer: str
    block_id: str
    block: Optional[Dict[str, Any]] = None
    ts_ms: float = Field(default=0.0)


class Vote(BaseModel):
    height: int
    round: int = 0
    voter: str
    vote_type: VoteType
    block_id: str
    ts_ms: float = Field(default=0.0)
    signature: Optional[str] = None  # slashing later


class QC(BaseModel):
    height: int
    round: int = 0
    vote_type: VoteType
    block_id: str
    voters: List[str]
    ts_ms: float = Field(default=0.0)