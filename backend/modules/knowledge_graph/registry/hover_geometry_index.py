# backend/modules/knowledge_graph/registry/hover_geometry_index.py

import os
import json
from typing import Dict, Optional

HOVER_GEOMETRY_PATH = "data/hover_geometry_index.json"

class HoverGeometryIndex:
    def __init__(self, path: str = HOVER_GEOMETRY_PATH):
        self.path = path
        self.index: Dict[str, dict] = {}
        self.load()

    def set_geometry_metadata(self, container_id: str, metadata: dict):
        """Store hover/collapse/overlay metadata for a container."""
        self.index[container_id] = {
            "hover_preview": metadata.get("hover_preview", ""),
            "collapsed_geometry": metadata.get("collapsed_geometry", {}),
            "entangled_links": metadata.get("entangled_links", []),
            "hologram_hint": metadata.get("hologram_hint", {}),
            "last_update": metadata.get("last_update"),
        }
        self.save()

    def get_geometry_metadata(self, container_id: str) -> Optional[dict]:
        """Fetch all hover/geometry metadata for a container."""
        return self.index.get(container_id)

    def search_by_entangled_target(self, target_id: str) -> Dict[str, dict]:
        """Find containers linked to a specific target container via entanglement."""
        results = {}
        for cid, meta in self.index.items():
            if target_id in meta.get("entangled_links", []):
                results[cid] = meta
        return results

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save hover geometry index: {e}")

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self.index = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to load hover geometry index: {e}")