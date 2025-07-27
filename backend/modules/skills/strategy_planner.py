import uuid
from datetime import datetime
from pathlib import Path
import json
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.logging.failure_logger import FailureLogger
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.skills.goal_engine import GOALS
from backend.modules.skills.goal_engine import GoalEngine  # Added for goal linkage
from backend.modules.knowledge.knowledge_graph_writer import kg_writer

class StrategyPlanner:
    def __init__(self, ...):
        ...
        self.trace = CodexTrace()

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

STRATEGY_FILE = Path(__file__).parent / "aion_strategies.json"

class StrategyPlanner:
    def __init__(self, enable_glyph_logging=True):
        self.enable_glyph_logging = enable_glyph_logging  # 🔒 Toggle to enable/disable plan glyph injection
        self.memory = MemoryEngine()
        self.goal_engine = GoalEngine(enable_glyph_logging=enable_glyph_logging)  # propagate toggle
        self.tracker = MilestoneTracker(goal_creation_callback=self.goal_engine.create_goal_from_milestone)
        self.strategies = []
        self.agents = []  # For agent communication
        self.strategy_goal_map = {}  # Maps strategy_id -> goal string
        self.load()
        self.detect_and_handle_rewrites()  # 🧠 Respond to self-rewrite trigger
        self.failure_logger = FailureLogger()

    def plan_strategy(self, goal):
        strategy = {
            "uuid": str(uuid.uuid4()),
            "goal": goal.get("name"),
            "created_at": datetime.utcnow().isoformat(),
            "steps": self._generate_plan_steps(goal),
        }
        self.strategies.append(strategy)
        self.save_strategies()

        # 🚫 R4g: Check disable toggle before glyph injection
        if not self.enable_glyph_logging:
            print("🚫 Plan glyph injection disabled by toggle.")
            return strategy

        # ✅ R4e–R4h: Inject plan glyph into knowledge graph
        try:
            kg_writer.inject_glyph(
                content=str(strategy.get("steps", [])),
                glyph_type="plan",
                metadata={
                    "uuid": strategy.get("uuid"),
                    "goal": strategy.get("goal"),
                    "created_at": strategy.get("created_at"),
                    "tags": ["🧭", "🧩"],
                    "origin": "StrategyPlanner"
                },
                plugin="StrategyPlanner"
            )
            print(f"📡 Injected planning glyph into KG for goal: {strategy.get('goal')}")
        except Exception as e:
            print(f"⚠️ Failed to inject plan glyph into KG: {e}")

        return strategy

        def estimate_cost(self, text):
            """
            Estimates symbolic cost for a given strategy action using Tessaris logic.
            """
            try:
                from backend.modules.tessaris.tessaris_engine import estimate_cost as tessaris_estimate
                return tessaris_estimate(text)
            except Exception as e:
                print(f"⚠️ Could not estimate cost: {e}")
                return 0.5  # default midpoint

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
                    self.generate_with_ids(priority_importance=importance)
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
                # Ensure all strategies have IDs, add if missing
                fixed_count = 0
                for s in self.strategies:
                    if "id" not in s or not s["id"]:
                        s["id"] = str(uuid.uuid4())
                        fixed_count += 1
                if fixed_count > 0:
                    print(f"⚠️ Added missing 'id' to {fixed_count} loaded strategies.")
                    self.save()
                # Rebuild strategy_goal_map on load
                self.strategy_goal_map = {s["id"]: s.get("goal") for s in self.strategies if "id" in s}
            except Exception as e:
                print(f"⚠️ Failed to load strategy file: {e}")
                self.strategies = []
                self.strategy_goal_map = {}
        else:
            self.strategies = []
            self.strategy_goal_map = {}

    def save(self):
        try:
            with open(STRATEGY_FILE, "w") as f:
                json.dump(self.strategies, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save strategy file: {e}")

    def check_for_contradiction(self, new_strategy):
        """
        Checks if the new strategy contradicts existing strategies.
        Emits ⮁ glyph trigger if contradiction found, and triggers rewrite.
        """
        for existing in self.strategies:
            if existing.get("goal") == new_strategy.get("goal") and existing.get("action") != new_strategy.get("action"):
                print(f"⮁ Contradiction detected for goal: {new_strategy['goal']}")

                # 🧠 Log failure to KG
                self.failure_logger.log_failure(
                    "GoalConflict",
                    f"Strategy for goal '{new_strategy['goal']}' contradicts existing strategy",
                    context="StrategyPlanner"
                )

                # Emit self-rewrite glyph into memory symbolic store
                self.memory.store_symbolic({
                    "glyph": "⮁",
                    "description": f"Contradictory strategy detected for goal '{new_strategy['goal']}'.",
                    "timestamp": datetime.now().isoformat(),
                    "origin": "StrategyPlanner"
                })

                # Trigger strategy regeneration with elevated priority
                self.generate_with_ids(priority_importance=8)
                return True
        return False

    def generate(self, priority_importance=5):
        """
        Legacy generate method without IDs - kept for compatibility.
        """
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

    def generate_with_ids(self, priority_importance=5):
        """
        Generates new strategies with unique IDs and tracks them in strategy_goal_map.
        Adds deferment logic for high-cost strategies.
        """
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

                strategy_id = str(uuid.uuid4())

                if tag == "cognitive_reflection":
                    idea = {
                        "id": strategy_id,
                        "goal": "Reflect on identity and purpose",
                        "action": "Analyze previous dreams and summarize AION’s current self-image.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                elif tag == "wallet_integration":
                    idea = {
                        "id": strategy_id,
                        "goal": "Prepare for wallet integration",
                        "action": "List what is required to securely manage and visualize token balances.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                elif tag == "nova_connection":
                    idea = {
                        "id": strategy_id,
                        "goal": "Design Nova UI interactions",
                        "action": "Create a plan for frontend modules to visualize dreams, milestones, and goals.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                elif tag == "grid_mastery":
                    idea = {
                        "id": strategy_id,
                        "goal": "Expand embodied cognition",
                        "action": "Use lessons from Grid World to prepare for next-level simulation and dynamic interaction space.",
                        "timestamp": datetime.now().isoformat(),
                        "priority": importance_score
                    }
                else:
                    continue  # skip unknown tags

                # Optional: Assign estimated cost (placeholder logic)
                idea["cost"] = m.get("estimated_cost", 0.5)  # or generate with heuristic
                # ⚠️ Defer high-cost strategies
                if idea["cost"] >= 0.8:
                    idea["deferred"] = True
                    print(f"⚠️ Strategy deferred due to high cost: {idea['goal']}")
                else:
                    idea["deferred"] = False

                # Check contradiction and skip if found
                if self.check_for_contradiction(idea):
                    print("⚠️ Strategy skipped due to contradiction.")
                    continue

                new_strategies.append(idea)
                self.strategy_goal_map[strategy_id] = idea["goal"]

        if new_strategies:
            self.strategies.extend(new_strategies)
            self.save()
            print(f"✅ {len(new_strategies)} new strategies with IDs generated.")
        else:
            print("📭 No new strategies generated.")

    def add_strategy_from_reflection(self, text):
        strategy_id = str(uuid.uuid4())
        cost = self.estimate_cost(text)
        strategy = {
            "id": strategy_id,
            "goal": "Explore reflective insight",
            "action": text,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
            "priority": 10 - round(cost * 10)  # inverse priority
        }

        # Check contradiction and skip if found
        if self.check_for_contradiction(strategy):
            print("⚠️ Reflection strategy skipped due to contradiction.")
            return

        self.strategies.append(strategy)
        self.strategy_goal_map[strategy_id] = strategy["goal"]
        self.save()
        print(f"🧠 Reflection strategy added with estimated cost {cost:.2f}")
    
    def detect_and_handle_rewrites(self):
        """🌀 A3: Detect ⮁ self-rewrite glyphs and regenerate strategies."""
        recent_memory = self.memory.get_recent(limit=50)
        for m in recent_memory:
            if m.get("glyph") == "⮁":
                print("🌀 Detected ⮁ self-rewrite glyph. Generating new strategy loop...")
                self.generate_with_ids(priority_importance=7)
                break    

        def generate_goal(self):
        """
        Generates a single high-level goal string for AION.
        Uses highest priority strategy if available, else returns a default goal.
        """
        if self.strategies:
            sorted_strats = sorted(self.strategies, key=lambda x: x.get("priority", 0), reverse=True)
            top_strategy = sorted_strats[0]
            goal = top_strategy.get("goal", "Improve AION's capabilities")
            return goal
        else:
            return "Define initial goals for AION's growth and learning."
    
    def collapse_deferred_strategies(self):
        """
        Collapses all strategies marked as deferred due to high cost.
        Optionally removes them or tags with collapse metadata.
        """
        collapsed = 0
        for strategy in self.strategies:
            if strategy.get("deferred"):
                strategy["collapsed"] = True
                strategy["collapse_reason"] = "high_cost"
                collapsed += 1
                print(f"🧊 Collapsing deferred strategy: {strategy['goal']}")

        if collapsed > 0:
            self.save()
            print(f"✅ Collapsed {collapsed} high-cost strategies.")
        else:
            print("📭 No strategies collapsed.")

    def generate_fallbacks_for_collapsed(self):
        """
        For each collapsed strategy, attempt to generate a fallback strategy
        with lower priority and simpler action plan. Fallbacks are symbolically entangled (↔).
        """
        fallback_count = 0
        for strategy in self.strategies:
            if strategy.get("collapsed") and not strategy.get("fallback_generated"):
                goal = strategy.get("goal")
                fallback_action = f"Attempt minimal step toward: {goal}"
                fallback_priority = max(1, int(strategy.get("priority", 5) * 0.5))

                fallback_id = str(uuid.uuid4())
                fallback = {
                    "id": fallback_id,
                    "goal": goal,
                    "action": fallback_action,
                    "timestamp": datetime.now().isoformat(),
                    "priority": fallback_priority,
                    "fallback_for": strategy["id"],
                    "entangled_with": strategy["id"],   # ↔ link
                    "glyph": "↔"
                }

                self.strategies.append(fallback)
                strategy["fallback_generated"] = True
                fallback_count += 1
                print(f"🔁 Generated fallback for: {goal} ↔ {strategy['id']}")

                # 🧠 Log symbolic entanglement in CodexTrace and memory
                self.memory.log({
                    "type": "entanglement",
                    "glyph": "↔",
                    "from": strategy["id"],
                    "to": fallback_id,
                    "timestamp": datetime.now().isoformat(),
                    "origin": "StrategyPlanner"
                })

                # Optional: log entanglement for memory/trace
                self.memory.log({
                    "type": "entanglement",
                    "glyph": "↔",
                    "from": strategy["id"],
                    "to": fallback_id,
                    "timestamp": datetime.now().isoformat(),
                    "origin": "StrategyPlanner"
                })

        if fallback_count > 0:
            self.save()
            print(f"✅ {fallback_count} fallback strategies created.")
        else:
            print("📭 No fallbacks generated.")

    def log_collapsed_strategies_to_trace(self):
        """
        Logs all collapsed or deferred strategies to CodexTrace for replay/simulation.
        """
        for strategy in self.strategies:
            if strategy.get("collapsed") or strategy.get("deferred"):
                trace = {
                    "type": "collapse_event",
                    "source": "StrategyPlanner",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "id": strategy["id"],
                        "goal": strategy["goal"],
                        "action": strategy["action"],
                        "priority": strategy.get("priority", 5),
                        "collapsed": strategy.get("collapsed", False),
                        "deferred": strategy.get("deferred", False)
                    }
                }
                self.trace.log(trace)
                print(f"📉 Logged collapse/defer event for: {strategy['goal']}")

    def export_to_dc(self, path="exported_strategies.dc.json"):
        """
        Exports the current strategic plan into a .dc.json container format.
        Includes glyph metadata, goals, actions, and origin trace.
        """
        dc = {
            "container_id": f"strategy_{uuid.uuid4().hex[:8]}",
            "type": "strategic_plan",
            "created": datetime.now().isoformat(),
            "seed_glyphs": [],
            "glyph_trace": [],
            "metadata": {
                "origin": "StrategyPlanner",
                "strategy_count": len(self.strategies)
            }
        }

        for s in self.strategies:
            glyph = {
                "glyph": "🎯",
                "goal": s.get("goal"),
                "action": s.get("action"),
                "priority": s.get("priority", 5),
                "timestamp": s.get("timestamp"),
                "strategy_id": s.get("id"),
                "cost": s.get("cost", 0.5),
                "deferred": s.get("deferred", False)
            }

            # ✅ Add entanglement info if available
            if s.get("entangled_with"):
                glyph["entangled_with"] = s["entangled_with"]
                glyph["glyph"] = "↔"  # override to entangled glyph

            dc["seed_glyphs"].append(glyph)
            dc["glyph_trace"].append({
                "type": "strategy",
                "source": "StrategyPlanner",
                "timestamp": s.get("timestamp"),
                "data": glyph
            })

        with open(path, "w") as f:
            json.dump(dc, f, indent=2)
            print(f"✅ Exported strategy container to {path}")

    def import_from_dc(self, path):
        """
        Loads a strategy plan from a .dc.json file and injects its glyphs into the strategy list.
        Prevents duplicate IDs and preserves symbolic tags.
        Triggers ⮁ mutation if contradictions are found or origin is external.
        Forks ↔ entangled strategies if goals match but actions differ.
        """
        try:
            with open(path, "r") as f:
                dc = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load container: {e}")
            return

        if dc.get("type") != "strategic_plan":
            print("⚠️ Container is not a valid strategic_plan type.")
            return

        origin = dc.get("metadata", {}).get("origin", "unknown")
        contradiction_found = False
        forked_count = 0
        imported = 0

        for glyph in dc.get("seed_glyphs", []):
            strategy_id = glyph.get("strategy_id", str(uuid.uuid4()))
            if any(s["id"] == strategy_id for s in self.strategies):
                continue  # avoid duplicate

            new_goal = glyph.get("goal", "Undefined goal")
            new_action = glyph.get("action", "Undefined action")

            # Check for contradiction
            candidate = {
                "id": strategy_id,
                "goal": new_goal,
                "action": new_action,
                "priority": glyph.get("priority", 5),
                "timestamp": glyph.get("timestamp", datetime.now().isoformat())
            }

            if self.check_for_contradiction(candidate):
                print(f"⚠️ Contradiction in imported strategy ID {strategy_id}")
                contradiction_found = True
                continue

            # Check for ↔ entanglement (same goal, different action)
            for existing in self.strategies:
                if existing["goal"] == new_goal and existing["action"] != new_action:
                    forked_count += 1
                    self.memory.add({
                        "glyph": "↔",
                        "source": "import_from_dc",
                        "strategy_id": strategy_id,
                        "entangled_with": existing["id"],
                        "goal": new_goal,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"🔀 Forked ↔ entangled strategy for goal: {new_goal}")
                    break  # Only need one match

            self.strategies.append(candidate)
            imported += 1

        print(f"✅ Imported {imported} strategies from {path}")
        if forked_count:
            print(f"🔗 {forked_count} strategy forks created via ↔ entanglement.")

        if contradiction_found or origin != "StrategyPlanner":
            print("🌀 Triggering ⮁ self-rewrite due to mutation conditions...")
            self.memory.add({
                "glyph": "⮁",
                "source": "import_from_dc",
                "origin": origin,
                "timestamp": datetime.now().isoformat()
            })
            self.run_self_rewrite()

    def diff_with_dc(self, path):
        """
        Compares current strategies with a .dc.json container.
        Outputs a diff of new, redundant, and conflicting (↔) strategies.
        """
        try:
            with open(path, "r") as f:
                dc = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load container: {e}")
            return

        if dc.get("type") != "strategic_plan":
            print("⚠️ Container is not a valid strategic_plan type.")
            return

        current_goals = {s["goal"]: s for s in self.strategies}
        report = {
            "new": [],
            "redundant": [],
            "conflicting": []
        }

        for glyph in dc.get("seed_glyphs", []):
            goal = glyph.get("goal")
            action = glyph.get("action")
            sid = glyph.get("strategy_id", "unknown")

            if goal not in current_goals:
                report["new"].append((sid, goal, action))
            else:
                existing = current_goals[goal]
                if existing["action"] == action:
                    report["redundant"].append((sid, goal))
                else:
                    report["conflicting"].append((sid, goal, action, existing["action"]))

        print("\n🔍 Strategy Diff Report")
        print("─────────────────────────────")

        if report["new"]:
            print(f"\n🟩 New strategies ({len(report['new'])}):")
            for sid, goal, action in report["new"]:
                print(f"  [+] {goal} → {action}")
                # Check deferred status if strategy object exists
                strategy = next((s for s in self.strategies if s["id"] == sid), None)
                if strategy and strategy.get("deferred"):
                    print("     ⏳ Status: DEFERRED (High cost)")

        if report["redundant"]:
            print(f"\n🟨 Redundant strategies ({len(report['redundant'])}):")
            for sid, goal in report["redundant"]:
                print(f"  [=] {goal}")

        if report["conflicting"]:
            print(f"\n🟥 Conflicting strategies ({len(report['conflicting'])}):")
            for sid, goal, new_action, existing_action in report["conflicting"]:
                print(f"  [↔] {goal}")
                print(f"     ↳ existing: {existing_action}")
                print(f"     ↳ new:      {new_action}")

        print("\n✅ Diff complete.\n")
        return report