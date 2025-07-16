# backend/modules/glyphos/glyph_executor.py

from backend.modules.glyphos.glyph_parser import parse_glyph
from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.dna_switch import register_dna_switch
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.personality.personality_engine import PersonalityProfile
from backend.modules.skills.milestone_tracker import MilestoneTracker


class GlyphExecutor:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.dispatcher = GlyphDispatcher(state_manager)
        self.active_container = self.state_manager.get_current_container()
        self.goal_engine = GoalEngine()
        self.memory_engine = MemoryEngine()
        self.personality = PersonalityProfile()
        self.milestone_tracker = MilestoneTracker()

    def read_glyph_at(self, x: int, y: int, z: int) -> str:
        """
        Reads the glyph value at a given 3D coordinate in the active container.
        """
        cube = self.active_container.get("cubes", {}).get(f"{x},{y},{z}", {})
        return cube.get("glyph", "")

    def execute_glyph_at(self, x: int, y: int, z: int):
        """
        Execute glyph logic at specified coordinate.
        This handles known glyph behaviors and dispatches to registered modules.
        """
        coord = f"{x},{y},{z}"
        glyph = self.read_glyph_at(x, y, z)
        if not glyph:
            print(f"⚠️ No glyph found at {coord}")
            return

        parsed = parse_glyph(glyph)
        print(f"🔍 Parsed glyph at {coord}: {parsed}")

        # Dispatch to module logic
        self.dispatcher.dispatch(parsed)

        # Get current simulation tick
        current_tick = self.state_manager.get_tick()

        # Specific glyph behaviors
        if glyph == "🧠":
            self.goal_engine.boot_next_skill()
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "action": "boot_next_skill",
                "coord": coord,
                "tick": current_tick,
                "trait_impact": {"curiosity": +0.02},
            })
            self.personality.adjust_trait("curiosity", +0.02)

        elif glyph == "⚙":
            self.goal_engine.run_top_goal()
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "action": "run_top_goal",
                "coord": coord,
                "tick": current_tick,
                "trait_impact": {"ambition": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.01)

        elif glyph == "🔬":
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "action": "curiosity_spark",
                "coord": coord,
                "tick": current_tick,
                "trait_impact": {"curiosity": +0.03, "humility": +0.01},
            })
            self.personality.adjust_trait("curiosity", +0.03)
            self.personality.adjust_trait("humility", +0.01)

        elif glyph == "🎯":
            goal_id = self.goal_engine.create_goal("Reflect on surroundings from glyph 🎯", priority=7)
            self.milestone_tracker.check_milestones()
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "action": "created_goal",
                "coord": coord,
                "tick": current_tick,
                "goal_id": goal_id,
                "trait_impact": {"ambition": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.01)

        elif glyph == "🌟":
            self.milestone_tracker.mark_manual_milestone("glyph_star_trigger")
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "action": "milestone_unlocked",
                "coord": coord,
                "tick": current_tick,
                "milestone": "glyph_star_trigger",
                "trait_impact": {"ambition": +0.02, "curiosity": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.02)
            self.personality.adjust_trait("curiosity", +0.01)

        else:
            self.memory_engine.store({
                "type": "glyph_trigger",
                "glyph": glyph,
                "coord": coord,
                "tick": current_tick,
                "action": "executed_generic_glyph"
            })


register_dna_switch(__file__)