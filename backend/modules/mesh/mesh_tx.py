# backend/modules/mesh/mesh_tx.py

from __future__ import annotations
from typing import TypedDict, List
import time
import uuid

from .mesh_types import DeviceId, AccountId, ClusterId


class MeshTx(TypedDict):
    mesh_tx_id: str
    cluster_id: ClusterId
    from_account: AccountId
    to_account: AccountId
    amount_pho: str
    created_at_ms: int
    prev_local_seq: int
    sender_device_id: DeviceId
    sender_signature: str   # opaque string, filled by wallet signer


class LocalTxLog(TypedDict):
    """
    Append-only log of MeshTx for a given account.
    Used by wallet + reconcile.
    """
    account: AccountId
    entries: List[MeshTx]
    last_seq: int


def new_mesh_tx(
    *,
    cluster_id: ClusterId,
    from_account: AccountId,
    to_account: AccountId,
    amount_pho: str,
    prev_local_seq: int,
    sender_device_id: DeviceId,
    sender_signature: str,
) -> MeshTx:
    """Helper to construct a MeshTx with a fresh ID + timestamp."""
    return MeshTx(
        mesh_tx_id=f"m_{uuid.uuid4().hex}",
        cluster_id=cluster_id,
        from_account=from_account,
        to_account=to_account,
        amount_pho=amount_pho,
        created_at_ms=int(time.time() * 1000),
        prev_local_seq=prev_local_seq,
        sender_device_id=sender_device_id,
        sender_signature=sender_signature,
    )


__all__ = ["MeshTx", "LocalTxLog", "new_mesh_tx"]