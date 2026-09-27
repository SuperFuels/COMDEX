"""Canonical commitment for the exact GlyphChain ledger block under consensus.

Consensus block identifiers describe the consensus height, round and proposer.
This module adds a content commitment for the ledger block at that height so a
quorum certificate can prove the transaction root it actually finalized.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from backend.modules.chain_sim.chain_sim_ledger import compute_tx_identity
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root


LEDGER_COMMITMENT_SCHEMA = "glyphchain.ledger-block-commitment.v1"
MAX_LEDGER_TRANSACTIONS = 10_000


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hex64(value: Any, *, field: str, allow_empty: bool = False) -> str:
    text = str(value or "").strip().lower()
    if allow_empty and not text:
        return ""
    if len(text) != 64:
        raise ValueError(f"{field}_invalid")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    return text


def normalize_ledger_block(
    block: Mapping[str, Any] | None,
    *,
    chain_id: str,
    height: int,
) -> dict[str, Any]:
    """Validate a proposed ledger block and return its portable commitment."""
    raw = dict(block or {})
    wanted_height = int(height)
    if wanted_height <= 0:
        raise ValueError("ledger_height_invalid")
    supplied_height = int(raw.get("height") or wanted_height)
    if supplied_height != wanted_height:
        raise ValueError("ledger_height_mismatch")

    raw_transactions = raw.get("txs") or []
    if not isinstance(raw_transactions, list) or len(raw_transactions) > MAX_LEDGER_TRANSACTIONS:
        raise ValueError("ledger_transaction_limit_exceeded")
    transactions = raw_transactions
    normalized_transactions: list[dict[str, Any]] = []
    tx_hashes: list[str] = []
    for expected_index, item in enumerate(transactions):
        if not isinstance(item, Mapping):
            raise ValueError("ledger_transaction_invalid")
        tx_index = int(item.get("tx_index") if item.get("tx_index") is not None else expected_index)
        if tx_index != expected_index:
            raise ValueError("ledger_transaction_order_invalid")
        tx_hash = _hex64(item.get("tx_hash"), field="ledger_transaction_hash")
        tx_id = str(item.get("tx_id") or "").strip()
        if tx_id != f"tx_{tx_hash[:12]}":
            raise ValueError("ledger_transaction_id_invalid")
        computed_id, computed_hash = compute_tx_identity(
            str(item.get("from_addr") or ""),
            int(item.get("nonce") or 0),
            str(item.get("tx_type") or ""),
            dict(item.get("payload") or {}),
        )
        if computed_id != tx_id or computed_hash != tx_hash:
            raise ValueError("ledger_transaction_envelope_mismatch")
        tx_hashes.append(tx_hash)
        normalized_transactions.append({
            "tx_id": tx_id,
            "tx_hash": tx_hash,
            "tx_index": tx_index,
        })

    computed_root = merkle_root([hash_leaf(bytes.fromhex(value)) for value in tx_hashes]).hex()
    header = dict(raw.get("header") or {})
    supplied_root = str(raw.get("txs_root") or header.get("txs_root") or computed_root).strip().lower()
    supplied_root = _hex64(supplied_root, field="ledger_txs_root")
    if supplied_root != computed_root:
        raise ValueError("ledger_txs_root_mismatch")
    state_root = _hex64(
        raw.get("state_root") or header.get("state_root"),
        field="ledger_state_root",
        allow_empty=True,
    )
    commitment_payload = {
        "schema_version": LEDGER_COMMITMENT_SCHEMA,
        "chain_id": str(chain_id),
        "height": wanted_height,
        "txs_root": computed_root,
        "state_root": state_root or None,
        "transactions": normalized_transactions,
    }
    return {
        "ledger_commitment": sha256(_canonical(commitment_payload)).hexdigest(),
        "txs_root": computed_root,
        "state_root": state_root or None,
        "commitment_payload": commitment_payload,
    }


def empty_ledger_block(*, height: int) -> dict[str, Any]:
    return {"height": int(height), "txs": [], "header": {}}
