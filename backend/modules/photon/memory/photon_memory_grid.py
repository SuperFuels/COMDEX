"""
🔷 Photon Memory Grid (PMG) - SRK-12 Task 2 / SRK-14 Task 3 / SRK-17 Sync Update
Entanglement-aware persistence layer for photon computation states.
Handles state persistence, entanglement linkage, integrity validation,
and optional synchronization with the Resonance Ledger.
"""

import time
import asyncio
import hashlib
from typing import Dict, Any, Optional
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer


class PhotonMemoryGrid:
    def __init__(self):
        # Core persistence and synchronization
        self.grid: Dict[str, Dict[str, Any]] = {}
        self._photon_state_map: Dict[str, Dict[str, Any]] = {}
        self._entanglement_links: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

        # Security & policy integration
        self.policy = QKDPolicyEnforcer()

        # Optional resonance ledger handle (SRK-14 Task 3)
        # Optional resonance ledger handle (SRK-14 Task 3)
        from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
        self._ledger = ResonanceLedger()

    # ────────────────────────────────────────────────────────────────
    def attach_ledger(self, ledger):
        """Attach a Resonance Ledger instance for synchronization."""
        self._ledger = ledger

    def get_entanglement_record(self, entanglement_id: str):
        """Retrieve an entanglement record from the resonance ledger."""
        return getattr(self, "_entanglement_ledger", {}).get(entanglement_id)   

    def store_entanglement_state(self, entanglement_id: str, record: dict):
        """
        SRK-14 - Persist entanglement coherence + resonance state into PMG ledger.
        This is called by the EntanglementEngine whenever a new entanglement is registered.
        """
        if not hasattr(self, "_entanglement_ledger"):
            self._entanglement_ledger = {}

        self._entanglement_ledger[entanglement_id] = {
            "entanglement_id": entanglement_id,
            "timestamp": record.get("timestamp"),
            "field_potential": record.get("field_potential"),
            "coherence": record.get("coherence"),
            "entropy_shift": record.get("entropy_shift"),
            "wave_a_id": record.get("wave_a_id"),
            "wave_b_id": record.get("wave_b_id"),
            "status": "active",
        }
        return True

        # ───────────────────────────────────────────────
    def archive_collapse_event(self, entanglement_id: str, coherence_loss: float, sqi_drift: float):
        """
        SRK-15 - Archive collapsed entanglement into the Resonant Decay Ledger.

        When an entanglement collapses (either naturally or by forced coherence failure),
        we record the energy/coherence loss and SQI drift for resonance continuity mapping.
        """
        if not hasattr(self, "_resonance_decay_ledger"):
            self._resonance_decay_ledger = {}

        record = {
            "entanglement_id": entanglement_id,
            "timestamp": time.time(),
            "coherence_loss": round(coherence_loss, 6),
            "sqi_drift": round(sqi_drift, 6),
            "status": "collapsed",
        }

        self._resonance_decay_ledger[entanglement_id] = record
        return record

    def get_resonance_decay_ledger(self):
        """Return all collapsed entanglement archives."""
        return getattr(self, "_resonance_decay_ledger", {})
 
    # ────────────────────────────────────────────────────────────────
    async def store_capsule_state(self, capsule_id: str, state: Dict[str, Any]):
        """Persist photon field state with coherence metadata and checksum."""
        async with self.lock:
            coherence = state.get("coherence", 1.0)
            timestamp = time.time()
            checksum = self._checksum_state(state)

            record = {
                "state": state,
                "coherence": coherence,
                "timestamp": timestamp,
                "checksum": checksum,
            }

            # Maintain both short-term and long-term maps
            self.grid[capsule_id] = record
            self._photon_state_map[capsule_id] = record

            # 🔶 SRK-14 Task 3 - register event in resonance ledger
            if self._ledger:
                await self._ledger.register_link(
                    capsule_id,
                    capsule_id,  # self-reference denotes snapshot origin
                    phi_delta=0.0,
                    coherence=coherence,
                    meta={"checksum": checksum, "event": "store_capsule_state"},
                )

            return {
                "status": "stored",
                "capsule_id": capsule_id,
                "coherence": coherence,
                "checksum": checksum,
                "time": timestamp,
            }

    # ────────────────────────────────────────────────────────────────
    def recall_state(self, capsule_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a previously stored photon capsule state."""
        state = self.grid.get(capsule_name)
        if not state:
            return None
        return {
            **state,
            "checksum": state.get("checksum", self._checksum_state(state)),
            "restored": True,
        }

    # ────────────────────────────────────────────────────────────────
    def restore_capsule_state(self, capsule_id: str) -> Dict[str, Any]:
        """Retrieve photon state for re-entanglement (legacy alias)."""
        return self._photon_state_map.get(capsule_id, {})

    # ────────────────────────────────────────────────────────────────
    def link_entanglement(self, capsule_a: str, capsule_b: str, phi_delta: float, coherence: float):
        """Record a persistent resonance correlation between two capsules."""
        key = f"{capsule_a}↔{capsule_b}"
        link = {
            "phi_delta": phi_delta,
            "coherence": coherence,
            "timestamp": time.time(),
        }
        self._entanglement_links[key] = link

        # 🔶 SRK-14 Task 3 - ledger synchronization
        if self._ledger:
            asyncio.create_task(
                self._ledger.register_link(
                    capsule_a,
                    capsule_b,
                    phi_delta=phi_delta,
                    coherence=coherence,
                    meta={"event": "link_entanglement"},
                )
            )
        return {"status": "linked", "link": key}

    # ────────────────────────────────────────────────────────────────
    async def collapse_on_expiry(self, coherence_threshold: float = 0.25):
        """Auto-collapse photon fields below coherence threshold."""
        expired = []
        async with self.lock:
            for cid, entry in list(self._photon_state_map.items()):
                if entry.get("coherence", 1.0) < coherence_threshold:
                    expired.append(cid)
                    del self._photon_state_map[cid]
                    self.grid.pop(cid, None)
        return {"collapsed": expired, "count": len(expired)}

    # ────────────────────────────────────────────────────────────────
    async def snapshot_to_glyphvault(self):
        """Persist current PMG state to GlyphVault."""
        try:
            from backend.modules.glyphwave.vault.glyphvault_writer import GlyphVaultWriter
            writer = GlyphVaultWriter()
            await writer.save_snapshot({
                "states": self._photon_state_map,
                "links": self._entanglement_links,
                "timestamp": time.time(),
            })
            # Optionally record snapshot event in ledger
            if self._ledger:
                await self._ledger.propagate_resonance()
            return {"status": "snapshot_saved", "count": len(self._photon_state_map)}
        except ImportError:
            return {"status": "snapshot_skipped", "reason": "GlyphVaultWriter unavailable"}

    # ────────────────────────────────────────────────────────────────
    def integrity_check(self, capsule_name: str) -> bool:
        """Verify state checksum matches expected hash."""
        state = self.grid.get(capsule_name)
        if not state:
            return False
        stored_checksum = state.get("checksum")
        return stored_checksum == self._checksum_state(state.get("state", {}))

    # ────────────────────────────────────────────────────────────────
    def _checksum_state(self, state: Dict[str, Any]) -> str:
        """Compute a deterministic checksum of a photon state."""
        try:
            state_repr = str(sorted(state.items()))
        except Exception:
            state_repr = str(state)
        return hashlib.sha3_256(state_repr.encode()).hexdigest()

    # ────────────────────────────────────────────────────────────────
    async def snapshot_async(self) -> Dict[str, Any]:
        """
        🔹 SRK-17 Update - Asynchronous state snapshot for GHX Sync Layer.
        Provides a lightweight export of PMG state and entanglement map.
        """
        return await asyncio.to_thread(self._snapshot_sync)

    def _snapshot_sync(self) -> Dict[str, Any]:
        """Synchronous snapshot implementation wrapped by snapshot_async()."""
        return {
            "timestamp": time.time(),
            "state_count": len(self._photon_state_map),
            "link_count": len(self._entanglement_links),
            "states": self._photon_state_map,
            "links": self._entanglement_links,
        }

    # ────────────────────────────────────────────────────────────────
    def retrieve_capsule_state(self, capsule_id: str) -> Dict[str, Any]:
        """
        SRK-14 Compatibility Alias:
        Retrieve a capsule's photon state. Automatically unwraps nested `state`
        dicts for legacy test and BeamPersistence compatibility.
        """
        record = self.restore_capsule_state(capsule_id)
        if not record:
            return {}
        # 🔧 unwrap if stored in { "state": {...}, ... }
        if "state" in record and isinstance(record["state"], dict):
            return record["state"]
        return record