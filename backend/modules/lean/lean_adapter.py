# -*- coding: utf-8 -*-
"""
LeanAdapter - Unified Bridge between Tessaris QQC Core and Lean proof ecosystem.
──────────────────────────────────────────────────────────────────────────────
High-level API used by QQC Central Kernel.

Key updates:
- Uses the newer converters that accept lean_text/lean_path/source_id
- Keeps adapter resilient (soft-import optional modules)
- Adds small helpers: _safe_len, _load_json_file
- Keeps current method names so callers don’t break
"""

from __future__ import annotations

import logging
import os
import json
from typing import Dict, Any, Optional, List, Callable

from backend.symatics import lean_bridge

logger = logging.getLogger(__name__)


# ----------------------------
# Soft imports (keep adapter resilient)
# ----------------------------
def _soft_import(path: str):
    try:
        module = __import__(path, fromlist=["*"])
        return module
    except Exception as e:
        logger.debug(f"[LeanAdapter] soft-import failed: {path} ({e})")
        return None


lean_batch = _soft_import("backend.modules.lean.lean_batch")
lean_injector = _soft_import("backend.modules.lean.lean_injector")
lean_exporter = _soft_import("backend.modules.lean.lean_exporter")
lean_to_glyph = _soft_import("backend.modules.lean.lean_to_glyph")
lean_ghx = _soft_import("backend.modules.lean.lean_ghx")
lean_watch = _soft_import("backend.modules.lean.lean_watch")
glyph_to_lean = _soft_import("backend.modules.lean.glyph_to_lean")
symatics_to_lean = _soft_import("backend.modules.lean.symatics_to_lean")
lean_proofverifier = _soft_import("backend.modules.lean.lean_proofverifier")
lean_audit = _soft_import("backend.modules.lean.lean_audit")
lean_proofviz = _soft_import("backend.modules.lean.lean_proofviz")


def _load_json_file(p: str) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_len(x: Any) -> int:
    try:
        return len(x)  # type: ignore[arg-type]
    except Exception:
        return 0


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

    def convert(
        self,
        *,
        lean_path: Optional[str] = None,
        lean_text: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert Lean into CodexLang structures.

        Supports filesystem OR in-memory text:
          - convert(lean_path="x.lean")
          - convert(lean_text="theorem ...", source_id="kg://...")
        """
        if not lean_to_glyph:
            raise RuntimeError("lean_to_glyph module unavailable")

        # Prefer updated signature if present (lean_path/lean_text/source_id)
        fn = getattr(lean_to_glyph, "convert_lean_to_codexlang", None)
        if not callable(fn):
            raise RuntimeError("lean_to_glyph.convert_lean_to_codexlang unavailable")

        try:
            return fn(lean_path=lean_path, lean_text=lean_text, source_id=source_id)  # type: ignore[misc]
        except TypeError:
            # Back-compat: older converter only accepted (path)
            if not lean_path:
                raise ValueError("This converter version requires lean_path")
            return fn(lean_path)  # type: ignore[misc]

    # ────────────────────────────────────────────────
    # Container export / injection
    # ────────────────────────────────────────────────
    def export_container(self, lean_path: str, container_type: str = "dc") -> Dict[str, Any]:
        """Build a container JSON structure from a Lean file."""
        if not lean_exporter:
            raise RuntimeError("lean_exporter module unavailable")
        build = getattr(lean_exporter, "build_container_from_lean", None)
        if not callable(build):
            raise RuntimeError("lean_exporter.build_container_from_lean unavailable")
        return build(lean_path, container_type)

    def inject(
        self,
        container_path: str,
        lean_path: str,
        overwrite: bool = True,
        normalize: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Inject Lean theorems into a symbolic container on disk.

        kwargs is allowed to pass through new flags without breaking callers.
        """
        if not lean_injector:
            raise RuntimeError("lean_injector module unavailable")

        load_container = getattr(lean_injector, "load_container", None)
        save_container = getattr(lean_injector, "save_container", None)
        inject_fn = getattr(lean_injector, "inject_theorems_into_container", None)

        if not callable(load_container) or not callable(save_container) or not callable(inject_fn):
            raise RuntimeError("lean_injector APIs unavailable")

        container = load_container(container_path)
        injected = inject_fn(container, lean_path, overwrite=overwrite, normalize=normalize, **kwargs)
        save_container(injected, container_path)
        logger.info(f"[LeanAdapter] Injected {lean_path} -> {container_path}")
        return injected

    # ────────────────────────────────────────────────
    # Batch and ledger operations
    # ────────────────────────────────────────────────
    def run_batch(self, proofs_dir: str = "backend/symatics/proofs", update_codex: bool = True) -> Dict[str, Any]:
        """Run Lean batch verification + Codex ledger update."""
        # lean_bridge.run_lean_proofs is your existing entrypoint
        self.last_summary = lean_bridge.run_lean_proofs(proofs_dir, update_codex)
        self.last_ledger = (self.last_summary or {}).get("ledger_path")
        return self.last_summary or {"status": "no_summary"}

    # ────────────────────────────────────────────────
    # GHX packetization
    # ────────────────────────────────────────────────
    def to_ghx_bundle(
        self,
        entries: List[Dict[str, Any]],
        out_path: str = "backend/holograms/lean_bundle.ghx.json",
        container_id: Optional[str] = None,
    ) -> str:
        """Bundle verified theorems into a GHX holographic proof packet."""
        if not lean_ghx:
            raise RuntimeError("lean_ghx module unavailable")
        fn = getattr(lean_ghx, "bundle_packets", None)
        if not callable(fn):
            raise RuntimeError("lean_ghx.bundle_packets unavailable")

        self.last_packets = fn(entries, out_path, container_id=container_id, source_path=None)
        logger.info(f"[LeanAdapter] GHX bundle created -> {out_path}")
        return out_path

    # ────────────────────────────────────────────────
    # Reverse conversion (Codex -> Lean)
    # ────────────────────────────────────────────────
    def from_codex(self, container: dict, out_path: str) -> str:
        """Generate a .lean file from a Codex container."""
        if not glyph_to_lean:
            raise RuntimeError("glyph_to_lean module unavailable")

        build = getattr(glyph_to_lean, "build_lean_from_codex", None) or getattr(
            glyph_to_lean, "build_lean_from_container", None
        )
        if not callable(build):
            raise RuntimeError("glyph_to_lean build function unavailable")

        # Prefer the newer writer if present
        try:
            build(container, out_path)  # legacy signature
        except TypeError:
            # new signature may return text; we save it
            text = build(container)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)

        # Audit (soft)
        if lean_audit and hasattr(lean_audit, "audit_event") and hasattr(lean_audit, "build_export_event"):
            try:
                lean_audit.audit_event(
                    lean_audit.build_export_event(
                        out_path=out_path,
                        container_id=container.get("id"),
                        container_type=container.get("type"),
                        lean_path=out_path,
                        num_items=_safe_len(container.get("symbolic_logic", [])),
                    )
                )
            except Exception:
                pass

        logger.info(f"[LeanAdapter] Generated Lean file from Codex container -> {out_path}")
        return out_path

    def from_symatics(self, expr: str, name: str = "symatics_axiom", out_path: Optional[str] = None) -> str:
        """Translate a raw Symatics algebraic expression into a Lean axiom."""
        if not symatics_to_lean:
            raise RuntimeError("symatics_to_lean module unavailable")

        fn = getattr(symatics_to_lean, "symatics_to_lean", None)
        if not callable(fn):
            raise RuntimeError("symatics_to_lean.symatics_to_lean unavailable")

        lean_code = fn(expr, name)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(lean_code)
            logger.info(f"[LeanAdapter] Symatics expression exported to {out_path}")
        return lean_code

    # ────────────────────────────────────────────────
    # Proof verification
    # ────────────────────────────────────────────────
    def verify_container(self, container_path: str, autosave: bool = True) -> bool:
        """Run full Lean proof verification for a container."""
        if not lean_proofverifier:
            raise RuntimeError("lean_proofverifier module unavailable")

        validate = getattr(lean_proofverifier, "validate_lean_container", None)
        if not callable(validate):
            raise RuntimeError("lean_proofverifier.validate_lean_container unavailable")

        container = _load_json_file(container_path)
        result = bool(validate(container, autosave=autosave))

        # Audit (soft)
        if lean_audit and hasattr(lean_audit, "audit_event"):
            try:
                lean_audit.audit_event(
                    {
                        "kind": "lean.verify",
                        "container": container_path,
                        "status": "ok" if result else "error",
                    }
                )
            except Exception:
                pass

        logger.info(f"[LeanAdapter] Verification {'passed' if result else 'failed'} for {container_path}")
        return result

    # ────────────────────────────────────────────────
    # Visualization / Telemetry
    # ────────────────────────────────────────────────
    def visualize(self, container_path: str, png_out: str = "viz/lean_graph.png") -> dict:
        """Attach Mermaid + PNG proof graph to container."""
        if not lean_proofviz:
            raise RuntimeError("lean_proofviz module unavailable")

        attach = getattr(lean_proofviz, "attach_visualizations", None)
        if not callable(attach):
            raise RuntimeError("lean_proofviz.attach_visualizations unavailable")

        container = _load_json_file(container_path)
        viz_data = attach(container, png_path=png_out)
        logger.info(f"[LeanAdapter] Visualization attached -> {png_out}")
        return viz_data

    # ────────────────────────────────────────────────
    # Watch + live sync
    # ────────────────────────────────────────────────
    def watch(self, path: str = "backend/symatics/proofs", callback: Optional[Callable[..., Any]] = None):
        """Start Lean file watcher (stub-friendly)."""
        if not lean_watch:
            logger.warning("[LeanAdapter] lean_watch unavailable; returning False")
            return False

        fn = getattr(lean_watch, "watch_lean_session", None)
        if not callable(fn):
            logger.warning("[LeanAdapter] watch_lean_session unavailable; returning False")
            return False

        return fn(path, callback=callback)

    # ────────────────────────────────────────────────
    # Summary and metrics
    # ────────────────────────────────────────────────
    def summarize(self) -> Dict[str, Any]:
        """Return last run summary for telemetry."""
        return self.last_summary or {"status": "no_runs"}

    def status(self) -> Dict[str, Any]:
        """Compact status snapshot for QQC dashboard."""
        verified = _safe_len((self.last_summary or {}).get("verified", []))
        failed = _safe_len((self.last_summary or {}).get("failed", []))
        return {
            "verified": verified,
            "failed": failed,
            "ledger": self.last_ledger,
            "ghx_packets": _safe_len(self.last_packets),
        }