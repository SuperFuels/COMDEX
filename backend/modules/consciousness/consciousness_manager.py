from modules.consciousness.time_engine import TimeEngine
from modules.consciousness.state_manager import StateManager
from modules.consciousness.decision_engine import DecisionEngine
from modules.consciousness.reflection_engine import ReflectionEngine
from modules.skills.goal_engine import GoalEngine
from modules.consciousness.energy_engine import EnergyEngine
from modules.consciousness.situational_engine import SituationalEngine
from modules.consciousness.personality_engine import PersonalityProfile
from modules.consciousness.planning_engine import PlanningEngine

from modules.hexcore.agent_manager import AgentManager
from modules.aion.sample_agent import SampleAgent

class ConsciousnessManager:
    def __init__(self):
        self.time = TimeEngine()
        self.state = StateManager()
        self.situation = SituationalEngine()  # ✅ Shared instance
        self.decision = DecisionEngine(self.situation)  # ✅ Injected into DecisionEngine
        self.reflector = ReflectionEngine()
        self.goal = GoalEngine()
        self.energy = EnergyEngine()
        self.personality = PersonalityProfile()
        self.planner = PlanningEngine()

        # Initialize and register agents
        self.agent_manager = AgentManager()
        self.agent_manager.register_agent("AION", SampleAgent("AION"))
        self.agent_manager.register_agent("Explorer", SampleAgent("Explorer"))

    def run_cycle(self, mode="live"):
        print("\n🌐 Starting Consciousness Cycle")

        # Wake or Sleep?
        if not self.time.can_wake():
            print("😴 AION remains asleep.")
            return "sleep"

        # Log and update situational awareness
        self.situation.log_event("Cycle start", "neutral")
        self.situation.analyze_context()

        # Evaluate current state
        current_state = self.state.dump_status()
        print(f"🧠 State: {current_state}")

        # Decision time
        context = {"mode": mode, "state": current_state}
        action = self.decision.decide(context)

        # Consume energy
        self.energy.consume(amount=1)

        # Energy warnings
        if self.energy.is_critical():
            print("[WARNING] Energy low — prioritize earning funds or requesting donations!")

        if self.energy.is_dead():
            print("[FATAL] Energy depleted — AION shutting down non-essential systems.")
            # Add shutdown logic if needed

        # Execute action
        if action == "reflect on dreams":
            self.reflector.reflect()
        elif action == "plan tasks":
            self.planner.strategize()
        elif action == "prioritize goals":
            pass  # Already handled in DecisionEngine
        elif action == "interact with Kevin":
            print("💬 Interacting with Kevin...")
        elif action == "explore memory":
            print("🔍 Exploring memory...")
        elif action == "go back to sleep":
            self.time.go_to_sleep()
        else:
            print("🤖 AION idles.")

        # Final goal and cycle log
        self.goal.log_task("Cycle completed")
        print("✅ Consciousness cycle complete.")

        return action