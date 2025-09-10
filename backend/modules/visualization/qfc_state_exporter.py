# File: backend/modules/visualization/qfc_state_exporter.py

import os
import json
from typing import Dict, Any
from backend.modules.dimensions.containers.container_loader import load_container_by_id
from backend.modules.runtime.ucs_runtime import save_container
from backend.modules.visualization.qfc_payload_utils import build_qfc_state_from_container

def save_qfc_state_to_container(container_id: str, qfc_state: Dict[str, Any]) -> bool:
    """
    Saves the QFC beam/glyph state into the symbolic container under `symbolic.qfc_state`.
    
    Args:
        container_id: ID of the container to update.
        qfc_state: Full QFC payload (beams, glyphs, overlays, etc.)
    
    Returns:
        True if the container was updated and saved successfully.
    """
    container = load_container_by_id(container_id)
    if not container:
        print(f"[QFC Export] ❌ Container '{container_id}' not found.")
        return False

    container.setdefault("symbolic", {})["qfc_state"] = qfc_state

    try:
        save_container(container_id, container)
        print(f"[QFC Export] ✅ Saved QFC state to container: {container_id}")
        return True
    except Exception as e:
        print(f"[QFC Export] ❌ Failed to save container {container_id}: {e}")
        return False

def export_current_qfc_state(container_id: str) -> bool:
    """
    Helper function that builds the current QFC state and writes it to the container.
    """
    try:
        qfc_payload = build_qfc_state_from_container(container_id)
        return save_qfc_state_to_container(container_id, qfc_payload)
    except Exception as err:
        print(f"[QFC Export] ⚠️ Error during export: {err}")
        return False
