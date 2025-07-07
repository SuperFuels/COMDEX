# backend/modules/consciousness/consciousness_manager.py

from backend.modules.consciousness.time_engine import TimeEngine
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.consciousness.awareness_engine import AwarenessEngine
from backend.modules.consciousness.decision_engine import DecisionEngine
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.consciousness.energy_engine import EnergyEngine
from backend.modules.consciousness.situational_engine import SituationalEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.consciousness.planning_engine import PlanningEngine

from backend.modules.hexcore.agent_manager import AgentManager
from backend.modules.aion.sample_agent import SampleAgent

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class ConsciousnessManager:
    def __init__(self):
        self.time = TimeEngine()
        self.state = StateManager()
        self.awareness = AwarenessEngine()
        self.situation = SituationalEngine()
        self.decision = DecisionEngine(self.situation)
        self.reflector = ReflectionEngine()
        self.goal = GoalEngine()
        self.energy = EnergyEngine()
        self.personality = PersonalityProfile()
        self.planner = PlanningEngine()

        # Agent System
        self.agent_manager = AgentManager()
        self.agent_manager.register_agent("AION", SampleAgent("AION"))
        self.agent_manager.register_agent("Explorer", SampleAgent("Explorer"))

    def run_cycle(self, mode="live"):
        print("\n🌐 Starting Consciousness Cycle")

        if not self.time.can_wake():
            print("😴 AION remains asleep.")
            return "sleep"

        awareness_report = self.awareness.check_awareness()
        print(f"[AWARENESS] {awareness_report['message']} (Boot ID: {awareness_report['boot_id']})")

        self.situation.log_event("Cycle start", "neutral")
        self.situation.analyze_context()

        current_state = self.state.dump_status()
        print(f"🧠 State: {current_state}")

        context = {"mode": mode, "state": current_state}
        action = self.decision.decide(context)

        self.energy.consume(amount=1)

        if self.energy.is_critical():
            print("[WARNING] Energy low — prioritize earning funds or requesting donations!")
        if self.energy.is_dead():
            print("[FATAL] Energy depleted — AION shutting down non-essential systems.")
            return "shutdown"

        if action == "reflect on dreams":
            self.reflector.reflect()
        elif action == "plan tasks":
            self.planner.strategize()
        elif action == "prioritize goals":
            pass
        elif action == "interact with Kevin":
            print("💬 Interacting with Kevin...")
        elif action == "explore memory":
            print("🔍 Exploring memory...")
        elif action == "go back to sleep":
            self.time.go_to_sleep()
        else:
            print("🤖 AION idles.")

        self.goal.log_task("Cycle completed")
        print("✅ Consciousness cycle complete.")

        return action