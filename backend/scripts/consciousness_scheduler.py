import time
import traceback
from backend.modules.consciousness.consciousness_manager import ConsciousnessManager

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def run_forever(interval_seconds=300):
    manager = ConsciousnessManager()
    print(f"🚀 Starting Consciousness Scheduler with interval {interval_seconds} seconds.")

    while True:
        try:
            action = manager.run_cycle()
            print(f"🕒 Cycle complete. Last action: {action}")
        except Exception:
            print("⚠️ Error in consciousness cycle:")
            traceback.print_exc()
        
        print(f"⏰ Sleeping for {interval_seconds} seconds...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_forever()