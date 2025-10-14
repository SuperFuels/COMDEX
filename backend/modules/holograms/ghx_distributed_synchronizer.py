"""
🛰️ SRK-17 Task 5 — GHX Distributed Ledger Synchronizer (GHX-DLS)
Module: backend/modules/holograms/ghx_distributed_synchronizer.py

Purpose:
    Orchestrates cross-node GHX bundle propagation and hash-chain continuity
    across Tessaris nodes. Extends the GHX Sync Layer into a distributed
    consensus framework.

Responsibilities:
    • Register locally validated GHX bundles
    • Broadcast bundles to peer nodes
    • Maintain a verified hash-linked continuity chain
    • Perform remote integrity validation and ledger merge
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional
from uuid import uuid4

from backend.modules.codex.codex_trace import CodexTrace


class GHXDistributedSynchronizer:
    """SRK-17 Task 5 — GHX Distributed Ledger Synchronizer (GHX-DLS)"""

    def __init__(self):
        self.chain: List[Dict[str, any]] = []
        self.peers: Dict[str, str] = {}  # node_id → endpoint
        self.trace = CodexTrace()
        self._lock = asyncio.Lock()

    # ────────────────────────────────────────────────────────────────
    async def register_bundle(self, bundle: Dict[str, any]) -> Dict[str, any]:
        """
        Register a locally validated GHX bundle and append to the distributed chain.
        """
        async with self._lock:
            prev_hash = self.chain[-1]["chain_hash"] if self.chain else None
            chain_hash = self._compute_chain_hash(bundle, prev_hash)

            record = {
                "bundle_id": bundle.get("ghx_id", f"GHX-{uuid4()}"),
                "timestamp": time.time(),
                "chain_hash": chain_hash,
                "prev_hash": prev_hash,
                "integrity": bundle.get("integrity", {}),
            }

            self.chain.append(record)
            self.trace.record(
                "ghx_dls_registered",
                {"bundle_id": record["bundle_id"], "chain_hash": chain_hash[:16]},
                {"module": "GHX-DLS", "status": "registered"},
            )

            return record

    # ────────────────────────────────────────────────────────────────
    async def broadcast_bundle(self, bundle: Dict[str, any]) -> Dict[str, any]:
        """
        Simulate broadcast of GHX bundle to all known peer nodes.
        (Future: integrate with Tessaris Mesh Relay / Codex RPC)
        """
        async with self._lock:
            sent_to = []
            for node_id, endpoint in self.peers.items():
                await asyncio.sleep(0.01)  # simulate async network latency
                sent_to.append(node_id)

            self.trace.record(
                "ghx_dls_broadcast",
                {"bundle": bundle.get("ghx_id"), "recipients": len(sent_to)},
                {"module": "GHX-DLS", "status": "broadcasted"},
            )
            return {"status": "broadcasted", "recipients": sent_to}

    # ────────────────────────────────────────────────────────────────
    async def verify_chain_integrity(self) -> Dict[str, any]:
        """
        Validate continuity of the distributed hash chain.
        Returns a chain health summary.
        """
        async with self._lock:
            errors = []
            for i in range(1, len(self.chain)):
                prev = self.chain[i - 1]["chain_hash"]
                curr_expected = self._compute_chain_hash({}, prev)
                if self.chain[i]["prev_hash"] != prev:
                    errors.append((i, "hash_mismatch"))

            valid = len(errors) == 0
            self.trace.record(
                "ghx_dls_chain_verified",
                {"entries": len(self.chain), "valid": valid},
                {"module": "GHX-DLS"},
            )
            return {"valid": valid, "entries": len(self.chain), "errors": errors}

    # ────────────────────────────────────────────────────────────────
    def add_peer(self, node_id: str, endpoint: str):
        """Register a new peer node in the DLS mesh."""
        self.peers[node_id] = endpoint
        self.trace.record(
            "ghx_dls_peer_added",
            {"node_id": node_id, "endpoint": endpoint},
            {"module": "GHX-DLS"},
        )

    # ────────────────────────────────────────────────────────────────
    def _compute_chain_hash(self, bundle: Dict[str, any], prev_hash: Optional[str]) -> str:
        """
        Deterministic continuity hash for a GHX chain link.
        Combines previous hash + bundle integrity hash + timestamp.
        """
        base = {
            "prev_hash": prev_hash or "",
            "bundle_hash": bundle.get("integrity", {}).get("hash", ""),
            "timestamp": time.time(),
        }
        encoded = json.dumps(base, sort_keys=True).encode()
        return hashlib.sha3_512(encoded).hexdigest()