# ============================
# 📁 codex_fabric.py
# ============================

import threading
import time
import random

from backend.modules.codex.codex_context_adapter import CodexContextAdapter
from backend.modules.codex.codex_scheduler import CodexScheduler
from backend.modules.codex.codex_supervisor import CodexSupervisor
from backend.modules.codex.codex_websocket_interface import broadcast_tick
from backend.modules.dimensions.dc_handler import (
    list_loaded_dimensions,
    load_dimension,
    run_dimension_tick
)

# 🧠 SQI Runtime: Q-routing
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore
from backend.modules.hexcore.memory_engine import MemoryEngine

# ✅ Beam persistence layer
from backend.modules.beamline import beam_store


class CodexFabric:
    """
    Simulates a multiverse of .dc CPUs with distributed CodexCore runtime.
    Orchestrates task batching, tick scheduling, and container-wise execution.
    """

    def __init__(self):
        self.dimensions = {}
        self.running = False
        self.tick_interval = 0.25  # seconds
        self.scheduler = CodexScheduler()
        self.supervisor = CodexSupervisor()
        self.adapter = CodexContextAdapter()
        self.qcores = {}  # container_id -> GlyphQuantumCore

    def discover_dimensions(self):
        """Find all loaded .dc containers that can run CodexCore"""
        all_dims = list_loaded_dimensions()
        for dim in all_dims:
            if dim.id not in self.dimensions:
                self.dimensions[dim.id] = {
                    "obj": dim,
                    "last_tick": 0,
                    "active": True
                }
                # ♾️ Initialize QGlyph quantum core for container
                self.qcores[dim.id] = GlyphQuantumCore(container_id=dim.id)

    def tick_dimension(self, dim_id):
        """Run Codex tick for a single container"""
        container = self.dimensions[dim_id]["obj"]
        try:
            self.adapter.set_context(container)

            # 🧠 Check for QGlyph execution flag
            if container.metadata.get("physics") == "symbolic-quantum":
                # ↯ Forked QGlyph execution path (symbolic quantum runtime)
                qcore = self.qcores[container.id]
                result = qcore.generate_qbit(glyph="⊕", coord="center")
                qcore.collapse_qbit(result)
                # ➕ Expand this logic in recursive runtime (future)

            # 🌀 Run normal CodexCore logic
            run_dimension_tick(container)

            # 📈 Supervisor tick
            self.supervisor.tick()

            # 📡 WebSocket: dimension tick summary
            now = time.time()
            self.dimensions[dim_id]["last_tick"] = now
            broadcast_tick({
                "type": "dimension_tick",
                "container": container.id,
                "timestamp": now
            })

        except Exception as e:
            print(f"⚠️ Error ticking container {container.id}: {e}")
            self.dimensions[dim_id]["active"] = False

    def codex_loop(self):
        """Main CodexFabric loop: iterate and process Codex ticks"""
        while self.running:
            self.discover_dimensions()
            for dim_id, meta in self.dimensions.items():
                if meta["active"]:
                    self.tick_dimension(dim_id)
            time.sleep(self.tick_interval)

    def start(self):
        if not self.running:
            print("[CodexFabric] Starting multiverse loop...")

            # ✅ Ensure persistence tables/files exist
            try:
                beam_store.ensure_tables()
                print("[CodexFabric] BeamStore tables ensured ✅")
            except Exception as e:
                print(f"[CodexFabric] ⚠️ BeamStore init failed: {e}")

            self.running = True
            threading.Thread(target=self.codex_loop, daemon=True).start()

    def stop(self):
        self.running = False
        print("[CodexFabric] Multiverse stopped.")

    def get_status(self):
        return {
            "dimensions": list(self.dimensions.keys()),
            "tick_interval": self.tick_interval,
            "running": self.running
        }


# Singleton instance
codex_fabric = CodexFabric()


# Optional direct start for debugging
if __name__ == "__main__":
    codex_fabric.start()
    while True:
        time.sleep(5)
        print("[Status]", codex_fabric.get_status())