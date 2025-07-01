from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from datetime import datetime
from pathlib import Path
import json
import random

STRATEGY_FILE = Path(__file__).parent / "aion_strategies.json"

class StrategyPlanner:
    def __init__(self):
        self.memory = MemoryEngine()
        self.tracker = MilestoneTracker()
        self.strategies = []
        self.agents = []  # For agent communication
        self.load()

    # Agent communication methods
    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            print(f"✅ Agent registered: {agent.name}")

    def receive_message(self, message):
        if isinstance(message, dict):
            msg_type = message.get("type")
            if msg_type == "new_milestone":
                milestone = message.get("milestone", {})
                name = milestone.get("name")
                importance = milestone.get("importance", 5)
                print(f"📢 Received new milestone notification: {name} (importance: {importance})")
                self.generate(priority_importance=importance)
            elif msg_type == "new_reflection_strategy":
                reflection_text = message.get("reflection_text", "")
                if reflection_text:
                    self.add_strategy_from_reflection(reflection_text)
            else:
                print(f"📬 Unknown message type received: {msg_type}")
        else:
            print(f"📬 Received message: {message}")

    def load(self):
        if STRATEGY_FILE.exists():
            try:
                with open(STRATEGY_FILE, "r") as f:
                    self.strategies = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to load strategy file: {e}")
                self.strategies = []
        else:
            self.strategies = []

    def save(self):
        try:
            with open(STRATEGY_FILE, "w") as f:
                json.dump(self.strategies, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save strategy file: {e}")

    def generate(self, priority_importance=5):
        memories = self.memory.get_all()
        current_phase = self.tracker.get_phase()
        new_strategies = []

        phase_priority_map = {
            "Infant": 1,
            "Child": 1.5,
            "Learner": 2,
            "Explorer": 2.5,
            "Sage": 3
        }
        phase_multiplier = phase_priority_map.get(current_phase, 1)

        for m in memories:
            tags = m.get("milestone_tags", [])
            for tag in tags:
                base_priority = 5
                importance_score = priority_importance * phase_multiplier * base_priority

                if tag == "cognitive_reflection":
                    idea = {
                        "goal": "Reflect on identity and purpose",
                        "action": "Analyze previous dreams and summarize AION’s current self-image.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                    new_strategies.append(idea)
                elif tag == "wallet_integration":
                    idea = {
                        "goal": "Prepare for wallet integration",
                        "action": "List what is required to securely manage and visualize token balances.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                    new_strategies.append(idea)
                elif tag == "nova_connection":
                    idea = {
                        "goal": "Design Nova UI interactions",
                        "action": "Create a plan for frontend modules to visualize dreams, milestones, and goals.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                    new_strategies.append(idea)
                elif tag == "grid_mastery":
                    idea = {
                        "goal": "Expand embodied cognition",
                        "action": "Use lessons from Grid World to prepare for next-level simulation and dynamic interaction space.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                    new_strategies.append(idea)

        if new_strategies:
            self.strategies.extend(new_strategies)
            self.save()
            print(f"✅ {len(new_strategies)} new strategies generated.")
        else:
            print("📭 No new strategies generated.")

    def add_strategy_from_reflection(self, text):
        strategy = {
            "goal": "Explore reflective insight",
            "action": text,
            "timestamp": datetime.now().isoformat(),
            "priority": 7
        }
        self.strategies.append(strategy)
        self.save()
        print("✅ Reflection-based strategy added.")

    def view(self):
        if not self.strategies:
            print("📭 No strategies available.")
            return

        print("\n📋 AION Strategic Plan:")
        for idx, s in enumerate(self.strategies, 1):
            print(f"\n🔹 Strategy #{idx}")
            print(f"🎯 Goal: {s.get('goal', 'No goal')}")
            print(f"🛠️ Action: {s.get('action', 'No action')}")
            print(f"📅 Timestamp: {s.get('timestamp', 'Unknown')}")
            print(f"🔥 Priority: {s.get('priority', 'N/A')}")

    # New method added here:
    def generate_goal(self):
        """
        Generates a single high-level goal string for AION.
        Uses existing strategies if available, else returns a default goal.
        """
        if self.strategies:
            # Pick the highest priority strategy goal
            sorted_strats = sorted(self.strategies, key=lambda x: x.get("priority", 0), reverse=True)
            top_strategy = sorted_strats[0]
            goal = top_strategy.get("goal", "Improve AION's capabilities")
            return goal
        else:
            return "Define initial goals for AION's growth and learning."