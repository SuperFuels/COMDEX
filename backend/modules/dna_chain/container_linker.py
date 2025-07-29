from typing import Dict, Optional
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.universal_container_system.ucs_entanglement import entangle_containers
from backend.modules.soullaw.soul_law_validator import SoulLawValidator
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.websocket_manager import broadcast_glyph_event
from backend.modules.sqi.sqi_event_bus import emit_sqi_event
import time

# Bidirectional opposites for default navigation
OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}

class ContainerLinker:
    def __init__(self, container_registry: Dict[str, dict], global_address_book: Optional[Dict[str, dict]] = None):
        self.registry = container_registry  # Shared in-memory dict of containers
        self.address_book = global_address_book if global_address_book is not None else {}
        self.ucs = ucs_runtime
        self.geometry_loader = UCSGeometryLoader()
        self.kg_writer = KnowledgeGraphWriter()

    def link(self, source_id: str, target_id: str, direction: str, bidirectional: bool = True) -> bool:
        if source_id not in self.registry or target_id not in self.registry:
            return False

        # ✅ SoulLaw enforcement before linking
        SoulLawValidator.validate_container_access(self.registry[source_id])
        SoulLawValidator.validate_container_access(self.registry[target_id])

        self._ensure_nav_map(source_id)
        self.registry[source_id]["nav"][direction] = target_id

        if bidirectional and direction in OPPOSITE_DIRECTIONS:
            opp = OPPOSITE_DIRECTIONS[direction]
            self._ensure_nav_map(target_id)
            self.registry[target_id]["nav"][opp] = source_id

        # ✅ UCS save & GHX highlight
        self._sync_to_ucs(source_id)
        self._sync_to_ucs(target_id)

        # ✅ GHX Visualization: highlight link creation
        try:
            self.ucs.visualizer.highlight(source_id)
            self.ucs.visualizer.highlight(target_id)
        except Exception as e:
            print(f"⚠️ GHX highlight failed during link: {e}")

        # ✅ Emit SQI Event
        emit_sqi_event("container_link", {
            "source": source_id,
            "target": target_id,
            "direction": direction,
            "timestamp": time.time()
        })

        return True

    def unlink(self, source_id: str, direction: str, bidirectional: bool = True) -> bool:
        if source_id not in self.registry:
            return False

        target_id = self.registry[source_id].get("nav", {}).get(direction)
        if not target_id:
            return False

        self.registry[source_id]["nav"].pop(direction, None)

        if bidirectional and direction in OPPOSITE_DIRECTIONS:
            opp = OPPOSITE_DIRECTIONS[direction]
            if target_id in self.registry:
                self.registry[target_id].get("nav", {}).pop(opp, None)

        # ✅ UCS sync for both containers
        self._sync_to_ucs(source_id)
        if target_id:
            self._sync_to_ucs(target_id)

        return True

    def auto_link_from_glyph(self, source_id: str, glyph: str, coords: Optional[tuple] = None) -> Optional[str]:
        """
        Triggered when glyph like 🧽 (grow) or ↔ (entangle) is placed in the container.
        """
        if glyph == "🧽" and coords:
            x, y, z = coords
            direction = self._infer_direction(x, y, z)
            target_id = self._generate_new_container(source_id, direction)
            self.link(source_id, target_id, direction)

            # ✅ KG Indexing
            self.kg_writer.write_link_entry(source_id, target_id, direction)

            return target_id

        if glyph == "↔":
            neighbor = self._find_nearest_unlinked(source_id)
            if neighbor:
                self.link(source_id, neighbor, "out")

                # ✅ UCS entanglement registry
                entangle_containers(source_id, neighbor)

                # ✅ KG Indexing
                self.kg_writer.write_entanglement_entry(source_id, neighbor)

                return neighbor

        return None

    def _ensure_nav_map(self, cid: str):
        if "nav" not in self.registry[cid]:
            self.registry[cid]["nav"] = {}

    def _generate_new_container(self, source_id: str, direction: str) -> str:
        new_id = f"{source_id}_{direction}"
        self.registry[new_id] = {
            "id": new_id,
            "title": f"Auto-{direction.title()} of {source_id}",
            "in_memory": True,
            "tags": ["auto-linked"],
            "nav": {},
            "geometry": "linked",
        }
        self.register_container(new_id, self.registry[new_id])

        # ✅ UCS Save & Geometry Registration
        self.ucs.save_container(new_id, self.registry[new_id])
        self.geometry_loader.register_geometry(
            self.registry[new_id].get("title", new_id),
            self.registry[new_id].get("symbol", "❔"),
            self.registry[new_id].get("geometry", "linked")
        )

        # ✅ GHX Broadcast
        broadcast_glyph_event({
            "type": "container_auto_link",
            "data": {"source": source_id, "new_container": new_id, "direction": direction}
        })

        return new_id

    def _find_nearest_unlinked(self, source_id: str) -> Optional[str]:
        for cid, data in self.registry.items():
            if cid != source_id and not data.get("nav"):
                return cid
        return None

    def _infer_direction(self, x: int, y: int, z: int) -> str:
        if z > 0: return "up"
        if z < 0: return "down"
        if y > 0: return "north"
        if y < 0: return "south"
        if x > 0: return "east"
        if x < 0: return "west"
        return "out"  # fallback

    def register_container(self, cid: str, data: dict):
        if cid not in self.address_book:
            self.address_book[cid] = {
                "id": cid,
                "title": data.get("title", "Unnamed Container"),
                "glyph": data.get("glyph"),
                "region": data.get("region"),
                "connected": list(data.get("nav", {}).values()),
                "in_memory": data.get("in_memory", False),
            }

    def resolve_address(self, query: str) -> Optional[str]:
        # Simple lookup by ID or partial match
        if query in self.address_book:
            return query
        for cid, meta in self.address_book.items():
            if query.lower() in meta.get("title", "").lower():
                return cid
        return None

    def _sync_to_ucs(self, cid: str):
        """Push updated container state to UCS runtime."""
        if cid in self.registry:
            self.ucs.save_container(cid, self.registry[cid])