import os
import json
from datetime import datetime, timezone
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.hexcore.memory_engine import MemoryEngine

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

planner = StrategyPlanner()
memory = MemoryEngine()

STRATEGY_FILE = "backend/modules/skills/aion_strategies.json"
ACTION_LOG_FILE = "backend/modules/skills/action_log.json"

def load_strategies():
    if not os.path.exists(STRATEGY_FILE):
        return []
    with open(STRATEGY_FILE, "r") as f:
        return json.load(f)

def simulate_action(action):
    print(f"🛠 Executing simulated action: {action}")
    memory.store({
        "label": f"executed_{action[:20].replace(' ', '_')}",
        "source": "strategy_executor",
        "type": "simulated_action",
        "content": f"Simulated execution of: {action}"
    })

def log_action(goal, action):
    log = []
    if os.path.exists(ACTION_LOG_FILE):
        with open(ACTION_LOG_FILE, "r") as f:
            log = json.load(f)
    log.append({
        "goal": goal,
        "action": action,
        "executed_at": datetime.now(timezone.utc).isoformat()
    })
    with open(ACTION_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def run_strategy_execution():
    print("🧠 Loading strategy plan...")
    strategies = load_strategies()

    if not strategies:
        print("❌ No strategies to execute.")
        return

    for strategy in strategies:
        goal = strategy.get("goal") or strategy.get("title", "Unnamed Goal")
        action = strategy.get("action") or strategy.get("description", "No Action")

        if not goal or not action:
            print(f"⚠️ Skipping invalid strategy: {strategy}")
            continue

        try:
            simulate_action(action)
            log_action(goal, action)
            print(f"✅ Executed strategy for goal: {goal}")
        except Exception as e:
            print(f"⚠️ Failed to execute strategy '{goal}': {e}")

if __name__ == "__main__":
    run_strategy_execution()