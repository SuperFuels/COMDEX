# ============================================================
# 🧩 SCI -> Lean Export API
# ============================================================
"""
Manual endpoint to export all Harmonic Atoms from the Knowledge Graph
into Lean `.lean` proof files via the Lean Export Bridge.

Usage:
    curl -X POST http://localhost:8080/api/sci/export_lean_atoms
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging
from typing import Any, Dict, List

# ============================================================
#  Internal dependencies (dual-mode for bridge or manual export)
# ============================================================
try:
    # Preferred bridge path if module is available
    from backend.modules.lean.lean_export_bridge import export_all_atoms_to_lean
    _HAS_EXPORT_BRIDGE = True
except ImportError:
    _HAS_EXPORT_BRIDGE = False
    from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
    from backend.modules.lean.lean_integration import push_to_lean


router = APIRouter(prefix="/api/sci", tags=["Lean Export"])


@router.post("/export_lean_atoms")
async def export_lean_atoms(limit: int = 100, domain: str = "physics_core") -> Dict[str, Any]:
    """
    Export all Harmonic Atoms from the Knowledge Graph into Lean formalization files.
    Uses export_all_atoms_to_lean() bridge if available, otherwise manually iterates
    through Knowledge Graph nodes and calls push_to_lean().
    """
    try:
        logging.info("[SCI] 🚀 Starting Lean export from Knowledge Graph...")
        start_time = datetime.utcnow()
        exported_paths: List[str] = []

        # ─────────────────────────────────────────────
        # 1️⃣ Bridge-Based Export (preferred)
        # ─────────────────────────────────────────────
        if _HAS_EXPORT_BRIDGE:
            exported_paths = export_all_atoms_to_lean(limit=limit, domain=domain)

        # ─────────────────────────────────────────────
        # 2️⃣ Manual Export (fallback)
        # ─────────────────────────────────────────────
        else:
            kg = get_kg_writer()
            all_nodes = kg.dump_all_nodes()

            harmonic_atoms = [
                n for n in all_nodes
                if isinstance(n, dict)
                and n.get("kind") == "harmonic_atom"
                and n.get("domain") == domain
            ][:limit]

            if not harmonic_atoms:
                raise HTTPException(status_code=404, detail="No harmonic_atom nodes found in KG.")

            for atom in harmonic_atoms:
                try:
                    path = push_to_lean({
                        "ref": atom.get("id", atom.get("label", "unknown")),
                        "label": atom.get("label"),
                        "sqi": atom.get("sqi", 0.0),
                        "timestamp": atom.get(
                            "timestamp",
                            datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
                        ),
                    })
                    exported_paths.append(path)
                except Exception as e:
                    logging.warning(f"[SCI] ⚠️ Failed to export {atom.get('id')}: {e}")

        duration = (datetime.utcnow() - start_time).total_seconds()

        if not exported_paths:
            raise HTTPException(status_code=404, detail="No Lean files exported from KG.")

        logging.info(f"[SCI] ✅ Export complete - {len(exported_paths)} files in {duration:.2f}s")

        return {
            "ok": True,
            "exported_count": len(exported_paths),
            "paths": exported_paths,
            "duration_sec": duration,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[SCI] ❌ Lean export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))