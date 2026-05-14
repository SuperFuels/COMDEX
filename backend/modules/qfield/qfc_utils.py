# 📄 backend/modules/qfield/qfc_utils.py
import uuid
import math
import os
import json
import re
from typing import Dict, List, Any, Tuple, Optional

# Default QFC Sheet directory (can be overridden)
QFC_SHEET_DIR = os.getenv("QFC_SHEET_DIR", "backend/data/qfc_sheets")

# Allowed filename characters
VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Optional: Import the broadcaster for live updates
try:
    from backend.modules.holography.qfc_bridge import broadcast_qfc_update
except ImportError:
    broadcast_qfc_update = None  # Fallback if not available

def build_qfc_view(container: Dict[str, Any], mode: str = "live") -> Dict[str, Any]:
    """
    Build a QFC-compatible payload with nodes and links for 3D rendering.
    Automatically includes symbolic tree, entanglement, orbit layout, and prediction links.
    """
    nodes, links = build_qfc_nodes_and_links(container)
    qfc_data = {
        "type": "qfc",
        "mode": mode,
        "containerId": container.get("id"),
        "nodes": nodes,
        "links": links,
    }

    # Optional live WebSocket update
    if broadcast_qfc_update:
        broadcast_qfc_update(container.get("id"), qfc_data)

    return qfc_data

def sanitize_sheet_id(sheet_id: str) -> str:
    """
    Validates and sanitizes the sheet ID to prevent injection or traversal.
    """
    if not VALID_ID_PATTERN.match(sheet_id):
        raise ValueError(f"Invalid QFC sheet ID: '{sheet_id}'")
    return sheet_id


def get_qfc_sheet_path(sheet_id: str) -> str:
    """
    Constructs the full path to the QFC sheet file.
    """
    sanitized_id = sanitize_sheet_id(sheet_id)
    return os.path.join(QFC_SHEET_DIR, f"{sanitized_id}.sqs.json")


def load_qfc_by_id(sheet_id: str, silent: bool = False) -> Dict[str, Any]:
    """
    Loads a QFC sheet from the filesystem by ID.

    Args:
        sheet_id (str): Unique identifier for the QFC sheet (filename without extension)
        silent (bool): If True, returns {} instead of raising if not found

    Returns:
        Dict[str, Any]: The loaded QFC sheet contents
    """
    path = get_qfc_sheet_path(sheet_id)

    if not os.path.exists(path):
        if silent:
            return {}
        raise FileNotFoundError(f"QFC sheet not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Optional basic validation
        if not isinstance(data, dict) or "nodes" not in data or "links" not in data:
            raise ValueError(f"Malformed QFC sheet: {sheet_id}")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in QFC sheet {sheet_id}: {e}")

def save_qfc_sheet(sheet_id: str, data: Dict[str, Any]) -> str:
    """
    Saves a QFC sheet to disk.
    """
    sanitized_id = sanitize_sheet_id(sheet_id)
    os.makedirs(QFC_SHEET_DIR, exist_ok=True)
    path = get_qfc_sheet_path(sanitized_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path

def build_qfc_nodes_and_links(container: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate 3D visual nodes and links from container's symbolic glyphs, atoms, and predictions.
    Includes orbit-based layout, entanglement links, and teleport routes.
    """
    glyphs = list(container.get("cubes", {}).values())
    predictions = container.get("predictions", {}).get("predicted_glyphs", [])
    symbol_tree = container.get("symbolTree", {})

    nodes = []
    links = []
    seen_ids = set()

    def build_position_from_orbit(orbit: int, index: int) -> List[float]:
        radius = 5 + 3 * orbit
        angle = (2 * math.pi / 8) * index
        return [radius * math.cos(angle), radius * math.sin(angle), 0]

    def build_node(g: Dict[str, Any], i: int = 0) -> Dict[str, Any]:
        meta = g.get("metadata", {})
        node_id = g.get("id", str(uuid.uuid4()))
        orbit = meta.get("orbit")
        pos = meta.get("qfc_position")

        if not pos and orbit is not None:
            pos = build_position_from_orbit(orbit, i)

        return {
            "id": node_id,
            "label": g.get("label", "∅"),
            "type": g.get("metadata", {}).get("type", "glyph"),
            "position": pos or [0, 0, 0],
            "metadata": meta,
        }

    def build_link(source_id: str, target_id: str, link_type: str = "entangled") -> Dict[str, Any]:
        return {
            "source": source_id,
            "target": target_id,
            "type": link_type,
        }

    # 🧩 Add main glyphs
    for i, g in enumerate(glyphs):
        node = build_node(g, i)
        node_id = node["id"]
        if node_id not in seen_ids:
            nodes.append(node)
            seen_ids.add(node_id)

        # 🧬 Entangled links
        for target_id in g.get("entangled", []):
            links.append(build_link(node_id, target_id, "entangled"))

        # 🌀 Teleport links
        for t_id in g.get("teleport_links", []):
            links.append(build_link(node_id, t_id, "teleport"))

        # 🔁 Logic links
        for l_id in g.get("logic_links", []):
            links.append(build_link(node_id, l_id, "logic"))

    # 🔮 Add predicted glyphs (if any)
    for i, p in enumerate(predictions):
        node = build_node(p, i + len(glyphs))
        node["predicted"] = True
        node_id = node["id"]
        if node_id not in seen_ids:
            nodes.append(node)
            seen_ids.add(node_id)

        for target_id in p.get("entangled", []):
            links.append(build_link(node_id, target_id, "entangled"))

        for t_id in p.get("teleport_links", []):
            links.append(build_link(node_id, t_id, "teleport"))

    # 🌳 Add symbolTree structure
    def recurse_tree(node: Dict[str, Any], parent_id: str = None):
        node_id = node.get("id") or str(uuid.uuid4())
        label = node.get("label", "glyph")
        qfc_node = {
            "id": node_id,
            "label": label,
            "type": node.get("type", "glyph"),
            "metadata": node.get("metadata", {}),
            "position": node.get("position", [0, 0, 0]),
        }

        if node_id not in seen_ids:
            nodes.append(qfc_node)
            seen_ids.add(node_id)

        if parent_id:
            links.append(build_link(parent_id, node_id, "tree-link"))

        # 🧬 Entanglement in symbol tree
        for eid in node.get("entangled_ids", []):
            links.append(build_link(node_id, eid, "entangled"))

        for child in node.get("children", []):
            recurse_tree(child, node_id)

    if symbol_tree:
        recurse_tree(symbol_tree.get("root", {}))

    return nodes, links

def build_qfc_payload(node_payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a lightweight QFC payload for WebSocket streaming from a single glyph node + context.
    This is used as a fallback if no entangled wave is available.
    """
    return {
        "type": "qfc",
        "mode": "fallback",
        "containerId": context.get("container_id"),
        "nodes": [
            {
                "id": context.get("source_node", "unknown"),
                "label": node_payload.get("glyph", "∅"),
                "type": "beam_tick",
                "position": [0, 0, 0],
                "metadata": node_payload.get("metadata", {})
            }
        ],
        "links": []
    }