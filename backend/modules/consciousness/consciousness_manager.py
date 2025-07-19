import os
import json
import threading

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

from backend.modules.dna_chain.dc_handler import (
    load_dimension,
    list_containers_with_memory_status,
    load_dimension_by_id,
)

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ✅ MemoryEngine logging
from backend.modules.hexcore.memory_engine import MEMORY

# ✅ Glyph trigger loop
from backend.modules.glyphos.glyph_trigger_engine import glyph_behavior_loop

# ✅ Trigger system
from backend.modules.dna_chain.trigger_engine import check_glyph_triggers
from backend.modules.glyphos.trigger_on_glyph_loop import register_container_for_glyph_triggers

# ✅ Bytecode glyph scanner
from backend.modules.glyphos.glyph_watcher import GlyphWatcher

# ✅ Tessaris Runtime
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.tessaris.thought_branch import ThoughtBranch

# ✅ Tessaris Store
from backend.modules.tessaris.tessaris_store import TESSARIS_STORE

DEFAULT_CONTAINER_ID = "default_container"

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

        # Glyph loop control flag
        self.glyph_loop_started = False

        # Glyph watcher module (B2)
        self.glyph_watcher = GlyphWatcher()

        # Tessaris Runtime (F2)
        self.tessaris = TessarisEngine()

        # 🔁 Boot default container into memory at startup
        self.boot_default_container()

    def boot_default_container(self):
        default_id = "aion_start"
        print(f"[🧠] Booting default container: {default_id}")
        container = load_dimension_by_id(default_id)
        if container:
            self.state.set_current_container(container)
        else:
            print("[⚠️] Failed to load default container.")

    def run_cycle(self, mode="live"):
        print("\n🌐 Starting Consciousness Cycle")

        # ✅ Start glyph behavior loop once
        if not self.glyph_loop_started:
            threading.Thread(target=glyph_behavior_loop, daemon=True).start()
            self.glyph_loop_started = True
            print("🔁 Glyph trigger loop started.")

        if not self.time.can_wake():
            print("😴 AION remains asleep.")
            return "sleep"

        # 🔁 Load primary container or fallback if missing
        try:
            start_container = load_dimension("aion_start")
        except Exception as e:
            print(f"[⚠️] Failed to load 'aion_start': {e}")
            print("[⛑️] Attempting to load fallback container...")
            try:
                start_container = load_dimension(DEFAULT_CONTAINER_ID)
            except Exception as fallback_error:
                print(f"[❌] Failed to load fallback container: {fallback_error}")
                print("[🚨] Critical error – no valid container loaded.")
                return "boot_failed"

        # ✅ Log the loaded container
        container_id = start_container.get("id", "unknown")

        # ✅ Register for glyph-based triggers
        register_container_for_glyph_triggers(container_id)

        self.situation.log_container_entry(container_id)

        # ✅ MemoryEngine log: container state
        MEMORY.store({
            "label": "container_load",
            "role": "system",
            "type": "container_loaded",
            "content": f"📦 Entered container: {container_id}",
            "data": start_container
        })

        # 🔌 Update state + describe loaded container
        self.state.set_current_container(start_container)

        # ✅ Run bytecode glyph watcher on this container (B2)
        self.glyph_watcher.watch_container(start_container)

        # 🔍 Check for glyph triggers in this container
        check_glyph_triggers(container_id)

        print(f"\n🧭 {start_container.get('welcome_message', 'Welcome.')}")
        print(f"📜 Rules: {', '.join(start_container.get('rules', []))}")
        print(f"🎯 Current Goals: {start_container.get('current_goals', [])}")
        print(f"🧠 Dreams: {start_container.get('dreams', [])}")
        print(f"🗺️ Available Containers: {start_container.get('available_containers', [])}")
        print(f"🚪 Navigation Methods: {start_container.get('navigation', {}).get('methods', [])}")
        self.state.update_context("location", container_id)

        # ✅ Pull full list of containers w/ memory status & store in state
        containers = list_containers_with_memory_status()
        self.state.context["available_containers"] = containers
        print("\n📦 All Available Containers:")
        for c in containers:
            mem_flag = "🧠" if c["in_memory"] else "📁"
            print(f"  {mem_flag} {c['id']}")

        # Awareness, situational analysis
        awareness_report = self.awareness.check_awareness()
        print(f"[AWARENESS] {awareness_report['message']} (Boot ID: {awareness_report['boot_id']})")

        self.situation.log_event("Cycle start", "neutral")
        self.situation.analyze_context()

        current_state = self.state.dump_status()
        print(f"🧠 State: {json.dumps(current_state, indent=2)}")

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

        # ✅ Tessaris trigger from goal
        active_goals = self.goal.get_active_goals()
        for g in active_goals:
            if "glyph_sequence" in g:
                print(f"🧬 Executing glyph logic from goal: {g['name']}")
                tb = ThoughtBranch(
                    glyphs=g["glyph_sequence"],
                    origin_id=g.get("origin_strategy_id", "unknown"),
                    position={"source": "goal_engine"},
                    metadata={"goal_name": g["name"]}
                )
                self.tessaris.execute_branch(tb)
                TESSARIS_STORE.save_branch(tb)

        self.goal.log_task("Cycle completed")
        print("✅ Consciousness cycle complete.")

        return action