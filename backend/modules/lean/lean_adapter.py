# -*- coding: utf-8 -*-
"""
LeanAdapter - Unified Bridge between Tessaris QQC Core and Lean proof ecosystem.
──────────────────────────────────────────────────────────────────────────────
Delegates to Lean parser, converter, exporter, injector, verification, and GHX tools.
Provides high-level API used by QQC Central Kernel (qqc_central_kernel.py).
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
from backend.symatics import lean_bridge
from backend.modules.lean import (
    lean_batch,
    lean_injector,
    lean_exporter,
    lean_to_glyph,
    lean_ghx,
    lean_watch,
    glyph_to_lean,
    symatics_to_lean,
    lean_proofverifier,
    lean_audit,
    lean_proofviz,
)

logger = logging.getLogger(__name__)


class LeanAdapter:
    """Main QQC integration interface for Lean proofs and theorem containers."""

    def __init__(self):
        self.bridge = lean_bridge.LeanBridge()
        self.last_summary: Optional[Dict[str, Any]] = None
        self.last_ledger: Optional[str] = None
        self.last_packets: List[str] = []
        logger.info("[LeanAdapter] Initialized")

    # ────────────────────────────────────────────────
    # Parsing + conversion
    # ────────────────────────────────────────────────
    def parse(self, lean_path: str) -> List[Dict[str, Any]]:
        """Parse a single Lean file -> declaration dicts."""
        if not os.path.isfile(lean_path):
            raise FileNotFoundError(lean_path)
        return self.bridge.parse(lean_path)

    def convert(self, lean_path: str) -> Dict[str, Any]:
        """Convert a Lean file into CodexLang structures."""
        return lean_to_glyph.convert_lean_to_codexlang(lean_path)

    # ────────────────────────────────────────────────
    # Container export / injection
    # ────────────────────────────────────────────────
    def export_container(self, lean_path: str, container_type: str = "dc") -> Dict[str, Any]:
        """Build a container JSON structure from a Lean file."""
        return lean_exporter.build_container_from_lean(lean_path, container_type)

    def inject(self, container_path: str, lean_path: str, overwrite=True, normalize=True) -> Dict[str, Any]:
        """Inject Lean theorems into a symbolic container on disk."""
        container = lean_injector.load_container(container_path)
        injected = lean_injector.inject_theorems_into_container(
            container, lean_path, overwrite=overwrite, normalize=normalize
        )
        lean_injector.save_container(injected, container_path)
        logger.info(f"[LeanAdapter] Injected {lean_path} -> {container_path}")
        return injected

    # ────────────────────────────────────────────────
    # Batch and ledger operations
    # ────────────────────────────────────────────────
    def run_batch(self, proofs_dir: str = "backend/symatics/proofs", update_codex: bool = True) -> Dict[str, Any]:
        """Run Lean batch verification + Codex ledger update."""
        self.last_summary = lean_bridge.run_lean_proofs(proofs_dir, update_codex)
        self.last_ledger = self.last_summary.get("ledger_path")
        return self.last_summary

    # ────────────────────────────────────────────────
    # GHX packetization
    # ────────────────────────────────────────────────
    def to_ghx_bundle(
        self,
        entries: List[Dict[str, Any]],
        out_path="backend/holograms/lean_bundle.ghx.json",
        container_id=None,
    ) -> str:
        """Bundle verified theorems into a GHX holographic proof packet."""
        self.last_packets = lean_ghx.bundle_packets(entries, out_path, container_id=container_id, source_path=None)
        logger.info(f"[LeanAdapter] GHX bundle created -> {out_path}")
        return out_path

    # ────────────────────────────────────────────────
    # Reverse conversion (Codex -> Lean)
    # ────────────────────────────────────────────────
    def from_codex(self, container: dict, out_path: str) -> str:
        """Generate a .lean file from a CodexLang container."""
        glyph_to_lean.build_lean_from_codex(container, out_path)
        lean_audit.audit_event(
            lean_audit.build_export_event(
                out_path=out_path,
                container_id=container.get("id"),
                container_type=container.get("type"),
                lean_path=out_path,
                num_items=len(container.get("symbolic_logic", [])),
            )
        )
        logger.info(f"[LeanAdapter] Generated Lean file from Codex container -> {out_path}")
        return out_path

    def from_symatics(self, expr: str, name="symatics_axiom", out_path=None) -> str:
        """Translate a raw Symatics algebraic expression into a Lean axiom."""
        lean_code = symatics_to_lean.symatics_to_lean(expr, name)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(lean_code)
            logger.info(f"[LeanAdapter] Symatics expression exported to {out_path}")
        return lean_code

    # ────────────────────────────────────────────────
    # Proof verification
    # ────────────────────────────────────────────────
    def verify_container(self, container_path: str, autosave=True) -> bool:
        """Run full Lean proof verification for a container."""
        with open(container_path, "r", encoding="utf-8") as f:
            container = json.load(f)
        result = lean_proofverifier.validate_lean_container(container, autosave=autosave)
        lean_audit.audit_event(
            {
                "kind": "lean.verify",
                "container": container_path,
                "status": "ok" if result else "error",
            }
        )
        logger.info(f"[LeanAdapter] Verification {'passed' if result else 'failed'} for {container_path}")
        return result

    # ────────────────────────────────────────────────
    # Visualization / Telemetry
    # ────────────────────────────────────────────────
    def visualize(self, container_path: str, png_out="viz/lean_graph.png") -> dict:
        """Attach Mermaid + PNG proof graph to container."""
        with open(container_path, "r", encoding="utf-8") as f:
            container = json.load(f)
        viz_data = lean_proofviz.attach_visualizations(container, png_path=png_out)
        logger.info(f"[LeanAdapter] Visualization attached -> {png_out}")
        return viz_data

    # ────────────────────────────────────────────────
    # Watch + live sync
    # ────────────────────────────────────────────────
    def watch(self, path="backend/symatics/proofs", callback=None):
        """Start Lean file watcher (no-op in stub mode)."""
        return lean_watch.watch_lean_session(path, callback=callback)

    # ────────────────────────────────────────────────
    # Summary and metrics
    # ────────────────────────────────────────────────
    def summarize(self) -> Dict[str, Any]:
        """Return last run summary for telemetry."""
        return self.last_summary or {"status": "no_runs"}

    def status(self) -> Dict[str, Any]:
        """Compact status snapshot for QQC dashboard."""
        return {
            "verified": len(self.last_summary.get("verified", [])) if self.last_summary else 0,
            "failed": len(self.last_summary.get("failed", [])) if self.last_summary else 0,
            "ledger": self.last_ledger,
            "ghx_packets": len(self.last_packets),
        }