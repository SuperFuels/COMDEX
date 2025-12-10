# backend/modules/mesh/mesh_types.py

from __future__ import annotations
from typing import TypedDict, Dict

DeviceId = str
AccountId = str
ClusterId = str


class LocalIdentity(TypedDict):
    device_id: DeviceId
    primary_account: AccountId


class LocalBalance(TypedDict):
    account: AccountId
    global_confirmed_pho: str          # last on-chain balance we trust
    local_net_delta_pho: str           # sum(local_in - local_out) since last sync
    offline_credit_limit_pho: str      # max unbacked local spend
    safety_buffer_pho: str             # UX / risk padding


class OfflineCreditPolicy(TypedDict):
    default_limit_pho: str
    per_account_overrides: Dict[AccountId, str]


__all__ = [
    "DeviceId",
    "AccountId",
    "ClusterId",
    "LocalIdentity",
    "LocalBalance",
    "OfflineCreditPolicy",
]