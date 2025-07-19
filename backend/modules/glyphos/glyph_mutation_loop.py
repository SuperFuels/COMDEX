# backend/modules/glyphos/glyph_mutation_loop.py

import threading
import time
import traceback
from datetime import datetime
from typing import Optional

from backend.modules.dna_chain.dc_handler import list_all_containers, get_dc_path
from backend.modules.glyphos.glyph_mutator import auto_mutate_if_expired, run_self_rewrite
from backend.modules.hexcore.memory_engine import store_memory_entry

class GlyphMutationLoop(threading.Thread):
    """
    ♻️ Background loop to process glyph mutations over time:
      - Auto-decay rewrite (via decay_limit_ms)
      - Self-rewriting logic (⬁ glyphs)
    """
    def __init__(self, tick_interval_sec: float = 5.0, container_filter: Optional[list] = None):
        super().__init__()
        self.tick_interval = tick_interval_sec
        self.running = False
        self.container_filter = container_filter  # If set, restrict to specific container IDs

    def run(self):
        self.running = True
        print("[♻️] GlyphMutationLoop started.")

        while self.running:
            try:
                container_ids = self.container_filter or list_all_containers()
                now_ms = int(datetime.utcnow().timestamp() * 1000)

                for cid in container_ids:
                    path = get_dc_path(cid)
                    container = self._load_container(path)
                    if not container:
                        continue

                    for coord, cube in container.get("cubes", {}).items():
                        mutated = False

                        # Decay-based auto-rewrite
                        if auto_mutate_if_expired(path, coord, now_ms=now_ms):
                            mutated = True

                        # Self-rewriting trigger (⬁)
                        if run_self_rewrite(path, coord):
                            mutated = True

                        if mutated:
                            store_memory_entry("glyph_autorewrite", {
                                "container": cid,
                                "coord": coord,
                                "timestamp": datetime.utcnow().isoformat()
                            })

                time.sleep(self.tick_interval)

            except Exception as e:
                print(f"[⚠️] GlyphMutationLoop error: {e}\n{traceback.format_exc()}")
                time.sleep(self.tick_interval * 2)

    def stop(self):
        print("[🛑] Stopping GlyphMutationLoop...")
        self.running = False

    def _load_container(self, path):
        try:
            from backend.modules.dna_chain.dc_handler import load_dc_container
            return load_dc_container(path)
        except Exception as e:
            print(f"[⚠️] Failed to load container {path}: {e}")
            return None