# backend/modules/mesh/mesh_reconcile_service.py

from __future__ import annotations
from decimal import Decimal
from typing import TypedDict, List, Dict, Optional

from backend.modules.mesh.mesh_types import AccountId, DeviceId, ClusterId
from backend.modules.mesh.cluster_block import ClusterBlock
from backend.modules.mesh.mesh_tx import MeshTx
from backend.modules.mesh.mesh_types import LocalBalance

from backend.modules.gma.gma_mesh_policy import get_offline_limit_pho


class ReconcileRequest(TypedDict):
    account: AccountId
    device_id: DeviceId
    last_global_block_height: int
    local_mesh_blocks: List[ClusterBlock]


class ReconcileResult(TypedDict):
    account: AccountId
    accepted_local_delta_pho: str
    disputed_mesh_tx_ids: List[str]
    settlement_tx_hash: Optional[str]


def _collect_all_txs(blocks: List[ClusterBlock]) -> List[MeshTx]:
    txs: List[MeshTx] = []
    for b in blocks:
        txs.extend(b.get("txs", []))
    return txs


def compute_local_delta_for_request(
    req: ReconcileRequest,
) -> Decimal:
    """
    Sum local_in - local_out for the given account across provided ClusterBlocks.
    """
    account = req["account"]
    txs = _collect_all_txs(req["local_mesh_blocks"])

    delta = Decimal("0")
    for tx in txs:
        amt = Decimal(tx["amount_pho"])
        if tx["to_account"] == account:
            delta += amt
        if tx["from_account"] == account:
            delta -= amt
    return delta


def clamp_accepted_delta(
    raw_delta: Decimal,
    offline_limit_pho: Decimal,
) -> Decimal:
    """
    Apply offline credit policy to the raw local delta.

    We currently:
      - allow full positive delta (incoming funds),
      - clamp negative delta so you can't spend more than offline_limit_pho.
    """
    if raw_delta >= 0:
        return raw_delta

    # Example policy: cap absolute negative delta by offline_limit_pho
    if abs(raw_delta) > offline_limit_pho:
        return -offline_limit_pho
    return raw_delta


def detect_conflicts_for_request(req: ReconcileRequest) -> List[MeshTx]:
    """
    Placeholder for conflict detection:
    - double-spends
    - sequence breaks
    - incompatible with on-chain nonces / tx history

    For now: returns empty list, meaning "no conflicts detected".
    """
    # TODO: implement real conflict checks against chain state.
    return []


def reconcile_mesh_for_account(
    req: ReconcileRequest,
    *,
    offline_limit_pho: Optional[Decimal] = None,
) -> ReconcileResult:
    """
    Core reconcile function used by both HTTP routes and tests.

    - Computes net local delta.
    - Applies offline credit policy (either provided or from GMA).
    - Returns a ReconcileResult with accepted delta and disputed tx IDs.
    """
    account = req["account"]

    # Pull policy from GMA if caller didn’t pass one explicitly
    if offline_limit_pho is None:
        offline_limit_pho = get_offline_limit_pho(account)

    raw_delta = compute_local_delta_for_request(req)
    disputed_txs = detect_conflicts_for_request(req)
    accepted = clamp_accepted_delta(raw_delta, offline_limit_pho)

    result: ReconcileResult = {
        "account": account,
        "accepted_local_delta_pho": str(accepted),
        "disputed_mesh_tx_ids": [t["mesh_tx_id"] for t in disputed_txs],
        "settlement_tx_hash": None,  # later: on-chain settlement tx
    }
    return result