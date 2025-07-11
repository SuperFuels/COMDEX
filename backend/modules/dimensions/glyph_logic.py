"""
Glyph Logic Processor for Tessaris Runtime
Evaluates symbolic glyphs from .dc containers.
"""

from modules.tessaris.thought_branch import execute_branch_from_glyph
from modules.skills.strategy_planner import generate_strategy
from modules.memory.memory_engine import MemoryEngine

def process_glyph_logic(glyph, avatar=None):
    """
    Evaluate and act on the glyph logic at the avatar’s current location.
    """

    if glyph.startswith("⟦"):
        try:
            action = None
            if "→" in glyph:
                _, action = glyph.split("→", 1)
                action = action.strip()

            if action.startswith("THINK"):
                thought = action.replace("THINK:", "").strip()
                return execute_branch_from_glyph(thought)

            elif action.startswith("GOAL"):
                goal = action.replace("GOAL:", "").strip()
                MemoryEngine.store(f"Triggered goal: {goal}", role="glyph")
                return f"Goal proposed: {goal}"

            elif action.startswith("STRATEGY"):
                plan = generate_strategy(action.replace("STRATEGY:", "").strip())
                return f"Strategy: {plan}"

            elif action.startswith("TELEPORT"):
                dest = action.replace("TELEPORT:", "").strip()
                if avatar:
                    avatar.teleport(dest)
                    return f"Teleported to {dest}"

            elif action.startswith("EMOTE"):
                emotion = action.replace("EMOTE:", "").strip()
                avatar.inject_emotion(emotion)
                return f"Emotion activated: {emotion}"

            return f"No known action triggered: {action}"

        except Exception as e:
            return f"⚠️ Error processing glyph: {str(e)}"
    else:
        return "⚪ Non-symbolic data — no action taken."
