
from typing import Optional
from typing import Any, Dict, List, Union, Tuple
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
        "↔": "entangle",
        "⧖": "collapse",
        "🧭": "guide",     # bias next-step lemma selection   
    }

# Real modules
boot_selector = BootSelector()
reflector = ReflectionEngine()

# ✅ NEW: Dynamic operator weights (modifiable by KG evolution)
OPERATOR_WEIGHTS = {
    "↔": 1.0,  # Entanglement strength
    "⧖": 1.0,  # Collapse bias
    "⬁": 1.0,  # Mutation rate
    "🧭": 1.0, # Guidance strength (lemma selection bias)
}


def interpret_glyph(glyph: str, context: Dict[str, Any]) -> Dict[str, Any]:
    branch = context.get("branch")
    idx = context.get("index")
    meta = context.get("metadata", {})
    position = context.get("position", 0)

    symbol = GLYPH_SYMBOL_MAP.get(glyph, "unknown")
    logs = [f"[Glyph] {glyph} interpreted as '{symbol}' (branch={getattr(branch, 'origin_id', '?')}, index={idx})"]
    triggered_modules: List[str] = []
    memory_traces: List[Dict[str, Any]] = []

    if "value" in meta and isinstance(meta["value"], str) and any(c in meta["value"] for c in GLYPH_SYMBOL_MAP):
        logs.append(f"🔁 Nested glyph expression found: {meta['value']} — [parser pending]")

    try:
        if glyph == "🧠":
            result = reflector.run(limit=5)
            store_memory({"label": "glyph_reflection", "content": result})
            logs.append("→ 🪞 Reflection triggered.")
            triggered_modules.append("ReflectionEngine")
            memory_traces.append({"type": "reflection", "content": result})
            # Feed reflection into Symbol Graph
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

        elif glyph == "↔":
            # Entangle: unify/equate expressions
            strength = OPERATOR_WEIGHTS.get("↔", 1.0)
            logs.append(f"→ 🔗 Entangle: unified expressions (strength={strength:.2f}).")
            triggered_modules.append("Entangle")
            meta.setdefault("hints", {})["prefer_equivalence"] = True
            try:
                if hasattr(symbol_graph, "entangle"):
                    symbol_graph.entangle(context.get("payload", None))
            except Exception:
                pass

        elif glyph == "⧖":
            # Collapse: resolve a constraint / prune a branch
            bias = OPERATOR_WEIGHTS.get("⧖", 1.0)
            logs.append(f"→ ⧖ Collapse: constraint resolved (bias={bias:.2f}).")
            triggered_modules.append("Collapse")
            meta.setdefault("hints", {})["constraint_resolved"] = True

        elif glyph == "🧭":
            # Guide: bias next-step lemma selection
            weight = OPERATOR_WEIGHTS.get("🧭", 1.0)
            logs.append(f"→ 🧭 Guide: lemma selection biased (weight={weight:.2f}).")
            triggered_modules.append("Guide")
            meta.setdefault("hints", {})["lemma_bias"] = {
                "weight": weight,
                "strategy": "prefer_short_lemmas"
            }
            try:
                planner = get_strategy_planner()
                if hasattr(planner, "nudge"):
                    planner.nudge({"lemma_bias": weight})
            except Exception:
                pass

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

    # ✅ Optional operator score delta (neutral, opt-in)
    score_delta = 0.0
    if "Entangle" in triggered_modules:
        score_delta += OPERATOR_WEIGHTS.get("↔", 0.0)
    if "Collapse" in triggered_modules:
        score_delta += OPERATOR_WEIGHTS.get("⧖", 0.0)
    if "Guide" in triggered_modules:
        score_delta += OPERATOR_WEIGHTS.get("🧭", 0.0)

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
        "score_delta": score_delta,
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

def parse_glyph_packet(packet: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Back-compat helper used by GlyphNet terminal.
    Accepts either a qglyph packet or a single-glyph packet and returns a normalized interpretation dict.
      Expected inputs:
        { "qglyph": { "superposition": [...], "entangled_with": [...], "metadata": {...} } }
        { "glyph": "🧠", "meta": {...} }
        { "symbol": "🧠", "meta": {...} }
        { "value": "🧠", "meta": {...} }   # very old producers
    """
    context = (context or {}).copy()

    if not isinstance(packet, dict):
        return {"type": "error", "error": "invalid_packet_type", "packet": str(type(packet))}

    # qglyph path
    if "qglyph" in packet and isinstance(packet["qglyph"], dict):
        qg = packet["qglyph"]
        # allow packet-level metadata to flow into qglyph metadata
        if "meta" in packet and isinstance(packet["meta"], dict):
            qg.setdefault("metadata", {}).update(packet["meta"])
        return interpret_qglyph(qg, context)

    # single glyph path
    glyph = packet.get("glyph") or packet.get("symbol") or packet.get("value")
    if glyph is not None:
        # pass through metadata if present
        meta = packet.get("meta") or packet.get("metadata") or {}
        ctx = context.copy()
        ctx.setdefault("metadata", meta)
        result = interpret_glyph(str(glyph), ctx)
        result["type"] = "glyph"
        return result

    return {"type": "noop", "reason": "no_glyph_in_packet", "packet_keys": list(packet.keys())}

# ────────────────────────────────────────────────
# 🔧 Glyph DSL Compiler / Parser (proper, back-compat)
# ────────────────────────────────────────────────
_LABEL_TO_GLYPH = {v: k for k, v in GLYPH_SYMBOL_MAP.items()}

def _normalize_text(s: str) -> str:
    return " ".join(str(s).strip().split())

def _split_header_payload_action(text: str) -> Tuple[list, str, str]:
    # Parses:  "LabelA | LabelB : payload → Action"
    labels, payload, action = [], "", ""
    head, sep, tail = text.partition(":")
    if sep:
        labels = [l.strip() for l in head.split("|") if l.strip()]
        payload = tail.strip()
    else:
        payload = text.strip()
    body, sep2, act = payload.partition("→")
    if sep2:
        payload = body.strip()
        action = act.strip()
    return labels, payload, action

def _labels_to_glyphs(labels: list) -> list:
    out = []
    for lab in labels:
        if lab in _LABEL_TO_GLYPH:
            out.append(_LABEL_TO_GLYPH[lab])     # map known label → glyph
        elif lab in GLYPH_SYMBOL_MAP:
            out.append(lab)                       # already a glyph
        else:
            out.append(lab)                       # keep free-form label (goes to meta tags)
    return out

def compile_glyphs(glyph_data: Union[str, list, dict], *, tags: list = None, metadata: dict = None) -> dict:
    """
    Compile a glyph expression into a normalized glyph block.

    Accepts:
      • str  — DSL:  'LabelA | LabelB : payload → Action'
      • list — sequence of glyphs, e.g. ['Δ','λ','Σ']
      • dict — pass-through; fills defaults

    Returns:
      {
        "type": "glyph_block",
        "glyphs": [...],
        "payload": "...",
        "action": "Vault",
        "meta": { "labels": [...], "tags": [...], ... },
        "original": "raw input if provided"
      }
    """
    tags = tags or []
    metadata = metadata or {}

    if isinstance(glyph_data, dict):
        blk = {
            "type": "glyph_block",
            "glyphs": glyph_data.get("glyphs", []),
            "payload": glyph_data.get("payload", ""),
            "action": glyph_data.get("action", ""),
            "meta": glyph_data.get("meta", {}),
            "original": glyph_data.get("original"),
        }
        blk["meta"].setdefault("tags", [])
        blk["meta"]["tags"] = list({*blk["meta"]["tags"], *tags})
        blk["meta"].update(metadata)
        return blk

    if isinstance(glyph_data, list):
        return {
            "type": "glyph_block",
            "glyphs": glyph_data,
            "payload": "",
            "action": "",
            "meta": {"labels": [], "tags": tags, **metadata},
            "original": None,
        }

    if isinstance(glyph_data, str):
        raw = glyph_data
        labels, payload, action = _split_header_payload_action(raw)
        labels_norm = [_normalize_text(l) for l in labels]
        payload = _normalize_text(payload)
        action = _normalize_text(action)

        mapped = _labels_to_glyphs(labels_norm)
        glyph_list, free_labels = [], []
        for item in mapped:
            if item in GLYPH_SYMBOL_MAP:
                glyph_list.append(item)
            else:
                free_labels.append(item)

        meta = {"labels": labels_norm, "tags": list({*tags, *free_labels}), **metadata}
        return {
            "type": "glyph_block",
            "glyphs": glyph_list,
            "payload": payload,
            "action": action,
            "meta": meta,
            "original": raw,
        }

    # Fallback: wrap unknown input as payload
    return {
        "type": "glyph_block",
        "glyphs": [],
        "payload": str(glyph_data),
        "action": "",
        "meta": {"labels": [], "tags": tags, **metadata},
        "original": None,
    }

def parse_logic(glyph_block: Union[dict, str, list]) -> str:
    """
    Convert a glyph block back into readable DSL.

    Priority:
      1) If 'original' exists → return it (lossless).
      2) Reconstruct: 'LabelA | LabelB : payload → Action'
    """
    if isinstance(glyph_block, str):
        return glyph_block

    if isinstance(glyph_block, list):
        labels = [GLYPH_SYMBOL_MAP.get(g, g) for g in glyph_block]
        hdr = " | ".join(labels).strip()
        return hdr or "(empty)"

    if not isinstance(glyph_block, dict):
        return str(glyph_block)

    if glyph_block.get("original"):
        return glyph_block["original"]

    glyphs = glyph_block.get("glyphs", [])
    payload = glyph_block.get("payload", "") or ""
    action = glyph_block.get("action", "") or ""
    meta = glyph_block.get("meta", {}) or {}

    labels = [GLYPH_SYMBOL_MAP.get(g, g) for g in glyphs]
    extra = [t for t in meta.get("tags", []) if t not in labels]
    header_parts = labels + extra
    header = " | ".join(header_parts).strip()

    parts = []
    if header:
        parts.append(header + " :")
    if payload:
        parts.append(payload)
    if action:
        parts.append(f"→ {action}")

    return _normalize_text(" ".join(parts)) or "(empty)"