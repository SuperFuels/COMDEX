from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from datetime import datetime
from pathlib import Path
import json

STRATEGY_FILE = Path(__file__).parent / "aion_strategies.json"

class StrategyPlanner:
    def __init__(self):
        self.memory = MemoryEngine()
        self.tracker = MilestoneTracker()
        self.strategies = []
        self.load()

    def load(self):
        if STRATEGY_FILE.exists():
            try:
                with open(STRATEGY_FILE, "r") as f:
                    self.strategies = json.load(f)
            except:
                print("⚠️ Failed to load strategy file.")
                self.strategies = []

    def save(self):
        with open(STRATEGY_FILE, "w") as f:
            json.dump(self.strategies, f, indent=2)

    def generate(self):
        """Create a strategy based on milestone tags in memories."""
        memories = self.memory.get_all()
        new_strategies = []
        for m in memories:
            tags = m.get("milestone_tags", [])
            for tag in tags:
                if tag == "cognitive_reflection":
                    idea = {
                        "goal": "Reflect on identity and purpose",
                        "action": "Analyze previous dreams and summarize AION’s current self-image.",
                        "timestamp": datetime.now().isoformat()
                    }
                    new_strategies.append(idea)
                elif tag == "wallet_integration":
                    idea = {
                        "goal": "Prepare for wallet integration",
                        "action": "List what is required to securely manage and visualize token balances.",
                        "timestamp": datetime.now().isoformat()
                    }
                    new_strategies.append(idea)
        if new_strategies:
            self.strategies.extend(new_strategies)
            self.save()
            print(f"📘 Generated {len(new_strategies)} new strategies.")
        else:
            print("🧩 No new strategies generated.")

    def view(self):
        print("\n🎯 Current AION Strategies:")
        for i, strat in enumerate(self.strategies, 1):
            print(f"{i}. {strat['goal']} — {strat['action']} @ {strat['timestamp']}")
