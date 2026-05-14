# ============================================================
# 🧩 Lean ↔ Knowledge Graph Bridge
# File: backend/modules/lean/lean_prover_bridge.py
# ============================================================
"""
Bridges auto-generated Lean proof structures into the Knowledge Graph.
Creates/updates a lean_proof node and links it to a harmonic_atom node.

Fixes:
- Atom id ambiguity (caller may pass label/ref instead of real KG node id)
- Proof node id collisions (includes container_id + hash of abs path)
- KG API signature drift (inject_edge / update_node positional vs keyword)
"""

import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer


def _utc_ts() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _resolve_atom_node_id(kg: Any, atom_id_or_label: str) -> Optional[str]:
    """
    Best-effort resolve: if caller passes label/ref instead of real KG node id.
    Looks in kg.node_registry (if available).
    """
    if not atom_id_or_label:
        return None

    registry = getattr(kg, "node_registry", {}) or {}

    # 1) Direct match by id
    for n in registry.values():
        if n.get("id") == atom_id_or_label:
            return n.get("id")

    # 2) Match by label
    for n in registry.values():
        if n.get("label") == atom_id_or_label:
            return n.get("id")

    # 3) Match by ref (common in your stack)
    for n in registry.values():
        if n.get("ref") == atom_id_or_label:
            return n.get("id")

    return None


def _inject_edge_compat(
    kg: Any,
    *,
    container_id: str,
    source: str,
    target: str,
    relation: str,
    metadata: Dict[str, Any],
) -> None:
    """
    KG API signature drift guard:
      - some versions: inject_edge(source=, target=, relation=, metadata=)
      - others: inject_edge(container_id, source, target, relation, metadata)
    """
    try:
        kg.inject_edge(
            source=source,
            target=target,
            relation=relation,
            metadata=metadata,
        )
        return
    except TypeError:
        pass

    kg.inject_edge(container_id, source, target, relation, metadata)


def _update_node_compat(kg: Any, *, node_id: str, patch: Dict[str, Any], container_id: str) -> None:
    """
    KG API signature drift guard for update_node:
      - some versions: update_node(node_id, patch)
      - others: update_node(container_id, node_id, patch)
    """
    try:
        kg.update_node(node_id, patch)
        return
    except TypeError:
        pass

    kg.update_node(container_id, node_id, patch)


# ------------------------------------------------------------
# 🌐 Link Lean proof node into Knowledge Graph
# ------------------------------------------------------------
def link_lean_to_kg(atom_ref: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Creates/updates a lean_proof node and links it to the harmonic_atom node.

    atom_ref may contain:
      - id (kg node id) OR
      - ref / label (needs resolving via node_registry)
      - container_id / containerId
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph writer unavailable")

        if not lean_path or not isinstance(lean_path, str):
            raise ValueError("Missing lean_path")

        lean_abs = os.path.abspath(lean_path)
        if not os.path.isfile(lean_abs):
            raise FileNotFoundError(f"Lean file not found: {lean_abs}")

        atom_hint = atom_ref.get("id") or atom_ref.get("ref") or atom_ref.get("label")
        if not atom_hint:
            raise ValueError("Missing atom_ref (expected id/ref/label)")

        atom_node_id = _resolve_atom_node_id(kg, str(atom_hint)) or str(atom_hint)

        container_id = atom_ref.get("container_id") or atom_ref.get("containerId") or "sci:default"

        lean_name = os.path.basename(lean_abs)

        # avoid collisions across dirs/containers
        proof_node_id = f"lean::{container_id}::{_sha16(lean_abs)}::{lean_name}"

        proof_node = {
            "id": proof_node_id,
            "label": lean_name,
            "kind": "lean_proof",
            "path": lean_abs,
            "timestamp": _utc_ts(),
            "links": {"formalizes": atom_node_id},
            "domain": atom_ref.get("domain", "physics_core"),
            "container_id": container_id,
        }

        # Inject / upsert node
        kg.inject_node(container_id, proof_node)

        # Create explicit edge
        _inject_edge_compat(
            kg,
            container_id=container_id,
            source=proof_node_id,
            target=atom_node_id,
            relation="formalizes",
            metadata={
                "lean_path": lean_abs,
                "auto_link": True,
                "created_at": _utc_ts(),
            },
        )

        # Update the harmonic atom node with backlink
        atom_update = {
            "proof_ref": lean_abs,
            "formal_status": "linked",
            "linked_at": _utc_ts(),
        }
        _update_node_compat(kg, node_id=atom_node_id, patch=atom_update, container_id=container_id)

        logging.info(f"[LeanBridge] ✅ Linked {proof_node_id} -> {atom_node_id}")
        return proof_node

    except Exception as e:
        logging.error(f"[LeanBridge] ❌ Failed to link Lean proof: {e}")
        return {"error": str(e)}


# ------------------------------------------------------------
# 🔍 Reverse Lookup: Get linked Lean proof for an atom
# ------------------------------------------------------------
def get_linked_lean_for_atom(atom_id_or_label: str) -> Dict[str, Any]:
    """
    Return the lean_proof node that formalizes this atom (id/ref/label).
    """
    try:
        kg = get_kg_writer()
        if not kg:
            raise RuntimeError("Knowledge Graph unavailable")

        atom_node_id = _resolve_atom_node_id(kg, atom_id_or_label) or atom_id_or_label

        registry = getattr(kg, "node_registry", {}) or {}
        for node in registry.values():
            if node.get("kind") != "lean_proof":
                continue
            links = node.get("links", {}) or {}
            if links.get("formalizes") == atom_node_id:
                return node
        return {}

    except Exception as e:
        logging.warning(f"[LeanBridge] ⚠️ Could not fetch linked Lean proof: {e}")
        return {}


# ------------------------------------------------------------
# 🔁 Optional bulk-sync utility
# ------------------------------------------------------------
def sync_all_lean_proofs(
    base_dir: str = "data/lean/atoms",
    container_id: str = "sci:auto",
) -> int:
    """
    Scan base_dir for .lean files and link them into KG.
    Uses filename (minus .lean) as an atom hint (ref/id).
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
            atom_hint = filename[:-5]  # strip ".lean"

            atom_ref = {"ref": atom_hint, "id": atom_hint, "container_id": container_id}
            result = link_lean_to_kg(atom_ref, lean_path)
            if "error" not in result:
                linked_count += 1

        logging.info(f"[LeanBridge] 🔗 Synced {linked_count} Lean proofs into KG.")
        return linked_count

    except Exception as e:
        logging.error(f"[LeanBridge] ❌ Bulk sync failed: {e}")
        return 0