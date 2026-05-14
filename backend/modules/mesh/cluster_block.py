# backend/modules/mesh/cluster_block.py

from __future__ import annotations
from typing import TypedDict, List
import hashlib
import json

from .mesh_types import ClusterId, DeviceId
from .mesh_tx import MeshTx


class ClusterBlock(TypedDict):
    cluster_id: ClusterId
    height: int
    prev_block_hash: str
    txs: List[MeshTx]
    hash: str
    notary_device_id: DeviceId
    notary_signature: str


def compute_block_hash(
    *,
    cluster_id: ClusterId,
    height: int,
    prev_block_hash: str,
    txs: List[MeshTx],
    notary_device_id: DeviceId,
) -> str:
    payload = {
        "cluster_id": cluster_id,
        "height": height,
        "prev_block_hash": prev_block_hash,
        "txs": txs,
        "notary_device_id": notary_device_id,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def new_cluster_block(
    *,
    cluster_id: ClusterId,
    height: int,
    prev_block_hash: str,
    txs: List[MeshTx],
    notary_device_id: DeviceId,
    notary_signature: str,
) -> ClusterBlock:
    h = compute_block_hash(
        cluster_id=cluster_id,
        height=height,
        prev_block_hash=prev_block_hash,
        txs=txs,
        notary_device_id=notary_device_id,
    )
    return ClusterBlock(
        cluster_id=cluster_id,
        height=height,
        prev_block_hash=prev_block_hash,
        txs=txs,
        hash=h,
        notary_device_id=notary_device_id,
        notary_signature=notary_signature,
    )