# backend/modules/chain_sim/chain_sim_merkle.py
from __future__ import annotations

import hashlib
from typing import List, Dict, Any


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def hash_leaf(payload_bytes: bytes) -> bytes:
    # domain-separated leaf hash
    return _sha256(b"leaf:" + payload_bytes)


def hash_node(left: bytes, right: bytes) -> bytes:
    # domain-separated inner hash
    return _sha256(b"node:" + left + right)


def merkle_root(leaves: List[bytes]) -> bytes:
    if not leaves:
        return _sha256(b"empty")

    level = list(leaves)
    while len(level) > 1:
        nxt: List[bytes] = []
        i = 0
        while i < len(level):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]  # duplicate last
            nxt.append(hash_node(left, right))
            i += 2
        level = nxt
    return level[0]


def merkle_proof(leaves: List[bytes], index: int) -> List[Dict[str, Any]]:
    """
    Proof is a list of {sibling_hex, side} where side ∈ {"left","right"}
    meaning: sibling is on that side of the running hash.
    """
    if index < 0 or index >= len(leaves):
        raise ValueError("index out of range")

    proof: List[Dict[str, Any]] = []
    level = list(leaves)
    idx = index

    while len(level) > 1:
        # pad odd
        if len(level) % 2 == 1:
            level.append(level[-1])

        is_left = (idx % 2 == 0)
        sibling_idx = idx + 1 if is_left else idx - 1
        sibling = level[sibling_idx]
        proof.append(
            {
                "sibling": sibling.hex(),
                "side": "right" if is_left else "left",
            }
        )

        # build next level
        nxt: List[bytes] = []
        for i in range(0, len(level), 2):
            nxt.append(hash_node(level[i], level[i + 1]))
        level = nxt
        idx //= 2

    return proof


def verify_proof(leaf_hash: bytes, proof: List[Dict[str, Any]], root: bytes) -> bool:
    h = leaf_hash
    for step in proof:
        sib = bytes.fromhex(str(step.get("sibling", "")))
        side = step.get("side")
        if side == "right":
            h = hash_node(h, sib)
        elif side == "left":
            h = hash_node(sib, h)
        else:
            return False
    return h == root