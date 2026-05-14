# backend/modules/mesh/mesh_log.py

from __future__ import annotations
from typing import TypedDict, List

from .mesh_types import AccountId
from .mesh_tx import MeshTx


class LocalTxLog(TypedDict):
    account: AccountId
    entries: List[MeshTx]
    last_seq: int


def new_local_tx_log(account: AccountId) -> LocalTxLog:
    return LocalTxLog(account=account, entries=[], last_seq=0)


def append_mesh_tx(log: LocalTxLog, tx: MeshTx) -> LocalTxLog:
    """
    Append a MeshTx to the log and update last_seq.
    No validation here – caller should have checked prev_local_seq.
    """
    log["entries"].append(tx)
    log["last_seq"] = tx["prev_local_seq"]
    return log