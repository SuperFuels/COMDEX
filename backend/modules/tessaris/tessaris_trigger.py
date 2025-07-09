# File: backend/modules/tessaris/tessaris_trigger.py

from typing import Optional, Dict, Any
from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.tessaris.tessaris_store import save_snapshot

class TessarisTrigger:
    def __init__(self):
        self.engine = TessarisEngine()

    def run_from_goal(self, goal_text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Convert goal text or metadata into glyph logic and execute it.
        """
        label = metadata.get("label") if metadata else "goal_trigger"
        print(f"🎯 Triggering Tessaris from goal: {label}")

        root = BranchNode(symbol="✧", source="goal")
        children = root.generate_branches()
        for child in children:
            root.add_child(child)

        branch = ThoughtBranch(glyphs=[n.symbol for n in children], origin_id=label)
        self.engine.execute_branch(branch)
        print("🌿 Tessaris executed goal logic branch.")

        save_snapshot(branch=branch, label=label)

    def run_from_game_event(self, event: str, data: Optional[Dict[str, Any]] = None):
        """
        Convert a game event into a glyph trigger.
        """
        label = f"game_event_{event}"
        print(f"🕹️ Triggering Tessaris from game event: {label}")

        root = BranchNode(symbol="🪄", source="game")
        children = root.generate_branches()
        for child in children:
            root.add_child(child)

        branch = ThoughtBranch(glyphs=[n.symbol for n in children], origin_id=label)
        self.engine.execute_branch(branch)
        print("🎮 Tessaris executed game event logic branch.")

        save_snapshot(branch=branch, label=label)

# Example manual triggers (for CLI/testing)
if __name__ == "__main__":
    trigger = TessarisTrigger()
    trigger.run_from_goal("Complete the lava challenge", metadata={"label": "goal_lava"})
    trigger.run_from_game_event("jump", data={"location": "lava_room"})