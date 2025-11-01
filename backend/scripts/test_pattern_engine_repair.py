# File: backend/scripts/test_pattern_engine_repair.py
"""
test_pattern_engine_repair.py
=============================

Integration test for PatternEngineRepair (F3).

Simulates:
    1. Creation of an original UCS container
    2. Entangled fork creation via EntangledRuntimeForker
    3. Observer-driven collapse resolution via ObserverPathSelector
    4. Resonance repair via PatternEngineRepair
    5. Reinjection of stabilized beam into QQC runtime

Expected:
    - Forks are detected and merged
    - Repair metadata recorded
    - Reinjected beam scheduled successfully
"""

import time
import logging
from pprint import pprint

from backend.modules.runtime.pattern_engine_repair import PatternEngineRepair
from backend.modules.runtime.entangled_runtime_forker import EntangledRuntimeForker
from backend.modules.runtime.observer_path_selector import select_path_from_superposition
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.modules.runtime.beam_scheduler import global_scheduler
from backend.modules.runtime.beam_queue import get_active_beams


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPatternRepair")


def create_mock_container(container_id: str = "test_container") -> dict:
    """Create a simple UCS container with a single cube and entanglement-ready glyph."""
    container = {
        "id": container_id,
        "type": "container",
        "cubes": {
            "A1": {"glyph": "[⚛:0 ↔ 1]"}
        },
        "metadata": {"created": time.time()},
        "coherence": 0.9,
        "entangled": False,
        "wormholes": [],
    }
    return container


def run_test_cycle():
    print("\n🔧 [Test] Initializing UCS runtime...")
    ucs = get_ucs_runtime()
    forker = EntangledRuntimeForker(ucs)
    repair_engine = PatternEngineRepair()

    # Step 1 - Create base container
    base = create_mock_container()
    ucs.register_container(base["id"], base)
    print(f"✅ Created container: {base['id']}")

    # Step 2 - Fork entangled containers
    forks = forker.fork_container(base, coord="A1", glyph="[⚛:0 ↔ 1]")
    print(f"✅ Created forks: {[f['id'] for f in forks]}")

    # Step 3 - Simulate drift
    last_txn = {"C_total": 0.6, "field_signature": {"psi": 0.12}}
    print(f"📉 Simulating SQI drift: {last_txn}")

    # Step 4 - Run repair cycle
    result = repair_engine.run_repair_cycle(last_txn)
    print(f"\n🩺 Repair cycle result:")
    pprint(result)

    # Step 5 - Inspect UCS state
    print("\n📦 UCS containers after repair:")
    pprint(list(ucs.containers.keys()))

    # Step 6 - Inspect reinjected beams
    ready = get_active_beams()
    print(f"\n💡 Reinjected Beams in Queue: {len(ready)}")
    for beam in ready:
        print(
            f"  * Beam ID: {getattr(beam, 'id', getattr(beam, 'wave_id', '?'))}, "
            f"State: {getattr(beam, 'state', getattr(beam, 'status', 'unknown'))}, "
            f"Coherence: {beam.coherence}"
        )

    print("\n✅ Test cycle complete.\n")


if __name__ == "__main__":
    print("\n🧮 Running Pattern Engine Repair Integration Test (F3)...")
    run_test_cycle()