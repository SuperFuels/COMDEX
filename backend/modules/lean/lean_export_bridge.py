# ============================================================
# 🔁 Knowledge Graph → Lean Export Bridge
# ============================================================
"""
Allows bidirectional synchronization between the Knowledge Graph (KG)
and Lean formal files. If a Harmonic Atom node exists in the KG,
this bridge can export or update its corresponding .lean proof structure.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

LEAN_EXPORT_DIR = "data/lean/atoms_sync"

# ------------------------------------------------------------
# 🧩 Export Harmonic Atom from KG to Lean file
# ------------------------------------------------------------
def export_atom_to_lean(atom_id: str, out_dir: str = LEAN_EXPORT_DIR) -> str:
    """
    Generates or updates a .lean proof file based on a Harmonic Atom
    stored inside the Knowledge Graph.

    Args:
        atom_id (str): The ID of the harmonic_atom node in KG.
        out_dir (str): Output directory for generated Lean files.

    Returns:
        str: Path to generated .lean file.
    """
    try:
        kg = get_kg_writer()
        node = None

        # Look up atom in registry
        registry = getattr(kg, "node_registry", {})
        for n in registry.values():
            if n.get("id") == atom_id or n.get("label") == atom_id:
                node = n
                break

        if not node:
            raise ValueError(f"Harmonic Atom not found in KG: {atom_id}")

        label = node.get("label", atom_id)
        sqi = node.get("sqi", 0.0)
        timestamp = node.get("timestamp", datetime.utcnow().isoformat())
        waveform = node.get("waveform", {})

        # Ensure export directory
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{label.replace(':','_').replace('@','_')}.lean"
        path = os.path.join(out_dir, fname)

        # Write Lean structure
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"-- Auto-exported from Tessaris Knowledge Graph\n")
            f.write(f"structure HarmonicAtom where\n")
            f.write(f"  label : String := \"{label}\"\n")
            f.write(f"  sqi   : Float := {sqi}\n")
            f.write(f"  timestamp : String := \"{timestamp}\"\n")
            f.write(f"\n-- Embedded waveform metadata\n")
            f.write(f"def waveform_meta : String := '{json.dumps(waveform)[:400]}'\n")

        logging.info(f"[LeanExportBridge] ✅ Exported {label} → {path}")
        return path

    except Exception as e:
        logging.error(f"[LeanExportBridge] ❌ Failed to export Atom {atom_id} → Lean: {e}")
        return ""


# ------------------------------------------------------------
# 🔁 Sync All Harmonic Atoms from KG → Lean directory
# ------------------------------------------------------------
def export_all_atoms_to_lean(out_dir: str = LEAN_EXPORT_DIR) -> list[str]:
    """
    Iterates through all harmonic_atom nodes and exports them as Lean files.
    Returns list of exported paths.
    """
    paths = []
    try:
        kg = get_kg_writer()
        registry = getattr(kg, "node_registry", {})
        for node in registry.values():
            if node.get("kind") == "harmonic_atom":
                p = export_atom_to_lean(node["id"], out_dir)
                if p:
                    paths.append(p)
        logging.info(f"[LeanExportBridge] Exported {len(paths)} harmonic_atoms → Lean")
        return paths
    except Exception as e:
        logging.error(f"[LeanExportBridge] ❌ Bulk export failed: {e}")
        return []