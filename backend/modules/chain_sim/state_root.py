# backend/modules/chain_sim/state_root.py
from __future__ import annotations

from typing import Any, Dict
from .canonical_codec import canonical_hash_hex
from .tx_executor import get_chain_state_snapshot

def compute_state_root() -> str:
    snap = get_chain_state_snapshot()
    return canonical_hash_hex(snap)