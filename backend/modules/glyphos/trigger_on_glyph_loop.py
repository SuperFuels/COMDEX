# File: backend/modules/glyphos/trigger_on_glyph_loop.py

import threading
import time
from typing import Set

from backend.modules.dna_chain.dc_handler import load_dimension_by_id
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.glyphos.symbolic_hash_engine import symbolic_hash
from backend.modules.glyphos.runtime_logger import log_glyph_trace

# ✅ DNA evolution tracking
DNA_SWITCH.register(__file__)

# ✅ Glyphs that trigger runtime logic
WATCHED_GLYPHS = {"🧠", "✧", "🪄"}

# ✅ Containers under active watch
GLYPH_TRIGGER_REGISTRY: Set[str] = set()

# ✅ Runtime deduplication: hash of recent glyphs
TRIGGER_HISTORY: Set[str] = set()
MAX_HISTORY = 10000


def register_container_for_glyph_triggers(container_id: str):
    """Register a container ID to be watched for glyph triggers."""
    GLYPH_TRIGGER_REGISTRY.add(container_id)
    print(f"[🔗] Registered container for glyph trigger watch: {container_id}")


def glyph_behavior_loop(poll_interval: float = 2.0):
    """Main loop to poll containers and trigger logic on matching glyphs."""
    print("🔁 Starting Glyph Behavior Loop...")

    while True:
        for container_id in list(GLYPH_TRIGGER_REGISTRY):
            try:
                container = load_dimension_by_id(container_id)
                cubes = container.get("cubes", [])

                for cube in cubes:
                    glyphs = cube.get("glyphs", [])
                    if not glyphs:
                        continue

                    match = next((g for g in glyphs if g in WATCHED_GLYPHS), None)
                    if not match:
                        continue

                    glyph_hash = symbolic_hash(cube)
                    if glyph_hash in TRIGGER_HISTORY:
                        continue

                    print(f"🚨 Glyph trigger in {container_id}: {glyphs}")
                    TRIGGER_HISTORY.add(glyph_hash)
                    if len(TRIGGER_HISTORY) > MAX_HISTORY:
                        TRIGGER_HISTORY.pop()

                    log_glyph_trace(match, {
                        "container": container_id,
                        "glyphs": glyphs,
                        "reason": "tessaris_trigger",
                        "source": cube.get("source", "unknown"),
                        "coord": cube.get("coord", "?"),
                    })

                    TessarisEngine.process_triggered_cube(cube, source=container_id)

            except Exception as e:
                print(f"⚠️ Error checking glyphs in {container_id}: {e}")

        time.sleep(poll_interval)


def launch_glyph_trigger_thread(poll_interval: float = 2.0):
    """Start the glyph watcher in a background thread."""
    thread = threading.Thread(target=glyph_behavior_loop, args=(poll_interval,), daemon=True)
    thread.start()
    print("🚀 Glyph trigger thread launched.")