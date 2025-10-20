from pathlib import Path
from datetime import datetime
import json
from sentence_transformers import SentenceTransformer, util
from backend.modules.skills.boot_selector import BootSelector  # 🧠 Skill trigger

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 📁 File paths
MODULE_DIR = Path(__file__).resolve().parent
MILESTONE_FILE = MODULE_DIR / "aion_milestones.json"
PHASE_LOG_FILE = MODULE_DIR / "aion_phase_log.json"
PHASE_SUMMARY_FILE = MODULE_DIR / "aion_phase_summary.json"

# 🧠 Default AION growth state
DEFAULT_STATE = {
    "phase": "Infant",
    "unlocked_modules": ["memory_engine", "dream_core"],
    "locked_modules": [
        "memory_access",
        "strategy_planner",
        "vision_core",
        "voice_interface",
        "wallet_logic",
        "nova_frontend"
    ],
    "milestones": [],
    "goals": []
}

# 🌀 Phase progression order
PHASE_ORDER = ["Infant", "Child", "Learner", "Explorer", "Sage"]

# 🔓 Modules to unlock per milestone
MILESTONE_UNLOCK_MAP = {
    "first_dream": ["strategy_planner"],
    "cognitive_reflection": ["vision_core"],
    "voice_activation": ["voice_interface"],
    "wallet_integration": ["wallet_logic"],
    "nova_connection": ["nova_frontend"],
    "grid_world_complete": ["memory_access"]
}

# 🧠 Semantic triggers
TRIGGER_PATTERNS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"],
    "grid_world_complete": ["grid complete", "navigation mastery", "learned environment"]
}

from sentence_transformers import SentenceTransformer
from pathlib import Path
import os, json, logging

class MilestoneTracker:
    def __init__(self, goal_creation_callback=None):
        self.goal_creation_callback = goal_creation_callback

        # ✅ Known model search paths
        model_paths = [
            "/srv/backend/models/all-MiniLM-L6-v2",  # Docker absolute path
            str(Path(__file__).resolve().parent.parent / "models/all-MiniLM-L6-v2"),  # /backend/modules/... → /backend/models/
            "./backend/models/all-MiniLM-L6-v2",  # dev relative path
            "./models/all-MiniLM-L6-v2",          # fallback
        ]

        self.model = None
        for path in model_paths:
            if os.path.exists(path):
                try:
                    self.model = SentenceTransformer(path, local_files_only=True)
                    print(f"✅ MilestoneTracker: using MiniLM model from {path}")
                    break
                except Exception as e:
                    logging.warning(f"⚠️ Failed to load model from {path}: {e}")

        if self.model is None:
            logging.warning(f"[MilestoneTracker] ❌ Model not found in any known path: {model_paths}")

        # Continue normal initialization
        self.trigger_embeddings = self._embed_triggers() if self.model else {}
        self.boot_selector = BootSelector()

        if MILESTONE_FILE.exists():
            with open(MILESTONE_FILE, "r") as f:
                self.state = json.load(f)
        else:
            self.state = DEFAULT_STATE.copy()
            self.save()

    def _embed_triggers(self):
        return {milestone: self.model.encode(phrases) for milestone, phrases in TRIGGER_PATTERNS.items()}

    def detect_milestones_from_dream(self, text, threshold=0.75):
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 10]
        if not sentences:
            return
        sentence_embeddings = self.model.encode(sentences)
        for milestone, trigger_vecs in self.trigger_embeddings.items():
            sims = util.cos_sim(sentence_embeddings, trigger_vecs)
            max_score = sims.max().item()
            if max_score >= threshold:
                excerpt = sentences[sims.argmax(dim=0).item()]
                print(f"🧠 Milestone '{milestone}' matched with score {max_score:.2f}")
                self.add_milestone(milestone, source="dream_content", excerpt=excerpt)

    def detect_gridworld_completion(self, grid_data: dict):
        if grid_data.get("percent_complete", 0) >= 100:
            print("🏁 Grid World completed! Milestone will be recorded.")
            self.add_milestone("grid_world_complete", source="grid_world")

    def add_milestone(self, name, source="manual", excerpt=None, origin_strategy_id=None):
        if name in [m["name"] for m in self.state["milestones"]]:
            return
        milestone = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        if excerpt:
            milestone["dream_excerpt"] = excerpt.strip()[:200]
        if origin_strategy_id:
            milestone["origin_strategy_id"] = origin_strategy_id  # <-- NEW

        self.state["milestones"].append(milestone)

        self.try_unlock_modules(name)
        self.advance_phase(name)

        if self.goal_creation_callback:
            try:
                # Pass origin_strategy_id so GoalEngine can link
                self.goal_creation_callback(name, origin_strategy_id=origin_strategy_id)
                print(f"🎯 Goal created for milestone: {name} linked to strategy: {origin_strategy_id}")
            except Exception as e:
                print(f"⚠️ Goal creation callback failed for '{name}': {e}")

        try:
            skill = self.boot_selector.find_matching_skill(excerpt or name)
            if skill:
                print(f"🚀 Skill '{skill['title']}' triggered from milestone '{name}'.")
        except Exception as e:
            print(f"⚠️ Skill boot trigger failed for milestone '{name}': {e}")

        self.save()

    def try_unlock_modules(self, milestone_name):
        for module in MILESTONE_UNLOCK_MAP.get(milestone_name, []):
            if module in self.state["locked_modules"]:
                self.state["locked_modules"].remove(module)
                self.state["unlocked_modules"].append(module)

    def advance_phase(self, reason=""):
        current_index = PHASE_ORDER.index(self.state["phase"])
        if current_index + 1 < len(PHASE_ORDER):
            old = self.state["phase"]
            self.state["phase"] = PHASE_ORDER[current_index + 1]
            print(f"🌱 AION advanced to phase: {self.state['phase']}")
            self.log_phase_change(old, self.state["phase"], reason)

    def log_phase_change(self, old, new, reason):
        entry = {
            "from": old,
            "to": new,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        log = []
        if PHASE_LOG_FILE.exists():
            try:
                with open(PHASE_LOG_FILE, "r") as f:
                    log = json.load(f)
            except Exception:
                pass
        log.append(entry)
        with open(PHASE_LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

    def save(self):
        with open(MILESTONE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
        try:
            self.export_summary()
        except Exception as e:
            print(f"⚠️ Failed to write phase summary: {e}")

    def export_summary(self):
        summary = {
            "current_phase": self.state["phase"],
            "unlocked_modules": self.state["unlocked_modules"],
            "locked_modules": self.state["locked_modules"],
            "milestone_count": len(self.state["milestones"]),
            "last_updated": datetime.now().isoformat()
        }
        with open(PHASE_SUMMARY_FILE, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Phase summary exported to: {PHASE_SUMMARY_FILE}")

    def get_phase(self):
        return self.state["phase"]

    def list_unlocked_modules(self):
        return self.state.get("unlocked_modules", [])

    def list_locked_modules(self):
        return self.state.get("locked_modules", [])

    def list_milestones(self):
        return self.state.get("milestones", [])

    def list_saved_goals(self):
        return [
            m["dream_excerpt"].strip()
            for m in self.state.get("milestones", [])
            if "goal" in m.get("dream_excerpt", "").lower() or "objective" in m.get("dream_excerpt", "").lower()
        ]

    def is_unlocked(self, module_name):
        return module_name in self.state.get("unlocked_modules", [])

    def unlock(self, module_name):
        if module_name in self.state.get("locked_modules", []):
            self.state["locked_modules"].remove(module_name)
            self.state["unlocked_modules"].append(module_name)
            print(f"🔓 Manually unlocked module: {module_name}")
            self.save()
        else:
            print(f"⚠️ Module '{module_name}' not found in locked list or already unlocked.")

    def get_goal_state(self):
        return self.state.get("goals", [])

    def is_milestone_triggered(self, tags):
        """
        Check if any milestone was triggered based on provided tags.
        Returns True if any tag matches an existing milestone name.
        """
        milestone_names = [m["name"] for m in self.state.get("milestones", [])]
        return any(tag in milestone_names for tag in tags)

    def update_goal(self, index, new_name=None, new_status=None):
        try:
            if index < 0 or index >= len(self.state["goals"]):
                raise IndexError("Invalid goal index.")
            goal = self.state["goals"][index]
            if new_name:
                goal["name"] = new_name.strip()
            if new_status:
                goal["status"] = new_status
            self.save()
        except Exception as e:
            print(f"⚠️ Goal update failed: {e}")

    def reorder_goals(self, new_order):
        if isinstance(new_order, list):
            self.state["goals"] = new_order
            self.save()

    def display_growth_phase(self):
        """
        Display AION's growth phase, unlocked/locked modules, and milestone history.
        """
        print(f"\n📈 AION Growth Phase: {self.get_phase()}")
        print(f"✅ Unlocked Modules: {', '.join(self.list_unlocked_modules()) or '(none)'}")
        print(f"🔒 Locked Modules: {', '.join(self.list_locked_modules()) or '(none)'}")
        print(f"\n🗓️ Milestones:")
        
        milestones = self.list_milestones()
        if not milestones:
            print("  (none yet)")
        else:
            for i, m in enumerate(milestones, 1):
                print(f"  {i}. {m['name']} @ {m['timestamp']} (via {m.get('source', 'manual')})")

    def summary(self):
        print(f"\n📈 AION Growth Phase: {self.get_phase()}")
        print(f"✅ Unlocked Modules: {', '.join(self.list_unlocked_modules())}")
        print(f"🔒 Locked Modules: {', '.join(self.list_locked_modules())}")
        print(f"\n🗓️ Milestones:")
        milestones = self.list_milestones()
        if not milestones:
            print("  (none yet)")
        else:
            for i, m in enumerate(milestones, 1):
                print(f"  {i}. {m['name']} @ {m['timestamp']} (via {m.get('source', 'manual')})")

    async def trigger_self_rewrite(self, reason="Contradiction detected, triggering self-rewrite glyph ⮁"):
        """
        Emits the self-rewrite glyph trigger ⮁.
        This method can be called whenever a contradiction or mutation
        in the symbolic reasoning chain is detected.
        """
        from backend.modules.glyphos.glyph_executor import GlyphExecutor
        from backend.modules.consciousness.state_manager import state_manager  # ✅ shared instance

        print(f"🔄 {reason}")
        try:
            # Use shared state_manager instance
            executor = GlyphExecutor(state_manager)

            # Trigger ⮁ at origin (or update coordinates if needed)
            await executor.trigger_glyph_remotely(
                container_id=state_manager.get_current_container_id(),
                x=0, y=0, z=0,
                source="MilestoneTracker"
            )
            print("✅ Self-rewrite glyph ⮁ triggered successfully.")
        except Exception as e:
            print(f"⚠️ Failed to trigger self-rewrite glyph: {e}")