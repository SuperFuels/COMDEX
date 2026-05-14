"""
🧩 SRK-18.4 - GHX Ledger Federation (DLF)
Module: backend/modules/holograms/ghx_ledger_federation.py
Subsystem: Holograms / GHX Continuity Layer

Purpose:
    Implements multi-node synchronization of GHX Continuity Ledgers.
    Provides event propagation, merge reconciliation, and integrity validation
    across distributed DLF nodes.

Overview:
    * Federation mesh between GHXContinuityLedger instances
    * Propagation of sealed events to registered peers
    * Deterministic merge with rebroadcast deduplication
    * Cross-node integrity verification via SHA3-512 federation root

Dependencies:
    - backend.modules.holograms.ghx_continuity_ledger.GHXContinuityLedger

Author: Tessaris Core Engineering
Spec Ref: SRK-18 / Holograms Continuity Protocol
Version: 1.0.0 (October 2025)
"""

import hashlib
import time
import json
from typing import Dict, Any
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


class GHXLedgerFederation:
    """Federated DLF manager handling multi-node ledger synchronization."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.peers: Dict[str, GHXContinuityLedger] = {}
        self.local_ledger = GHXContinuityLedger(node_id=node_id)
        self.last_sync_hash: str | None = None

    # ────────────────────────────────────────────────────────────────
    def register_peer(self, peer_id: str, ledger: GHXContinuityLedger) -> None:
        """Attach another node's ledger into the federation mesh."""
        self.peers[peer_id] = ledger

    # ────────────────────────────────────────────────────────────────
    def broadcast_event(self, event_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append an event to local ledger and propagate a sealed copy to all peers.
        Each peer appends the event tagged with origin and signed by its hash root.
        """
        local_entry = self.local_ledger.append_event(event_type, meta, origin=self.node_id)

        for pid, ledger in self.peers.items():
            # Prevent rebroadcast loops
            if any(e["curr_hash"] == local_entry["curr_hash"] for e in ledger.chain):
                continue

            ledger.append_event(
                f"{event_type}@{self.node_id}",
                meta,
                origin=self.node_id,
                signature=local_entry["curr_hash"],
            )

        self.last_sync_hash = local_entry["curr_hash"]
        return local_entry

    # ────────────────────────────────────────────────────────────────
    def merge_ledgers(self) -> Dict[str, Any]:
        """
        Merge peer ledgers into the local ledger.

        Behavior:
            * Pulls in unseen base events from peers
            * Ignores rebroadcast variants (e.g. beta@B)
            * Removes redundant rebroadcasts once a base is received
            * Skips duplicates, self-origin, and loopbacks
        """
        merged = False

        local_hashes = {e["curr_hash"] for e in self.local_ledger.chain}
        local_ids = {e["event_id"] for e in self.local_ledger.chain}
        local_origin_bases = {
            (e["origin"], e["event_type"].split("@")[0]) for e in self.local_ledger.chain
        }

        for pid, peer_ledger in self.peers.items():
            for entry in peer_ledger.chain:
                eid = entry["event_id"]
                etype = entry["event_type"]
                origin = entry["origin"]
                curr_hash = entry["curr_hash"]
                base_type = etype.split("@")[0]

                # Skip duplicates or self-origin entries
                if eid in local_ids or curr_hash in local_hashes:
                    continue
                if origin == self.local_ledger.node_id:
                    continue
                if etype.endswith(f"@{self.local_ledger.node_id}"):
                    continue

                # Rebroadcast vs base resolution
                if "@" in etype:
                    if (origin, base_type) in local_origin_bases:
                        continue  # redundant rebroadcast
                else:
                    # Replace existing rebroadcasts with base event
                    self.local_ledger.chain = [
                        e for e in self.local_ledger.chain
                        if not (
                            e["origin"] == origin
                            and e["event_type"].startswith(f"{base_type}@")
                        )
                    ]
                    # Refresh sets after pruning
                    local_hashes = {e["curr_hash"] for e in self.local_ledger.chain}
                    local_ids = {e["event_id"] for e in self.local_ledger.chain}
                    local_origin_bases = {
                        (e["origin"], e["event_type"].split("@")[0])
                        for e in self.local_ledger.chain
                    }

                # Append new entry
                self.local_ledger.chain.append(entry)
                local_hashes.add(curr_hash)
                local_ids.add(eid)
                local_origin_bases.add((origin, base_type))
                merged = True

        if self.local_ledger.chain:
            self.local_ledger.last_hash = self.local_ledger.chain[-1]["curr_hash"]

        return {
            "merged": merged,
            "local_length": len(self.local_ledger.chain),
            "peer_count": len(self.peers),
        }

    # ────────────────────────────────────────────────────────────────
    def verify_federation_integrity(self) -> Dict[str, Any]:
        """
        Verify all ledgers in the federation share a common continuity root.

        Returns:
            {
                "root_hashes": {node_id: last_hash, ...},
                "federation_hash": SHA3-512 over sorted root set,
                "consistent": bool,
                "timestamp": float
            }
        """
        roots = {pid: (ledger.last_hash or "") for pid, ledger in self.peers.items()}
        roots[self.node_id] = self.local_ledger.last_hash or ""
        unique_roots = set(roots.values())

        federation_hash = hashlib.sha3_512(
            json.dumps(roots, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return {
            "root_hashes": roots,
            "federation_hash": federation_hash,
            "consistent": len(unique_roots) == 1,
            "timestamp": time.time(),
        }