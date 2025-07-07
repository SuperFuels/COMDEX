import time
from backend.modules.skills.goal_scheduler import run_all_goals

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def run_forever(interval_seconds=3600):
    while True:
        run_all_goals()
        print(f"⏰ Waiting {interval_seconds} seconds before next run...")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_forever()
