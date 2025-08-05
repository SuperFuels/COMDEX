from typing import Any, Dict, List
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ NEW imports for KG-driven reasoning
from backend.modules.knowledge_graph.indexes.stats_index import build_stats_index  # or correct index
from backend.modules.knowledge_graph.indexes.tag_index import get_glyphs_by_tag
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.glyphos.symbol_graph import symbol_graph  # ✅ A5b

# Attempt safe imports for optional systems
try:
    from backend.modules.hexcore.memory_engine import store_memory
except ImportError:
    store_memory = lambda *args, **kwargs: None

try:
    from backend.modules.hexcore.memory_bridge import MemoryBridge
    bridge = MemoryBridge()
except ImportError:
    bridge = None

try:
    from backend.modules.codex.ops.op_trigger import op_trigger
except ImportError:
    op_trigger = None

# ⏳ Delay imports to avoid circular dependencies
def get_goal_engine():
    from backend.modules.skills.goal_engine import GoalEngine
    return GoalEngine()

def detect_contradiction(result: str) -> bool:
    """
    Detects contradictions in glyph interpretation results.
    Looks for ⊥ (bottom), negation markers, or explicit 'contradiction' keywords.
    """
    if not result:
        return False
    result_str = str(result).lower()
    return (
        "⊥" in result_str or
        "contradiction" in result_str or
        "inconsistent" in result_str or
        "invalid state" in result_str
    )

def get_strategy_planner():
    from backend.modules.skills.strategy_planner import StrategyPlanner
    return StrategyPlanner()

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

# ✅ NEW: Dynamic operator weights (modifiable by KG evolution)
OPERATOR_WEIGHTS = {
    "↔": 1.0,  # Entanglement strength
    "⧖": 1.0,  # Collapse bias
    "⬁": 1.0,  # Mutation rate
}


def interpret_glyph(glyph: str, context: Dict[str, Any]) -> Dict[str, Any]:
    branch = context.get("branch")
    idx = context.get("index")
    meta = context.get("metadata", {})
    position = context.get("position", 0)

    symbol = GLYPH_SYMBOL_MAP.get(glyph, "unknown")
    logs = [f"[Glyph] {glyph} interpreted as '{symbol}' (branch={getattr(branch, 'origin_id', '?')}, index={idx})"]
    triggered_modules = []
    memory_traces = []

    if "value" in meta and isinstance(meta["value"], str) and any(c in meta["value"] for c in GLYPH_SYMBOL_MAP):
        logs.append(f"🔁 Nested glyph expression found: {meta['value']} — [parser pending]")

    try:
        if glyph == "🧠":
            result = reflector.run(limit=5)
            store_memory({"label": "glyph_reflection", "content": result})
            logs.append("→ 🪞 Reflection triggered.")
            triggered_modules.append("ReflectionEngine")
            memory_traces.append({"type": "reflection", "content": result})

            # ✅ Feed reflection into Symbol Graph
            symbol_graph.feed_reflection(glyph, result)

        elif glyph == "⚙":
            planner = get_strategy_planner()
            plan = planner.generate()
            store_memory({"label": "glyph_strategy_plan", "content": plan})
            logs.append("→ ⚙ Strategy planned.")
            triggered_modules.append("StrategyPlanner")
            memory_traces.append({"type": "plan", "content": plan})

        elif glyph == "✧":
            logs.append("→ ✧ Trigger activated.")
            triggered_modules.append("Trigger")
            if op_trigger:
                try:
                    target_value = meta.get("value") or context.get("target") or "default_trigger"
                    op_trigger(context=context, target=target_value)
                except Exception as trigger_error:
                    logs.append(f"⚠️ Trigger error: {trigger_error}")

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
            "branch": getattr(branch, "origin_id", None),
            "index": idx,
            "position": position,
            "modules": triggered_modules,
            "meta": meta
        }
        try:
            bridge.trace("glyph_execution", trace)
        except Exception as trace_error:
            logs.append(f"⚠️ MemoryBridge trace failed: {trace_error}")

    # ✅ Feed tags into Symbol Graph (from meta or KnowledgeIndex)
    tags = meta.get("tags") or knowledge_index.get_tags_for_glyph(glyph)
    if tags:
        symbol_graph.feed_tags(glyph, tags)

    return {
        "glyph": glyph,
        "symbol": symbol,
        "branch": getattr(branch, "origin_id", None),
        "index": idx,
        "position": position,
        "log": "\n".join(logs),
        "modules": triggered_modules,
        "memory": memory_traces,
        "meta": meta,
    }


def glyph_from_label(label: str) -> str:
    for glyph, meaning in GLYPH_SYMBOL_MAP.items():
        if meaning == label:
            return glyph
    return "?"


def analyze_branch(branch) -> List[str]:
    summaries = []
    for i, glyph in enumerate(branch.glyphs):
        context = {"branch": branch, "index": i}
        result = interpret_glyph(glyph, context)
        summaries.append(f"{i}. Glyph {glyph} → {result['symbol']}: {result['log']}")
    return summaries


def interpret_qglyph(qglyph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    results = []
    collapse_trace = []
    for i, glyph in enumerate(qglyph.get("superposition", [])):
        local_context = context.copy()
        local_context["position"] = i
        result = interpret_glyph(glyph, local_context)
        results.append(result)
        collapse_trace.append({
            "glyph": glyph,
            "index": i,
            "symbol": result.get("symbol"),
            "modules": result.get("modules"),
        })

    return {
        "type": "qglyph",
        "results": results,
        "collapse_trace": collapse_trace,
        "entangled": qglyph.get("entangled_with", []),
        "origin": qglyph.get("origin", None),
        "metadata": qglyph.get("metadata", {}),
    }

# ────────────────────────────────────────────────
# 🧠 NEW: GlyphOS Logic Evolution (A5a + A5b + A5c integrated)
# ────────────────────────────────────────────────
def update_logic_from_kg():
    """
    Dynamically evolve operator weights and reasoning rules based on Knowledge Graph,
    feed changes into the Symbol Graph, and trigger adaptive glyph synthesis.
    """
    from backend.modules.glyphos.glyph_synthesis_engine import glyph_synthesizer  # ✅ A5c link

    kgw = KnowledgeGraphWriter()
    stats = kgw.validate_knowledge_graph()

    total_glyphs = stats["total_glyphs"]
    reflection_glyphs = get_glyphs_by_tag("reflection")
    entangled_glyphs = get_glyphs_by_tag("↔")

    # Adjust operator weights based on KG metrics
    OPERATOR_WEIGHTS["↔"] = 1.0 + (len(entangled_glyphs) / max(1, total_glyphs)) * 0.5
    OPERATOR_WEIGHTS["⧖"] = 1.0 if total_glyphs < 500 else 1.2
    OPERATOR_WEIGHTS["⬁"] = 1.0 + (len(reflection_glyphs) / max(1, total_glyphs)) * 0.3

    # Inject evolution glyph into KG
    kgw.inject_glyph(
        content=f"Updated GlyphOS operator weights ↔:{OPERATOR_WEIGHTS['↔']:.2f} ⧖:{OPERATOR_WEIGHTS['⧖']:.2f} ⬁:{OPERATOR_WEIGHTS['⬁']:.2f}",
        glyph_type="self_reflection",
        metadata={"tags": ["evolution", "logic_update"], "reason": "KG-driven adaptation"},
        plugin="GlyphOS"
    )

    # ✅ Feed updated weights into Symbol Graph
    symbol_graph.feed_weights(OPERATOR_WEIGHTS)

    # ✅ A5c: Trigger adaptive glyph synthesis based on KG density & entropy
    glyph_synthesizer.adaptive_synthesis()

    return OPERATOR_WEIGHTS