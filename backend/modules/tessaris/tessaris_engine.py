import uuid
import json

from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.storage.tessaris_store import save_thought_snapshot
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.dna_chain.switchboard import DNA_SWITCH

DNA_SWITCH.register(__file__)  # Track + mutate via DNA Chain

class TessarisEngine:
    def __init__(self):
        self.active_branches = []
        self.active_thoughts = {}
        self.goal_engine = GoalEngine()
        self.boot_selector = BootSelector()

    def seed_thought(self, root_symbol: str, source: str = "manual", metadata: dict = {}):
        """Initialize a recursive thought tree using a root symbol."""
        thought_id = str(uuid.uuid4())
        root = BranchNode(symbol=root_symbol, source=source, metadata=metadata)
        self.active_thoughts[thought_id] = root
        return thought_id, root

    def expand_thought(self, thought_id: str, depth: int = 3):
        """Expand a thought tree to a max recursive depth."""
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
        """Trigger thought from glyph data in a cube."""
        glyphs = cube.get("glyphs", [])
        if not glyphs:
            return
        symbol = glyphs[0]  # Seed symbol
        thought_id, root = self.seed_thought(symbol, source=source)
        self.expand_thought(thought_id)
        print(f"[🧠] Thought expanded from glyph {symbol} in {source}")

    def execute_branch(self, branch: ThoughtBranch):
        """
        Execute symbolic glyph logic in sequence.
        Used for flat or compressed logic (not tree-based).
        Also detects boot/goals and logs output.
        """
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
                self._maybe_create_goal(glyph, branch)
                self._maybe_suggest_boot(glyph, branch)
            except Exception as e:
                print(f"  ⚠️ Error interpreting glyph {glyph}: {e}")

        self.active_branches.append(branch)
        return True

    def _maybe_create_goal(self, glyph: str, branch: ThoughtBranch):
        if "Goal" in glyph or glyph.startswith("⟦ Goal"):
            print(f"[Tessaris] 🔍 Goal glyph detected: {glyph}")
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
            print(f"[Tessaris] 🧠 Boot glyph detected: {glyph}")
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
        """
        Parses GlyphOS syntax like:
        ⟦ Goal | Curiosity : Explore → Boot ⟧
        Returns: {"type": "Goal", "tag": "Curiosity", "value": "Explore", "action": "Boot"}
        """
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

    def clear(self):
        """Reset both flat and recursive memory."""
        self.active_branches = []
        self.active_thoughts = {}