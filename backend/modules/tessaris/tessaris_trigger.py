from typing import Optional, Dict, Any
from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.tessaris.tessaris_store import save_snapshot
from backend.modules.tessaris.memory_bridge import MemoryBridge
from backend.modules.dna_chain.dna_writer import propose_dna_mutation
from backend.modules.tessaris.glyph_logic import analyze_branch
from backend.modules.aion.dream_core import run_dream
from backend.modules.dna_chain.teleport import teleport_to_container

class TessarisTrigger:
    def __init__(self):
        self.engine = TessarisEngine()
        self.memory = MemoryBridge()

    def run_from_goal(self, goal_text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Convert goal text into glyph logic, execute recursively, and reflect.
        """
        label = metadata.get("label") if metadata else "goal_trigger"
        print(f"🎯 Triggering Tessaris from goal: {label}")

        root = BranchNode(symbol="🎯", value=goal_text, source="goal")
        children = root.generate_branches()
        for child in children:
            root.add_child(child)

        branch = ThoughtBranch(glyphs=[n.symbol for n in children], origin_id=label)
        result = self.engine.execute_branch(branch)
        print("🌿 Tessaris executed goal logic branch.")

        # 🔁 Reflective Feedback Loop
        insights = analyze_branch(branch)
        for insight in insights:
            summary = f"Insight from goal [{goal_text}]: {insight}"
            self.memory.write(role="observer", content=summary, tags=["tessaris", "goal", "insight"])

        # 🧬 Optional: DNA Proposal if mutation-worthy insight
        if any("mutation" in s.lower() for s in insights):
            propose_dna_mutation(
                reason=f"Symbolic insight during goal [{label}]",
                source="tessaris_trigger",
                code_context="goal execution",
                new_logic="\n".join(insights)
            )

        # 🧠 Snapshot + Memory Link
        save_snapshot(branch=branch, label=label)
        self.memory.link_to_branch(branch)

        print(f"🔁 Feedback loop complete with {len(insights)} insights.")

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

    def trigger_dream(self, reason: str = "glyph_triggered"):
        """
        Spawn a new dream reflection cycle via DreamCore.
        """
        print(f"🌀 Glyph triggered dream: {reason}")
        run_dream(trigger_reason=reason)

    def trigger_teleport(self, destination: str = "main_hub", label: str = "glyph_triggered"):
        """
        Teleport to a new container based on glyph trigger.
        """
        print(f"🪐 Glyph triggered teleport to: {destination}")
        teleport_to_container(container_id=destination, reason=label)


# Example manual triggers (for CLI/testing)
if __name__ == "__main__":
    trigger = TessarisTrigger()
    trigger.run_from_goal("Complete the lava challenge", metadata={"label": "goal_lava"})
    trigger.run_from_game_event("jump", data={"location": "lava_room"})
    trigger.trigger_dream("manual test dream")
    trigger.trigger_teleport("ocean_room", "manual teleport test")