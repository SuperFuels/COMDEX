# ============================
# 📁 codex_fabric.py
# ============================

import threading
import time

from backend.modules.codex.codex_context_adapter import CodexContextAdapter
from backend.modules.codex.codex_scheduler import CodexScheduler
from backend.modules.codex.codex_supervisor import CodexSupervisor
from backend.modules.codex.codex_websocket_interface import broadcast_tick
from backend.modules.runtime.container_runtime import get_container_runtime

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
        self.runtime = get_container_runtime()

    def discover_dimensions(self):
        """Discover all loaded containers via UCS/state manager."""
        try:
            container_ids = list(self.runtime.state_manager.all_containers.keys())
        except Exception:
            container_ids = []

        for cid in container_ids:
            if cid not in self.dimensions:
                self.dimensions[cid] = {
                    "obj": {"id": cid, "metadata": {}},
                    "last_tick": 0,
                    "active": True
                }
                # ♾️ Initialize QGlyph quantum core for container
                self.qcores[cid] = GlyphQuantumCore(container_id=cid)

    def tick_dimension(self, dim_id):
        """Run Codex tick for a single container using ContainerRuntime"""
        try:
            # 🧠 Check symbolic runtime flag
            meta = self.dimensions[dim_id]["obj"].get("metadata", {})
            if meta.get("physics") == "symbolic-quantum":
                qcore = self.qcores[dim_id]
                qb = qcore.generate_qbit(glyph="⊕", coord="center")
                qcore.collapse_qbit(qb)

            # 🌀 Execute one full runtime tick
            self.runtime.load_and_activate_container(dim_id)
            tick_log = self.runtime.run_tick()

            # 📈 Supervisor tick
            self.supervisor.tick()

            # 📡 WebSocket: dimension tick summary
            now = time.time()
            self.dimensions[dim_id]["last_tick"] = now
            broadcast_tick({
                "type": "dimension_tick",
                "container": dim_id,
                "timestamp": now,
                "executed": tick_log.get("executed", [])
            })

        except Exception as e:
            print(f"⚠️ Error ticking container {dim_id}: {e}")
            self.dimensions[dim_id]["active"] = False

    def codex_loop(self):
        """Main CodexFabric loop: iterate and process Codex ticks"""
        while self.running:
            self.discover_dimensions()
            for dim_id, meta in list(self.dimensions.items()):
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

    def get_current_container(self):
        """
        Returns the currently active symbolic container for Lean sync.
        """
        try:
            if hasattr(self, "current_container"):
                return self.current_container
            return {"id": "fabric_stub_container", "symbolic_logic": []}
        except Exception as e:
            print(f"[CodexFabric] ⚠️ get_current_container() failed: {e}")
            return {"error": str(e)}


# Singleton instance
codex_fabric = CodexFabric()


# Optional direct start for debugging
if __name__ == "__main__":
    codex_fabric.start()
    while True:
        time.sleep(5)
        print("[Status]", codex_fabric.get_status())