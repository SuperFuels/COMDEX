import time
import traceback
from backend.modules.consciousness.consciousness_manager import ConsciousnessManager

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