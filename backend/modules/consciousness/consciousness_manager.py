from backend.modules.consciousness.time_engine import TimeEngine
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.consciousness.decision_engine import DecisionEngine
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.goal_engine import GoalEngine
from backend.modules.consciousness.energy_engine import EnergyEngine
from backend.modules.consciousness.situational_engine import SituationalEngine
from backend.modules.consciousness.personality_profile import PersonalityProfile
from backend.modules.consciousness.planning_engine import PlanningEngine

from backend.modules.hexcore.agent_manager import AgentManager  # ✅ NEW: Hook into HexCore

class ConsciousnessManager:
    def __init__(self):
        self.time = TimeEngine()
        self.state = StateManager()
        self.decision = DecisionEngine()
        self.reflector = ReflectionEngine()
        self.goal = GoalEngine()
        self.energy = EnergyEngine()
        self.situation = SituationalEngine()
        self.personality = PersonalityProfile()
        self.planner = PlanningEngine()
        self.agent = AgentManager()  # ✅ Initialize HexCore agent logic

    def run_cycle(self, mode="live"):
        print("\n🌐 Starting Consciousness Cycle")

        # Wake or Sleep?
        if not self.time.can_wake():
            print("😴 AION remains asleep.")
            return "sleep"

        # Update situational context
        self.situation.log_event("Cycle start", "neutral")
        self.situation.analyze_context()

        # Evaluate current state
        current_state = self.state.report_state()
        print(f"🧠 State: {current_state}")

        # Decision time
        context = {"mode": mode, "state": current_state}
        action = self.decision.simulate_decision_tree(context)

        # Execute decision path
        if action == "reflect":
            self.reflector.reflect()
        elif action == "plan":
            self.planner.strategize()
        elif action == "act":
            print("🚀 Executing action via HexCore...")
            self.agent.perform_action()  # ✅ Hook to actual action logic
        elif action == "sleep":
            self.time.sleep()
        else:
            print("🤖 AION idles.")

        # Update internal metrics
        self.energy.consume()
        self.goal.log_task("Cycle completed")
        print("✅ Consciousness cycle complete.")

        return action
