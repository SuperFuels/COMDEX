from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


ConsensusStep = Literal["PROPOSAL", "PREVOTE", "PRECOMMIT"]


@dataclass(frozen=True)
class ProposalMsg:
    chain_id: str
    height: int
    round: int
    proposer_id: str
    # minimal commitments for now
    header: Dict[str, Any]
    # leader-inbox model: txs can be sent separately; proposal references a block hash
    block_hash: str
    # optional signature fields (future)
    pubkey_hex: str = ""
    signature_hex: str = ""

    def sign_bytes(self) -> str:
        # canonical sign-bytes (JSON) — matches your “canonical JSON” approach
        body = {
            "type": "PROPOSAL",
            "chain_id": self.chain_id,
            "height": int(self.height),
            "round": int(self.round),
            "proposer_id": self.proposer_id,
            "header": self.header or {},
            "block_hash": self.block_hash,
        }
        return _stable_json(body)

    def msg_id(self) -> str:
        return _sha256_hex(self.sign_bytes())


@dataclass(frozen=True)
class VoteMsg:
    chain_id: str
    height: int
    round: int
    step: ConsensusStep  # PREVOTE or PRECOMMIT
    voter_id: str
    block_hash: str  # empty string for nil vote
    pubkey_hex: str = ""
    signature_hex: str = ""

    def sign_bytes(self) -> str:
        body = {
            "type": "VOTE",
            "chain_id": self.chain_id,
            "height": int(self.height),
            "round": int(self.round),
            "step": self.step,
            "voter_id": self.voter_id,
            "block_hash": self.block_hash,
        }
        return _stable_json(body)

    def msg_id(self) -> str:
        return _sha256_hex(self.sign_bytes())


@dataclass(frozen=True)
class TxRelayMsg:
    """
    Leader inbox model: peers relay signed tx envelopes to the current leader.
    """
    chain_id: str
    sender_peer_id: str
    tx_envelope: Dict[str, Any]

    def msg_id(self) -> str:
        body = {
            "type": "TX_RELAY",
            "chain_id": self.chain_id,
            "sender_peer_id": self.sender_peer_id,
            "tx_envelope": self.tx_envelope or {},
        }
        return _sha256_hex(_stable_json(body))