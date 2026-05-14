# File: test_mutation_and_dream.py

import os
import sys
import asyncio

# Set path if running outside package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# ✅ DNA Switch registration
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# Core imports
from backend.modules.aion.dream_core import DreamCore
from backend.modules.hexcore.memory_engine import MEMORY, store_container_metadata

# Test container path
CONTAINER_PATH = "backend/modules/dimensions/containers/test_mutation.dc.json"
from backend.modules.consciousness.state_manager import state_manager

def main():
    print(f"🧪 Loading container from: {CONTAINER_PATH}")
    container = state_manager.load_container_from_file(CONTAINER_PATH)

    print("🧠 Storing container metadata in memory...")
    store_container_metadata(container)  # ✅ correct usage

    print("💤 Triggering dream cycle from container state...")
    dream_core = DreamCore()
    dream = asyncio.run(dream_core.run_dream_cycle())

    print("\n🌌 DREAM OUTPUT:")
    print("=" * 40)
    print(dream)
    print("=" * 40)

if __name__ == "__main__":
    main()