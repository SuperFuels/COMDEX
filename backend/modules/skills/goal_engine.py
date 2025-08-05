import json
from datetime import datetime
from pathlib import Path
import requests
from backend.config import GLYPH_API_BASE_URL, ENABLE_GLYPH_LOGGING
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.tessaris.tessaris_trigger import trigger_tessaris_from_goal
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.modules.glyphos.entanglement_utils import entangle_glyphs
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter, kg_writer

# ✅ Initialize Knowledge Graph Writer (no duplicate import)
kg_writer = KnowledgeGraphWriter()

# ✅ Awareness tag tracing
from backend.modules.glyphnet.glyphnet_trace import log_trace_event

GOAL_FILE = Path(__file__).parent / "goals.json"
LOG_FILE = Path(__file__).parent / "goal_skill_log.json"

DNA_SWITCH.register(__file__)

class GoalEngine:
    def __init__(self, enable_glyph_logging=ENABLE_GLYPH_LOGGING):
        self.enable_glyph_logging = enable_glyph_logging
        self.goals = []
        self.completed = []
        self.log = []
        self.agents = []
        self.load_goals()
        self.load_log()

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
                desc = milestone.get("description", f"Goal related to milestone {name}")
                print(f"📢 Received milestone notification: {name}, creating goal.")
                self.create_goal_from_milestone(name, desc)
            elif msg_type == "glyph_trigger":
                self.create_goal_from_glyph(message.get("glyph"))
            elif msg_type == "awareness_event":
                # ✅ Awareness-triggered goal
                name = message.get("name", "awareness_goal")
                desc = message.get("description", "Goal triggered by awareness trace.")
                source = message.get("source", "AwarenessEngine")
                tags = message.get("tags", [])

                print(f"🧠 Awareness-triggered goal: {name} [{tags}]")
                self.create_awareness_goal(name, desc, origin=source, tags=tags)

                # ✅ Trace it in GlyphNet
                log_trace_event(
                    event_type="goal_from_awareness",
                    data={"goal_name": name, "description": desc, "origin": source},
                    tags=["goal", "awareness"] + tags
                )
            else:
                print(f"📬 Unknown message type received: {msg_type}")
        else:
            print(f"📬 Received message: {message}")

    def load_goals(self):
        if GOAL_FILE.exists():
            try:
                with open(GOAL_FILE, "r") as f:
                    data = json.load(f)
                    self.goals = data.get("goals", [])
                    self.completed = data.get("completed", [])
            except json.JSONDecodeError:
                print("⚠️ Goal file is corrupt, resetting to empty.")
                self.goals = []
                self.completed = []
                self.save_goals()
        else:
            self.save_goals()

    def save_goals(self):
        try:
            with open(GOAL_FILE, "w") as f:
                json.dump({"goals": self.goals, "completed": self.completed}, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save goals file: {e}")

    def load_log(self):
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, "r") as f:
                    self.log = json.load(f)
            except Exception:
                self.log = []
        else:
            self.save_log()

    def save_log(self):
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(self.log, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save goal-skill log: {e}")

    def get_active_goals(self):
        active = []
        completed_set = set(self.completed)
        for g in self.goals:
            if g.get("name") in completed_set:
                continue
            dependencies = g.get("dependencies", [])
            if all(dep in completed_set for dep in dependencies):
                active.append(g)
        active.sort(key=lambda g: g.get("priority", 0), reverse=True)
        return active

    def mark_complete(self, goal_name, learned_skill=None, originating_dream_id=None, originating_strategy_id=None):
        for goal in self.goals:
            if goal.get("name") == goal_name and goal_name not in self.completed:
                self.completed.append(goal_name)
                goal["completed_at"] = datetime.now().isoformat()
                self.save_goals()
                print(f"✅ Goal marked complete: {goal_name}")

                log_entry = {
                    "goal": goal_name,
                    "learned_skill": learned_skill,
                    "dream_id": originating_dream_id,
                    "strategy_id": originating_strategy_id,
                    "timestamp": datetime.now().isoformat()
                }
                self.log.append(log_entry)
                self.save_log()
                print(f"🔍 Logged skill learning: {log_entry}")
                return goal
        print(f"⚠️ Goal not found or already completed: {goal_name}")
        return None

    def assign_goal(self, goal):
        if not self.enable_glyph_logging:
            print("🚫 Glyph injection disabled by toggle.")
            return goal

        try:
            kg_writer.inject_glyph(
                content=goal.get("description", ""),
                glyph_type="goal",
                metadata={
                    "name": goal.get("name"),
                    "reward": goal.get("reward"),
                    "priority": goal.get("priority"),
                    "origin": goal.get("origin_strategy_id") or goal.get("origin_glyph") or goal.get("origin", "system"),
                    "tags": goal.get("tags", []) + ["🎯"],
                    "created_at": goal.get("created_at")
                },
                plugin="GoalEngine"
            )
            print(f"📦 Injected goal glyph into knowledge graph: {goal.get('name')}")
        except Exception as e:
            print(f"⚠️ Failed to inject goal glyph into KG: {e}")

        existing_names = [g.get("name") for g in self.goals]
        for existing_goal in self.goals:
            if existing_goal.get("name") == goal.get("name") and existing_goal.get("description") != goal.get("description"):
                print(f"⚠️ Contradiction detected for goal '{goal.get('name')}', triggering self-rewrite ⮁ glyph.")
                try:
                    run_self_rewrite(goal.get("name"), reason="Contradictory goal assignment")
                    entangle_glyphs("⮁", f"goal_contradiction:{goal.get('name')}")
                except Exception as e:
                    print(f"⚠️ Failed to trigger self-rewrite on contradiction: {e}")
                return None
        if goal.get("name") in existing_names:
            print(f"⚠️ Goal '{goal.get('name')}' already assigned.")
            return None

        self.goals.append(goal)
        self.save_goals()
        print(f"✅ Goal assigned: {goal.get('name')}")

        try:
            trigger_tessaris_from_goal(goal)
            print(f"🧠 Tessaris logic triggered from goal: {goal.get('name')}")
        except Exception as e:
            print(f"⚠️ Tessaris trigger from goal failed: {e}")

        try:
            print("🧬 Synthesizing glyphs from goal assignment...")
            text = goal.get("description", "")
            synth_response = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": text, "source": "goal"}
            )
            if synth_response.status_code == 200:
                result = synth_response.json()
                print(f"✅ Synthesized {len(result.get('glyphs', []))} glyphs from goal.")
            else:
                print(f"⚠️ Glyph synthesis failed: {synth_response.status_code} {synth_response.text}")
        except Exception as e:
            print(f"🚨 Glyph synthesis error during goal assignment: {e}")

        return goal

    def create_goal_from_awareness(self, awareness_type: str, context: str, source: str = "AwarenessEngine"):
        """
        Create a goal triggered by an awareness trace such as 'confidence' or 'blindspot'.
        """
        name = f"awareness_goal_{awareness_type}_{datetime.now().strftime('%H%M%S')}"
        desc = f"Goal triggered by awareness state: {awareness_type.upper()} – {context}"
        tags = ["🧠", "awareness", awareness_type]

        goal = {
            "name": name,
            "description": desc,
            "reward": 4 if awareness_type == "confidence" else 6,
            "priority": 1 if awareness_type == "confidence" else 2,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "origin_strategy_id": source
        }

        # Optional: Inject into KG explicitly with awareness tag
        try:
            kg_writer.inject_glyph(
                content=desc,
                glyph_type="goal",
                metadata={
                    "name": name,
                    "awareness_type": awareness_type,
                    "context": context,
                    "origin": source,
                    "tags": tags,
                    "created_at": goal["created_at"]
                },
                plugin="AwarenessTrigger"
            )
            print(f"🧠 Injected awareness-triggered goal into KG: {name}")
        except Exception as e:
            print(f"⚠️ Awareness-trigger goal KG injection failed: {e}")

        return self.assign_goal(goal)

    def create_goal_from_milestone(self, milestone_name, description, reward=5, priority=1, dependencies=None, origin_strategy_id=None):
        if dependencies is None:
            dependencies = []
        goal = {
            "name": f"goal_for_{milestone_name}",
            "description": description,
            "reward": reward,
            "priority": priority,
            "dependencies": dependencies,
            "created_at": datetime.now().isoformat(),
            "origin_strategy_id": origin_strategy_id
        }
        return self.assign_goal(goal)

    def create_goal_from_strategy(self, goal_name, description, origin_strategy_id, reward=5, priority=1, dependencies=None):
        if dependencies is None:
            dependencies = []
        goal = {
            "name": goal_name,
            "description": description,
            "reward": reward,
            "priority": priority,
            "dependencies": dependencies,
            "created_at": datetime.now().isoformat(),
            "origin_strategy_id": origin_strategy_id
        }
        return self.assign_goal(goal)

    def create_goal_from_glyph(self, glyph, reward=3):
        name = f"glyph_goal_{glyph}"
        desc = f"Goal triggered by glyph {glyph} in Tessaris runtime."
        goal = {
            "name": name,
            "description": desc,
            "reward": reward,
            "priority": 1,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "origin_glyph": glyph
        }
        return self.assign_goal(goal)

    def create_awareness_goal(self, name, description, origin="AwarenessEngine", tags=None):
        goal = {
            "name": name,
            "description": description,
            "reward": 3,
            "priority": 2,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "origin": origin,
            "tags": tags or []
        }
        return self.assign_goal(goal)

    def log_progress(self, data):
        log_entry = {
            "type": data.get("type", "progress"),
            "event": data.get("event"),
            "message": data.get("message"),
            "success": data.get("success", True),
            "timestamp": datetime.now().isoformat()
        }
        print(f"[GOAL][LOG] {log_entry}")
        self.log.append(log_entry)
        self.save_log()

    def log_task(self, message):
        log_entry = {
            "type": "task",
            "event": "cycle_event",
            "message": message,
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        print(f"[GOAL][TASK] {log_entry}")
        self.log.append(log_entry)
        self.save_log()

GOALS = GoalEngine()

if __name__ == "__main__":
    print("🎯 Active Goals:")
    for g in GOALS.get_active_goals():
        print(f"- {g['name']} (reward: {g.get('reward', 'N/A')})")