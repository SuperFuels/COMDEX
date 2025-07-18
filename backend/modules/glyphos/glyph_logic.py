# glyph_logic.py

from typing import Any, Dict
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.goal_engine import GoalEngine
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# Optional: import MemoryBridge safely
try:
    from backend.modules.hexcore.memory_bridge import MemoryBridge
    bridge = MemoryBridge()
except ImportError:
    bridge = None

DNA_SWITCH.register(__file__)  # ✅ Track evolution of this logic

# Glyph → symbolic meaning
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

# Real modules
boot_selector = BootSelector()
reflector = ReflectionEngine()
goal_engine = GoalEngine()
planner = StrategyPlanner()


def interpret_glyph(glyph: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interprets a glyph symbol using symbolic logic + real modules.
    Returns a dict including logs, triggers, metadata, and module output.
    """
    branch = context.get("branch")
    idx = context.get("index")
    meta = context.get("metadata", {})
    position = context.get("position", 0)

    symbol = GLYPH_SYMBOL_MAP.get(glyph, "unknown")
    logs = [f"[Glyph] {glyph} interpreted as '{symbol}' (branch={branch.origin_id}, index={idx})"]
    triggered_modules = []
    memory_traces = []

    # Phase 3 stub: nested expression handling (e.g. Δ(ψ + ⚙))
    if "value" in meta and isinstance(meta["value"], str) and any(c in meta["value"] for c in GLYPH_SYMBOL_MAP):
        logs.append(f"🔁 Nested glyph expression found: {meta['value']} — [parser pending]")

    try:
        if glyph == "🧠":
            result = reflector.run(limit=5)
            store_memory({"label": "glyph_reflection", "content": result})
            logs.append("→ 🪞 Reflection triggered.")
            triggered_modules.append("ReflectionEngine")
            memory_traces.append({"type": "reflection", "content": result})

        elif glyph == "⚙":
            plan = planner.generate()
            logs.append("→ ⚙ Strategy planned.")
            triggered_modules.append("StrategyPlanner")
            memory_traces.append({"type": "plan", "content": plan})

        elif glyph == "✧":
            logs.append("→ ✧ Trigger activated.")
            triggered_modules.append("Trigger")

        elif glyph == "ψ":
            logs.append("→ 💤 Dream marker encountered.")
            triggered_modules.append("Dream")

        elif glyph == "🪄":
            logs.append("→ 🔁 Transformation logic placeholder.")
            triggered_modules.append("Transform")

        elif glyph == "Σ":
            logs.append("→ 🧾 Summarization logic.")
            triggered_modules.append("Summarizer")

        elif glyph == "☼":
            logs.append("→ ☀️ Light expansion behavior.")
            triggered_modules.append("Light")

        elif glyph == "λ":
            logs.append("→ 📜 Plan expansion initiated.")
            triggered_modules.append("Planner")

        elif glyph == "Δ":
            logs.append("→ 🚩 Intent declared.")
            triggered_modules.append("Intent")

        elif glyph == "⊕":
            logs.append("→ 🔄 Conditional logic triggered.")
            triggered_modules.append("Condition")

        elif glyph == "⇌":
            logs.append("→ 🔁 Adjustment logic.")
            triggered_modules.append("Adjust")

    except Exception as e:
        logs.append(f"⚠️ Glyph execution error: {str(e)}")
        triggered_modules.append("Error")

    # Optional MemoryBridge trace
    if bridge:
        trace = {
            "glyph": glyph,
            "symbol": symbol,
            "branch": branch.origin_id if branch else None,
            "index": idx,
            "position": position,
            "modules": triggered_modules,
        }
        bridge.trace("glyph_execution", trace)

    return {
        "glyph": glyph,
        "symbol": symbol,
        "branch": branch.origin_id if branch else None,
        "index": idx,
        "position": position,
        "log": "\n".join(logs),
        "modules": triggered_modules,
        "memory": memory_traces,
        "meta": meta,
    }