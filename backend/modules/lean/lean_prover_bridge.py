# ============================================================
# 🧩 Lean ↔ Knowledge Graph Bridge
# ============================================================
"""
Bridges the auto-generated Lean proof structures (from push_to_lean)
into the Knowledge Graph system. Each Lean proof (.lean file)
is linked to its corresponding Harmonic Atom node for formal traceability
and reverse resolution (formal proof ↔ symbolic atom).
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

# ------------------------------------------------------------
# 🌐 Link Lean proof node into Knowledge Graph
# ------------------------------------------------------------
def link_lean_to_kg(atom_ref: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Links a generated Lean proof (from push_to_lean) into the Knowledge Graph.
    Creates or updates a 'lean_proof' node and links it to the harmonic_atom node.

    Args:
        atom_ref: dict - reference returned from commit_atom_to_graph or push_to_lean
        lean_path: str - path to the generated Lean file

    Returns:
        dict - metadata of the created or updated lean_proof node
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph writer unavailable")

        atom_id = atom_ref.get("ref") or atom_ref.get("id")
        if not atom_id:
            raise ValueError("Missing atom_ref.id for KG linking")

        lean_name = os.path.basename(lean_path)
        proof_node_id = f"lean::{lean_name}"

        proof_node = {
            "id": proof_node_id,
            "label": lean_name,
            "kind": "lean_proof",
            "path": lean_path,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "links": {"formalizes": atom_id},
            "domain": atom_ref.get("domain", "physics_core"),
        }

        container_id = atom_ref.get("container_id", "sci:default")

        # Inject the proof node
        kg.inject_node(container_id, proof_node)

        # Create explicit edge
        kg.inject_edge(
            source=proof_node_id,
            target=atom_id,
            relation="formalizes",
            metadata={
                "lean_path": lean_path,
                "auto_link": True,
                "created_at": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            },
        )

        # Update the harmonic atom node with backlink
        atom_update = {
            "proof_ref": lean_path,
            "formal_status": "linked",
            "linked_at": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }
        kg.update_node(atom_id, atom_update)

        logging.info(f"[LeanBridge] ✅ Linked {proof_node_id} -> {atom_id}")
        return proof_node

    except Exception as e:
        logging.error(f"[LeanBridge] ❌ Failed to link Lean proof: {e}")
        return {"error": str(e)}

# ------------------------------------------------------------
# 🔍 Reverse Lookup: Get linked Lean proof for an atom
# ------------------------------------------------------------
def get_linked_lean_for_atom(atom_id: str) -> Dict[str, Any]:
    """
    Retrieve the linked Lean proof node for a given harmonic_atom id.

    Returns:
        dict - proof node metadata or empty dict if not found
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph unavailable")

        registry = getattr(kg, "node_registry", {})
        for node in registry.values():
            if node.get("kind") == "lean_proof":
                links = node.get("links", {})
                if links.get("formalizes") == atom_id:
                    return node
        return {}

    except Exception as e:
        logging.warning(f"[LeanBridge] ⚠️ Could not fetch linked Lean proof: {e}")
        return {}

# ------------------------------------------------------------
# 🔁 Optional bulk-sync utility
# ------------------------------------------------------------
def sync_all_lean_proofs(base_dir: str = "data/lean/atoms") -> int:
    """
    Scans the Lean export directory and links all discovered .lean files
    to their corresponding harmonic_atom nodes in the Knowledge Graph.
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph unavailable")

        if not os.path.isdir(base_dir):
            logging.warning(f"[LeanBridge] ⚠️ No Lean export directory found: {base_dir}")
            return 0

        linked_count = 0
        for filename in os.listdir(base_dir):
            if not filename.endswith(".lean"):
                continue
            lean_path = os.path.join(base_dir, filename)

            # Attempt to infer atom ID from filename convention
            atom_id = filename.replace(".lean", "")
            atom_ref = {"ref": atom_id, "id": atom_id, "container_id": "sci:auto"}

            result = link_lean_to_kg(atom_ref, lean_path)
            if "error" not in result:
                linked_count += 1

        logging.info(f"[LeanBridge] 🔗 Synced {linked_count} Lean proofs into KG.")
        return linked_count

    except Exception as e:
        logging.error(f"[LeanBridge] ❌ Bulk sync failed: {e}")
        return 0