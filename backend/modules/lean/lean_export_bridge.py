# ============================================================
# 🔁 Knowledge Graph -> Lean Export Bridge
# ============================================================
"""
Allows bidirectional synchronization between the Knowledge Graph (KG)
and Lean formal files.

NOTE (important):
- This exporter produces a *Lean-compilable artifact* that encodes KG data
  as constants/defs plus an optional "stub theorem" scaffold.
- It does NOT magically prove physics. Proofs still require real Lean theorems
  + supporting lemmas/imports.

Design goals:
- Always emit syntactically safe Lean (no raw/invalid string literals).
- Keep files minimal + buildable (no Mathlib dependency by default).
- Provide a scaffold area where later "real theorems" can be written.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

LEAN_EXPORT_DIR = "data/lean/atoms_sync"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _safe_filename(s: str) -> str:
    s = (s or "atom").strip()
    for ch in [":", "@", "/", "\\", " "]:
        s = s.replace(ch, "_")
    return s or "atom"


def _lean_escape_string(s: str) -> str:
    """
    Escape a Python string so it can live inside a Lean double-quoted string literal.
    """
    if s is None:
        s = ""
    s = str(s)
    # Lean supports \n, \t, \", \\ in String literals
    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s


def _json_compact(obj: Any, max_len: int = 4000) -> str:
    """
    Compact JSON for embedding; truncated to avoid gigantic Lean files.
    """
    try:
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        txt = json.dumps({"error": "unserializable"}, ensure_ascii=False)
    if len(txt) > max_len:
        txt = txt[:max_len] + "…"
    return txt


def _find_node_in_registry(kg: Any, atom_id: str) -> Optional[Dict[str, Any]]:
    """
    Registry-only lookup (current KG writer design).
    """
    registry = getattr(kg, "node_registry", {}) or {}
    # direct hit
    if atom_id in registry and isinstance(registry[atom_id], dict):
        return registry[atom_id]

    # scan fallback
    for n in registry.values():
        if not isinstance(n, dict):
            continue
        if n.get("id") == atom_id or n.get("label") == atom_id:
            return n
    return None


# ------------------------------------------------------------
# 🧩 Export Harmonic Atom from KG to Lean file
# ------------------------------------------------------------

def export_atom_to_lean(atom_id: str, out_dir: str = LEAN_EXPORT_DIR) -> str:
    """
    Generates or updates a .lean file based on a Harmonic Atom stored in KG.

    Returns:
        Path to generated .lean file ("" on failure).
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph writer unavailable")

        node = _find_node_in_registry(kg, atom_id)
        if not node:
            raise ValueError(
                f"Harmonic Atom not found in KG registry: {atom_id}. "
                "Note: this exporter only sees nodes present in kg.node_registry."
            )

        label = node.get("label", atom_id)
        kind = node.get("kind", "harmonic_atom")
        sqi = node.get("sqi", 0.0)
        ts = node.get("timestamp") or datetime.utcnow().isoformat(timespec="seconds") + "Z"
        waveform = node.get("waveform", {})

        # Safe Lean strings
        label_lean = _lean_escape_string(label)
        kind_lean = _lean_escape_string(kind)
        ts_lean = _lean_escape_string(ts)
        waveform_json = _json_compact(waveform, max_len=4000)
        waveform_lean = _lean_escape_string(waveform_json)

        # Ensure export directory
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{_safe_filename(label)}.lean"
        path = os.path.join(out_dir, fname)

        # Emit Lean module
        module_name = _safe_filename(label)
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        with open(path, "w", encoding="utf-8") as f:
            f.write("-- Auto-exported from Tessaris Knowledge Graph\n")
            f.write(f"-- Generated: {now}\n\n")

            # Keep it buildable without Mathlib
            f.write("namespace TessarisKG\n\n")

            f.write("/-- Data-only record exported from the KG. -/\n")
            f.write("structure HarmonicAtom where\n")
            f.write("  id        : String\n")
            f.write("  label     : String\n")
            f.write("  kind      : String\n")
            f.write("  sqi       : Float\n")
            f.write("  timestamp : String\n")
            f.write("deriving Repr\n\n")

            f.write("/-- Embedded waveform metadata (compact JSON string). -/\n")
            f.write(f"def waveform_meta_{module_name} : String := \"{waveform_lean}\"\n\n")

            f.write("/-- The exported atom constant (data). -/\n")
            f.write(f"def atom_{module_name} : HarmonicAtom := {{\n")
            f.write(f"  id := \"{_lean_escape_string(atom_id)}\",\n")
            f.write(f"  label := \"{label_lean}\",\n")
            f.write(f"  kind := \"{kind_lean}\",\n")
            # Float printing: keep simple; Lean Float literal expects decimal
            try:
                sqi_f = float(sqi)
            except Exception:
                sqi_f = 0.0
            f.write(f"  sqi := {sqi_f},\n")
            f.write(f"  timestamp := \"{ts_lean}\"\n")
            f.write("}\n\n")

            # Optional scaffold for "real" theorems
            f.write("/-\n")
            f.write("  Proof scaffold\n")
            f.write("  --------------\n")
            f.write("  Professionals will want *statements* that are checkable:\n")
            f.write("    - invariants about exported structures,\n")
            f.write("    - relationships between atoms,\n")
            f.write("    - derived quantities defined in Lean,\n")
            f.write("    - and proofs using a trusted library (often Mathlib).\n")
            f.write("\n")
            f.write("  This file intentionally ships with a trivial theorem so the module compiles.\n")
            f.write("  Replace/extend with real theorems as you formalize your calculus.\n")
            f.write("-/\n\n")

            f.write(f"theorem exported_atom_label_nonempty_{module_name} : atom_{module_name}.label.length >= 0 := by\n")
            f.write("  -- trivial: length is always >= 0\n")
            f.write("  simp\n\n")

            f.write("end TessarisKG\n")

        logging.info(f"[LeanExportBridge] ✅ Exported {label} -> {path}")
        return path

    except Exception as e:
        logging.error(f"[LeanExportBridge] ❌ Failed to export Atom {atom_id} -> Lean: {e}")
        return ""


# ------------------------------------------------------------
# 🔁 Sync All Harmonic Atoms from KG -> Lean directory
# ------------------------------------------------------------

def export_all_atoms_to_lean(out_dir: str = LEAN_EXPORT_DIR) -> List[str]:
    """
    Iterates through all harmonic_atom nodes currently present in kg.node_registry
    and exports them as Lean files.
    """
    paths: List[str] = []
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph writer unavailable")

        registry = getattr(kg, "node_registry", {}) or {}
        for node in registry.values():
            if not isinstance(node, dict):
                continue
            if node.get("kind") != "harmonic_atom":
                continue
            atom_id = node.get("id") or node.get("label")
            if not atom_id:
                continue
            p = export_atom_to_lean(atom_id, out_dir)
            if p:
                paths.append(p)

        logging.info(f"[LeanExportBridge] Exported {len(paths)} harmonic_atoms -> Lean")
        return paths

    except Exception as e:
        logging.error(f"[LeanExportBridge] ❌ Bulk export failed: {e}")
        return []