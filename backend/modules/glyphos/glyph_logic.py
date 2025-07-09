# File: backend/modules/glyphos/glyph_logic.py

from typing import Any, Dict
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.goal_engine import GoalEngine
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH

DNA_SWITCH.register(__file__)  # Enable glyph mutation + evolution tracking

# Basic symbolic mappings (extendable)
GLYPH_SYMBOL_MAP = {
    "Δ": "intent",
    "⊕": "condition",
    "λ": "plan",
    "⇌": "adjust",
    "Σ": "summarize",
    "☼": "light",
    "ψ": "dream",
    "✧": "trigger",
    "🧠": "reflect",
    "🪄": "transform",
    "⚙": "boot",
}

# Optional internal modules
boot_selector = BootSelector()
reflector = ReflectionEngine()
goal_engine = GoalEngine()
planner = StrategyPlanner()


def interpret_glyph(glyph: str, context: Dict[str, Any]) -> str:
    """
    Translate and execute a glyph symbol within a given context.
    Triggers symbolic logic and optionally real AION modules.
    """
    branch = context.get("branch")
    idx = context.get("index")
    meta = context.get("metadata", {})
    position = context.get("position", 0)

    symbol = GLYPH_SYMBOL_MAP.get(glyph, "unknown")
    log = f"[Glyph] {glyph} interpreted as '{symbol}' (in branch {branch.origin_id} at index {idx})"

    # Trigger real behaviors (v1 symbolic only)
    try:
        if glyph == "🧠":
            result = reflector.run(limit=5)
            store_memory({"label": "glyph_reflection", "content": result})
            log += " → 🪞 Reflected"
        elif glyph == "⚙":
            plan = planner.generate()
            log += f" → ⚙ Planned"
        elif glyph == "✧":
            log += " → ✧ Trigger evaluated"
        elif glyph == "ψ":
            log += " → 💤 Dream marker"
        elif glyph == "🪄":
            log += " → 🔁 Transform hint"
        elif glyph == "Σ":
            log += " → 🧾 Summarized logic"
        elif glyph == "☼":
            log += " → ☀️ Light expansion"
        elif glyph == "λ":
            log += " → 📜 Plan expansion"
        elif glyph == "Δ":
            log += " → 🚩 Intent declared"
        elif glyph == "⊕":
            log += " → 🔄 Conditional logic"
        elif glyph == "⇌":
            log += " → 🔁 Adjustment triggered"
    except Exception as e:
        log += f" ⚠️ Glyph execution error: {e}"

    return log