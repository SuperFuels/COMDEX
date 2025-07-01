from modules.aion.token_engine import TokenEngine
from modules.aion.milestone_tracker import MilestoneTracker

MODULES = {
    "memory": {"cost": 10, "milestone": "memory_access"},
    "dream_core": {"cost": 15, "milestone": "dream_core"},
    "ai_nlp": {"cost": 20, "milestone": "language_understanding"},
    "strategy_planner": {"cost": 30, "milestone": "strategy_mode"}
}

if __name__ == "__main__":
    t = TokenEngine()
    m = MilestoneTracker()

    print("🧠 Unlockable Modules:")
    for name, info in MODULES.items():
        print(f"- {name}: {info['cost']} $STK")

    module_name = input("\nWhich module do you want to unlock? Type exact name: ").strip()
    
    if module_name not in MODULES:
        print("❌ Invalid module name.")
    else:
        cost = MODULES[module_name]["cost"]
        balance = t.balance("aion")
        if balance < cost:
            print(f"❌ Not enough $STK to unlock {module_name} (needs {cost})")
        else:
            t.spend("aion", cost)
            print(f"🔓 Module Unlocked: {module_name} for {cost} $STK")

            # Unlock milestone if mapped
            milestone = MODULES[module_name].get("milestone")
            if milestone:
                m.unlock(milestone)
                print(f"✅ Milestone updated: {milestone}")
