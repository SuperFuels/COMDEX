# backend/modules/tessaris/tessaris_engine.py

import uuid
import json
import requests
import time

from config import GLYPH_API_BASE_URL
from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.storage.tessaris_store import save_thought_snapshot
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.tessaris.tessaris_intent_executor import queue_tessaris_intent
from backend.modules.memory.memory_bridge import MemoryBridge
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.modules.glyphos.glyph_generator import GlyphGenerator

# 🔁 Codex integration
from backend.modules.codex.codex_mind_model import CodexMindModel
from backend.modules.codex.codex_metrics import CodexMetrics

DNA_SWITCH.register(__file__)

class TessarisEngine:
    def __init__(self):
        self.active_branches = []
        self.active_thoughts = {}
        self.goal_engine = GoalEngine()
        self.boot_selector = BootSelector()
        self.memlog = MemoryBridge()
        self.glyph_generator = GlyphGenerator()

        # 🧠 Codex integration
        self.codex_mind = CodexMindModel()
        self.codex_metrics = CodexMetrics()

    def seed_thought(self, root_symbol: str, source: str = "manual", metadata: dict = {}):
        thought_id = str(uuid.uuid4())
        root = BranchNode(symbol=root_symbol, source=source, metadata=metadata)
        self.active_thoughts[thought_id] = root
        return thought_id, root

    def expand_thought(self, thought_id: str, depth: int = 3):
        root = self.active_thoughts.get(thought_id)
        if not root:
            raise ValueError("Thought not found")
        self._expand_branch(root, depth)
        save_thought_snapshot(thought_id, root)
        return root

    def _expand_branch(self, node: BranchNode, depth: int):
        if depth <= 0:
            return
        children = node.generate_branches()
        for child in children:
            node.add_child(child)
            self._expand_branch(child, depth - 1)

    def process_triggered_cube(self, cube: dict, source: str = "unknown"):
        glyphs = cube.get("glyphs", [])
        if not glyphs:
            return
        symbol = glyphs[0]
        thought_id, root = self.seed_thought(symbol, source=source)
        self.expand_thought(thought_id)
        print(f"[🧠] Thought expanded from glyph {symbol} in {source}")

    def execute_branch(self, branch: ThoughtBranch):
        print(f"🧠 Executing ThoughtBranch from {branch.origin_id} ({len(branch.glyphs)} glyphs)")

        MEMORY.store({
            "label": f"tessaris_exec_{branch.origin_id}",
            "role": "tessaris",
            "type": "thought_branch",
            "content": f"Glyph logic executed from origin {branch.origin_id}",
            "data": {
                "glyphs": branch.glyphs,
                "metadata": branch.metadata,
                "position": branch.position
            }
        })

        for idx, glyph in enumerate(branch.glyphs):
            try:
                result = interpret_glyph(glyph, context={
                    "branch": branch,
                    "position": branch.position,
                    "index": idx,
                    "metadata": branch.metadata
                })
                print(f"  ➤ Glyph {idx}: {glyph} → {result}")

                # 🔁 Codex tracking
                self.codex_mind.observe(glyph)
                self.codex_metrics.record_execution()

                coord = branch.position.get("coord")
                container_path = branch.metadata.get("container_path") if branch.metadata else None

                if glyph.strip().startswith("⟦ Write") or glyph.strip().startswith("⟦ Mutate"):
                    if coord and container_path:
                        success = run_self_rewrite(container_path, coord)
                        if success:
                            print(f"♻️ Self-rewriting glyph executed at {coord}")
                        else:
                            print(f"⚠️ Rewrite skipped at {coord}")

                if "⟲" in glyph and "Reflect" in result:
                    MEMORY.store({
                        "label": "tessaris_reflection",
                        "role": "tessaris",
                        "type": "self_reflection",
                        "content": f"Reflected on glyph {glyph}",
                        "data": {"glyph": glyph}
                    })
                    print(f"🔁 Reflection triggered from ⟲ glyph")

                self._maybe_create_goal(glyph, branch)
                self._maybe_suggest_boot(glyph, branch)

            except Exception as e:
                print(f"  ⚠️ Error interpreting glyph {glyph}: {e}")
                self.codex_metrics.record_error()

        self.extract_intents_from_glyphs(branch.glyphs, branch.metadata)
        self.active_branches.append(branch)

        # 🔁 Synthesis hook
        try:
            synth_payload = {
                "glyphs": branch.glyphs,
                "metadata": branch.metadata,
                "source": "tessaris_engine",
                "origin_id": branch.origin_id
            }
            response = requests.post(f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs", json=synth_payload)
            if response.ok:
                print(f"[✨] Synthesized glyphs: {response.json()}")
            else:
                print(f"[⚠️] Synthesis failed with status {response.status_code}")
        except Exception as e:
            print(f"[❌] Glyph synthesis error: {e}")

        # 🧬 Glyph regeneration
        try:
            generated = self.glyph_generator.generate_from_text(
                input_text=" ".join(branch.glyphs),
                context="tessaris"
            )
            print(f"[🧬] Glyphs re-generated from executed branch: {generated}")
        except Exception as e:
            print(f"[❌] Glyph generation error: {e}")

        return True

    def _maybe_create_goal(self, glyph: str, branch: ThoughtBranch):
        if "Goal" in glyph or glyph.startswith("⟦ Goal"):
            parsed = self._parse_glyph(glyph)
            if parsed:
                title = parsed.get("tag", "Unnamed Goal")
                desc = parsed.get("value", "Generated from glyph.")
                goal = self.goal_engine.create_goal_from_glyph(title, desc)
                print(f"[🎯] New goal proposed: {goal.get('name')}")
                MEMORY.store({
                    "label": "tessaris_goal_created",
                    "role": "tessaris",
                    "type": "goal_created",
                    "content": f"Goal '{goal.get('name')}' from glyph: {glyph}",
                    "data": goal
                })

    def _maybe_suggest_boot(self, glyph: str, branch: ThoughtBranch):
        if "Boot" in glyph or glyph.startswith("⟦ Skill") or glyph.startswith("⟦ Boot"):
            skill = self.boot_selector.find_matching_skill(glyph)
            if skill:
                print(f"[🚀] Matching boot skill found: {skill['title']}")
                MEMORY.store({
                    "label": "tessaris_boot_proposal",
                    "role": "tessaris",
                    "type": "boot_skill",
                    "content": f"Proposed boot skill: {skill['title']} from glyph: {glyph}",
                    "data": skill
                })
            else:
                print("😕 No matching boot skill found.")

    def _parse_glyph(self, glyph: str) -> dict:
        try:
            inner = glyph.strip("⟦⟧").strip()
            parts = inner.split("→")
            left = parts[0].strip()
            action = parts[1].strip() if len(parts) > 1 else "Reflect"
            type_tag, value = left.split(":", 1)
            g_type, tag = type_tag.split("|", 1)
            return {
                "type": g_type.strip(),
                "tag": tag.strip(),
                "value": value.strip(),
                "action": action
            }
        except Exception as e:
            print(f"[⚠️] Glyph parse failed: {e}")
            return None

    def extract_intents_from_glyphs(self, glyphs, metadata=None):
        for glyph in glyphs:
            parsed = self._parse_glyph(glyph)
            if not parsed:
                continue

            intent_type = None
            payload = {}

            if parsed["type"] == "Goal":
                intent_type = "goal"
                payload = {
                    "name": parsed.get("tag"),
                    "description": parsed.get("value"),
                }
            elif parsed["type"] == "Skill" or parsed["type"] == "Boot":
                intent_type = "avatar_action"
                payload = {
                    "skill": parsed.get("value"),
                    "reason": parsed.get("tag"),
                }
            elif parsed["type"] == "Plan":
                intent_type = "plan"
                payload = {
                    "steps": [parsed.get("value")],
                    "topic": parsed.get("tag"),
                }

            if intent_type:
                intent_data = {
                    "type": intent_type,
                    "data": payload,
                    "source": "tessaris_engine",
                    "glyph": glyph,
                    "metadata": metadata or {},
                }
                queue_tessaris_intent(intent_data)
                self.memlog.log({
                    "source": "tessaris_engine",
                    "event": "intent_queued",
                    "intent_type": intent_type,
                    "glyph": glyph,
                    "payload": payload,
                    "metadata": metadata or {},
                })
                print(f"🧠 Queued Tessaris intent ({intent_type}): {payload}")

    def clear(self):
        self.active_branches = []
        self.active_thoughts = []