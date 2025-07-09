# File: backend/modules/dna_chain/trigger_engine.py

from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.state_manager import StateManager  



def check_glyph_triggers(container_id: str):
    """
    Scan a loaded .dc container and execute any known triggers based on glyph + tag.
    """
    container = load_dc_container(container_id)
    microgrid = container.get("microgrid", {})

    for coord, meta in microgrid.items():
        glyph = meta.get("glyph")
        tag = meta.get("tag")

        # Define your trigger behavior map here:
        if glyph == "✦" and tag == "dream_trigger":
            print(f"[⚡] Dream trigger found at {coord}, launching dream cycle...")
            ReflectionEngine().reflect()

        elif glyph == "🧭" and tag == "teleport":
            destination = meta.get("destination")
            if destination:
                print(f"[⚡] Teleport trigger found at {coord}, going to {destination}...")
                StateManager().teleport_to(destination)

        elif glyph == "🧠" and tag == "reflect":
            print(f"[⚡] Reflection glyph found at {coord}, triggering reflection...")
            # Placeholder for future logic
            ReflectionEngine().reflect()

        # You can add more glyph+tag behaviors here later

    print("[✅] Trigger scan complete.")