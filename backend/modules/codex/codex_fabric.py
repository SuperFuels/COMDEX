import threading
import time
import random
from backend.modules.codex.codex_context_adapter import CodexContextAdapter
from backend.modules.codex.codex_scheduler import CodexScheduler
from backend.modules.codex.codex_supervisor import CodexSupervisor
from backend.modules.dimensions.dc_handler import list_loaded_dimensions, load_dimension, run_dimension_tick

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

    def tick_dimension(self, dim_id):
        """Run Codex tick for a single container"""
        container = self.dimensions[dim_id]["obj"]
        self.supervisor.run_codex_tick(container)
        self.dimensions[dim_id]["last_tick"] = time.time()

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