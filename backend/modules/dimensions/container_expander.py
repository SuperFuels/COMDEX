"""
Container Expander: Initializes and grows .dc containers
Uses DimensionKernel to seed runtime cube space and prepare for Avatar spawn.
Now integrated with:
    • UCS Runtime & Geometry Sync
    • SoulLaw Enforcement
    • Knowledge Graph Indexing
    • GHX Visualization Hooks
    • SQI Pi Wave Event Emission
    • Entanglement-Aware Growth
"""

from .dimension_kernel import DimensionKernel
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCSGeometryLoader
from backend.modules.dimensions.ucs.ucs_entanglement import entangle_containers
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.dna_chain.container_index_writer import add_to_index
from backend.modules.websocket_manager import broadcast_event as broadcast_glyph_event
from backend.modules.sqi.sqi_event_bus import emit_sqi_event
import time

class ContainerExpander:
    def __init__(self, container_id):
        self.kernel = DimensionKernel(container_id)
        self.container_id = container_id
        self.geometry_loader = UCSGeometryLoader()
        self.ucs = ucs_runtime
        self.kg_writer = KnowledgeGraphWriter()

        # ✅ Auto-register container in UCS
        container = self.kernel.get_container()
        self.ucs.save_container(container_id, container)

    def seed_initial_space(self, size=3, geometry="Tesseract"):
        """
        Seeds a base NxNxN runtime space and registers geometry.
        """
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    self.kernel.register_cube(x, y, z, 0)

        # ✅ UCS Geometry Registration
        container = self.kernel.get_container()
        self.geometry_loader.register_geometry(
            container.get("name", self.container_id),
            container.get("symbol", "❔"),
            geometry
        )

        # ✅ Save updated container state in UCS
        self.ucs.save_container(self.container_id, container)

        # ✅ Emit GHX Visualization highlight
        try:
            self.ucs.visualizer.highlight(self.container_id)
        except Exception as e:
            print(f"⚠️ GHX highlight failed during seed: {e}")

        return f"🌱 Seeded initial {size}x{size}x{size} runtime space."

    def grow_space(self, direction="z", layers=1):
        """
        Expands container runtime along a given axis and syncs UCS.
        """
        result = self.kernel.expand(axis=direction, amount=layers)
        container = self.kernel.get_container()

        # ✅ UCS Save
        self.ucs.save_container(self.container_id, container)

        # ✅ GHX Visualization Sync
        try:
            self.ucs.visualizer.highlight(self.container_id)
        except Exception as e:
            print(f"⚠️ GHX visualization sync failed: {e}")

        # ✅ Entanglement-Aware Growth
        entangled = container.get("entangled", [])
        for eid in entangled:
            try:
                entangle_containers(self.container_id, eid)
                print(f"↔ Propagated growth to entangled container: {eid}")
            except Exception as e:
                print(f"⚠️ Failed to propagate entanglement growth: {e}")

        # ✅ Emit SQI Event
        emit_sqi_event("container_growth", {
            "container_id": self.container_id,
            "direction": direction,
            "layers": layers,
            "timestamp": time.time()
        })

        return result

    def inject_glyph(self, x, y, z, t, glyph):
        """
        Injects glyph into container space with SoulLaw enforcement, KG indexing,
        UCS sync, and GHX broadcast.
        """
        # ✅ SoulLaw Validation
        verdict = SoulLawValidator.evaluate_glyph(glyph)
        self.ucs.soul_law.validate_access(self.kernel.get_container())
        if verdict != "approved":
            raise PermissionError(f"❌ SoulLaw denied glyph injection: {glyph} (verdict: {verdict})")

        # ✅ Inject glyph
        self.kernel.add_glyph(x, y, z, t, glyph)

        container = self.kernel.get_container()

        # ✅ Knowledge Graph & Index Sync
        entry = {
            "id": f"glyph_{int(time.time())}",
            "type": "glyph",
            "content": glyph,
            "timestamp": time.time(),
            "metadata": {"tags": ["glyph_injection"], "coord": f"{x},{y},{z}"}
        }
        add_to_index("glyph_index", entry)
        self.kg_writer.write_glyph_entry(entry)

        # ✅ UCS Save & GHX Sync
        self.ucs.save_container(self.container_id, container)
        try:
            broadcast_glyph_event({
                "type": "glyph_injection",
                "data": {
                    "coord": f"{x},{y},{z}",
                    "glyph": glyph,
                    "container_id": self.container_id,
                    "timestamp": time.time()
                }
            })
        except Exception as e:
            print(f"⚠️ WebSocket broadcast failed: {e}")

        # ✅ Emit SQI Event
        emit_sqi_event("glyph_injection", {
            "container_id": self.container_id,
            "glyph": glyph,
            "coord": f"{x},{y},{z}",
            "timestamp": time.time()
        })

        return f"✨ Glyph '{glyph}' injected at ({x},{y},{z})"

    def status(self):
        """
        Dumps container snapshot for monitoring/debugging.
        """
        snapshot = self.kernel.dump_snapshot()
        print(f"📦 Container Snapshot: {self.container_id}")
        return snapshot