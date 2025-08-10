"""
Glyph Logic Processor for Tessaris Runtime
Evaluates symbolic glyphs from .dc containers.
"""

from backend.modules.tessaris.thought_branch import execute_branch_from_glyph
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.hexcore.memory_engine import MEMORY

def process_glyph_logic(glyph, avatar=None):
    """
    Evaluate and act on the glyph logic at the avatar’s current location.
    """
    if not isinstance(glyph, str):
        return "⚪ Non-symbolic data — no action taken."

    if glyph.startswith("⟦"):
        try:
            action = None
            if "→" in glyph:
                _, action = glyph.split("→", 1)
                action = action.strip()
            else:
                return "⚪ No action marker found."

            if action.startswith("THINK"):
                thought = action.replace("THINK:", "").strip()
                return execute_branch_from_glyph(thought)

            elif action.startswith("GOAL"):
                goal = action.replace("GOAL:", "").strip()
                # Use MEMORY (not MemoryEngine)
                MEMORY.store({
                    "role": "glyph",
                    "label": "goal_trigger",
                    "content": f"Triggered goal: {goal}",
                })
                return f"Goal proposed: {goal}"

            elif action.startswith("STRATEGY"):
                goal_text = action.replace("STRATEGY:", "").strip()
                planner = StrategyPlanner()
                # Support both planner.generate(...) and planner.plan_strategy({...})
                if hasattr(planner, "generate"):
                    plan = planner.generate(goal_text)
                else:
                    plan = planner.plan_strategy({"name": goal_text})
                return f"Strategy: {plan}"

            elif action.startswith("TELEPORT"):
                dest = action.replace("TELEPORT:", "").strip()
                if avatar and hasattr(avatar, "teleport"):
                    avatar.teleport(dest)
                    return f"Teleported to {dest}"
                return "⚠️ Avatar missing or cannot teleport."

            elif action.startswith("EMOTE"):
                emotion = action.replace("EMOTE:", "").strip()
                if avatar and hasattr(avatar, "inject_emotion"):
                    avatar.inject_emotion(emotion)
                    return f"Emotion activated: {emotion}"
                return "⚠️ Avatar missing or cannot emote."

            return f"No known action triggered: {action}"

        except Exception as e:
            return f"⚠️ Error processing glyph: {str(e)}"
    else:
        return "⚪ Non-symbolic data — no action taken."


# ─────────────────────────────────────────────────────────────────────────────
# Added: Entanglement resolution for UCS + .dc containers
# Keeps API expected by container_api: get_entangled_links_for_universal_container_system
# ─────────────────────────────────────────────────────────────────────────────

# Try UCS runtime first (in-memory containers)
try:
    from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
except Exception:
    ucs_runtime = None

# Fallback to .dc handler (disk-backed containers)
try:
    from backend.modules.dna_chain.dc_handler import get_entangled_links as _dc_get_entangled_links
except Exception:
    _dc_get_entangled_links = None


def get_entangled_links_for_universal_container_system(container_id_or_name: str):
    """
    Resolve 'entangled' links for a container in the Universal Container System.
    Order of resolution:
      1) UCS runtime (in-memory) -> container['entangled'] or ['entangled_with']
      2) .dc handler fallback -> dc_handler.get_entangled_links(container_id)
    Returns a list (possibly empty) of linked container IDs/names.
    """

    # 1) UCS runtime path
    if ucs_runtime:
        # Try direct name match
        c = ucs_runtime.get_container(container_id_or_name)
        if c:
            links = c.get("entangled") or c.get("entangled_with") or []
            if isinstance(links, list):
                return links
            if isinstance(links, dict):
                return list(links.keys())

        # If not found by name, scan for matching id
        for _name, _c in getattr(ucs_runtime, "containers", {}).items():
            if _c.get("id") == container_id_or_name:
                links = _c.get("entangled") or _c.get("entangled_with") or []
                if isinstance(links, list):
                    return links
                if isinstance(links, dict):
                    return list(links.keys())
                break

    # 2) .dc handler fallback
    if _dc_get_entangled_links:
        try:
            return _dc_get_entangled_links(container_id_or_name) or []
        except Exception:
            pass

    # Default: nothing linked
    return []


# Optional: make it visible to 'from ... import ...'
try:
    __all__.append("get_entangled_links_for_universal_container_system")
except Exception:
    __all__ = ["get_entangled_links_for_universal_container_system"]