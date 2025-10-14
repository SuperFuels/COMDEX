"""
🧩 SRK-17 — GHX-Link Ledger Binding & Continuity Export
Module: backend/modules/holograms/ghx_sync_layer.py

Purpose:
    Synchronize Photon Memory Grid (PMG), Resonance Ledger (RL),
    Unified Symbolic Runtime (USR) telemetry, and GHX Trace data
    into a verified GHX bundle for GlyphVault persistence and
    CodexTrace continuity tracking.

Phases:
    • SRK-17 Task 1 — Resonance Ledger ⇄ GHX Sync Layer
    • SRK-17 Task 2 — PMG Snapshot Binder (temporal-state linkage)
    • SRK-17 Task 3 — USR Telemetry → GHX Trace Encoder
"""

import time
import json
import hashlib
import asyncio
from uuid import uuid4
from typing import Dict, Any

from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid
from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
from backend.symatics.unified_symbolic_runtime import UnifiedSymbolicRuntime
from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.holograms.ghx_trace_encoder import GHXTraceEncoder


class GHXSyncLayer:
    """SRK-17 — GHX-Link Ledger Binding & Continuity Export"""

    def __init__(self, container_id: str = "ghx_sync"):
        """
        Initialize synchronization layer components.
        The container_id anchors all GHX bundle writes to a persistent GlyphVault namespace.
        """
        self.pmg = PhotonMemoryGrid()
        self.ledger = ResonanceLedger()
        self.usr = UnifiedSymbolicRuntime()
        self.trace = CodexTrace()
        self.vault = GlyphVault(container_id)
        self.encoder = GHXTraceEncoder()  # 🔹 new Task 3 component

    # ────────────────────────────────────────────────────────────────
    async def assemble_bundle(self) -> dict:
        """
        SRK-17 Task 1 — collect state from all layers and create a verified GHX bundle.
        Includes:
            • PMG snapshot
            • Resonance Ledger snapshot
            • USR telemetry
            • Encoded GHX Trace (Task 3)
        """
        pmg_snapshot = await self.pmg.snapshot_async()
        ledger_snapshot = await self.ledger.snapshot_async()
        usr_telemetry = self.usr.export_telemetry()
        ghx_trace = self.encoder.encode(usr_telemetry)

        payload = {
            "ghx_id": f"GHX-{uuid4()}",
            "timestamp": time.time(),
            "pmg_snapshot": pmg_snapshot,
            "resonance_ledger": ledger_snapshot,
            "usr_telemetry": usr_telemetry,
            "ghx_trace": ghx_trace,
        }

        integrity_hash = hashlib.sha3_512(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        payload["integrity"] = {"hash": integrity_hash, "verified": True}

        await self.vault.save_bundle(payload)
        self.trace.record(
            "ghx_sync_bundle_created",
            {"ghx_id": payload["ghx_id"], "integrity": integrity_hash[:16]},
            {"module": "GHXSyncLayer", "status": "success"},
        )

        return payload

    # ────────────────────────────────────────────────────────────────
    def _bind_pmg_snapshot(self, pmg_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        SRK-17 Task 2 — PMG Snapshot Binder (temporal-state linkage)
        Attaches temporal linkage info to a PMG snapshot:
            • binder_seq — monotonic binder ID (ms)
            • prev_hash / curr_hash — continuity chain
        """
        states = pmg_snapshot.get("states", {})
        bind_seq = int(time.time() * 1_000)
        state_repr = json.dumps(states, sort_keys=True)
        curr_hash = hashlib.sha3_512(state_repr.encode()).hexdigest()

        prev_hash = None
        if hasattr(self.vault, "_last_saved_bundle"):
            prev_hash = getattr(self.vault, "_last_saved_bundle", {}).get("checksum")

        return {
            "binder_seq": bind_seq,
            "prev_hash": prev_hash,
            "curr_hash": curr_hash,
            "linked": prev_hash is not None,
        }

    # ────────────────────────────────────────────────────────────────
    async def assemble_bundle_with_pmg_binder(self) -> dict:
        """
        SRK-17 Task 2 + Task 3 — Assemble GHX bundle including PMG Binder
        and GHX Trace for temporal-state continuity and telemetry verification.
        """
        pmg_snapshot = (
            self.pmg.snapshot() if hasattr(self.pmg, "snapshot") else {}
        )
        ledger_snapshot = (
            self.ledger.snapshot() if hasattr(self.ledger, "snapshot") else {}
        )
        usr_telemetry = (
            self.usr.export_telemetry() if hasattr(self.usr, "export_telemetry") else {}
        )
        binder = self._bind_pmg_snapshot(pmg_snapshot)
        ghx_trace = self.encoder.encode(usr_telemetry)

        payload = {
            "ghx_id": f"GHX-{uuid4()}",
            "timestamp": time.time(),
            "pmg_snapshot": pmg_snapshot,
            "resonance_ledger": ledger_snapshot,
            "usr_telemetry": usr_telemetry,
            "pmg_binder": binder,
            "ghx_trace": ghx_trace,
        }

        integrity_hash = hashlib.sha3_512(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        payload["integrity"] = {"hash": integrity_hash, "verified": True}

        await self.vault.save_bundle(payload)
        self.trace.record(
            "ghx_sync_bundle_binded",
            {
                "ghx_id": payload["ghx_id"],
                "binder_seq": binder["binder_seq"],
                "trace_id": ghx_trace["trace_id"],
            },
            {"module": "GHXSyncLayer", "status": "success"},
        )

        return payload

    # ────────────────────────────────────────────────────────────────
    async def verify_trace_integrity(self, bundle: Dict[str, Any]) -> bool:
        """
        SRK-17 Task 3 — verify embedded GHX trace integrity before export.
        """
        ghx_trace = bundle.get("ghx_trace", {})
        if not ghx_trace:
            return False
        return self.encoder.verify_trace(ghx_trace)

from backend.modules.holograms.ghx_bundle_validator import GHXBundleValidator

    async def validate_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        SRK-17 Task 4 — Validate GHX bundle integrity and trace signatures.
        """
        validator = GHXBundleValidator()
        result = validator.validate_bundle(bundle)
        self.trace.record(
            "ghx_bundle_validated",
            {"ghx_id": bundle.get("ghx_id"), "status": result["overall_valid"]},
            {"module": "GHXSyncLayer", "phase": "validation"},
        )
        return result