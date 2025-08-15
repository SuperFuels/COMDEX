from backend.modules.glyphos.glyph_parser import parse_glyph
from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.websocket_manager import websocket_manager
from backend.modules.glyphos.glyph_summary import summarize_glyphs
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.aion.dream_core import run_dream
from backend.modules.consciousness.reflection_engine import generate_reflection
from backend.modules.dna_chain.dna_proposer import propose_dna_mutation
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.modules.tessaris.tessaris_trigger import TessarisTrigger
from backend.modules.glyphos.entanglement_utils import entangle_glyphs
from backend.modules.consciousness.awareness_engine import AwarenessEngine
# 🧠 Lazy import ONLY for circular dependency
def execute_goal_logic():
    from backend.modules.skills.goal_engine import GoalEngine
    goal_engine = GoalEngine()

# ✅ Cost estimator and GlyphPush adapter
from backend.modules.codex.codex_cost_estimator import estimate_glyph_cost
from backend.modules.codex.codex_context_adapter import CodexContextAdapter
from backend.modules.glyphnet.glyph_push_dispatcher import dispatch_glyph_push

import time
import uuid


class GlyphExecutor:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.dispatcher = GlyphDispatcher(state_manager)
        self.active_container = self.state_manager.get_current_container()
        self.goal_engine = GoalEngine()
        self.memory_engine = MemoryEngine()
        self.personality = PersonalityProfile()
        self.milestone_tracker = MilestoneTracker()
        self.container_id = self.state_manager.get_current_container_id() or "default"
        self.bridge = MemoryBridge(self.container_id)
        self.container_path = self.active_container.get("path", "") if self.active_container else ""
        self.codex_trace = CodexTrace()

    def read_glyph_at(self, x: int, y: int, z: int) -> str:
        cube = self.active_container.get("cubes", {}).get(f"{x},{y},{z}", {})
        return cube.get("glyph", "")

    async def broadcast_glyph_execution(self, glyph: str, action: str, trigger_type: str, coord: str, cost: float = 4.2):
        try:
            await websocket_manager.broadcast({
                "event": "glyph_execution",
                "payload": {
                    "glyph": glyph,
                    "action": action,
                    "source": "glyph_executor",
                    "timestamp": int(time.time()),
                    "cost": cost,
                    "trace_id": str(uuid.uuid4())[:8],
                    "trigger_type": trigger_type,
                    "sqi": True,
                    "detail": {
                        "coord": coord,
                        "container": self.container_id,
                        "operator": glyph,
                        "ethics_risk": 0.1,
                        "energy": 2.1,
                        "delay": 0.5,
                        "opportunity_loss": 0.2,
                    }
                }
            })
        except Exception as e:
            print(f"[⚠️] WebSocket glyph_execution failed: {e}")

    async def execute_glyph_at(self, x: int, y: int, z: int):
        coord = f"{x},{y},{z}"
        glyph = self.read_glyph_at(x, y, z)
        if not glyph:
            print(f"⚠️ No glyph found at {coord}")
            return

        parsed = parse_glyph(glyph)
        print(f"🔍 Parsed glyph at {coord}: {parsed}")
        self.dispatcher.dispatch(parsed)

        current_tick = self.state_manager.get_tick()
        trace_data = {
            "glyph": glyph,
            "coord": coord,
            "tick": current_tick,
            "origin": "glyph_executor",
        }

        try:
            cost = estimate_glyph_cost(glyph, container_id=self.container_id)
        except Exception:
            cost = 4.2

        self.codex_trace.log({
            **trace_data,
            "container": self.container_id,
            "action": "executed",
            "source": "glyph_executor"
        })

    async def trigger_glyph_remotely(self, container_id: str, x: int, y: int, z: int, source: str = "remote"):
        if container_id != self.container_id:
            self.container_id = container_id
            self.active_container = self.state_manager.get_container(container_id)
            self.container_path = self.active_container.get("path", "") if self.active_container else ""
            self.bridge = MemoryBridge(container_id)

        coord = f"{x},{y},{z}"
        glyph = self.read_glyph_at(x, y, z)

        if not glyph:
            print(f"⚠️ No glyph found at {coord} for remote trigger")
            return

        print(f"🛰️ Remotely triggering glyph {glyph} at {coord} from {source}")
        await self.execute_glyph_at(x, y, z)

        current_tick = self.state_manager.get_tick()
        trace_data = {
            "glyph": glyph,
            "coord": coord,
            "tick": current_tick,
            "container": self.container_id,
            "origin": "glyph_executor"
        }

        # === TRIGGER MAP ===
        if glyph == "↔":
            entangle_glyphs("↔", f"entangled:{coord}")
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "entangle_glyph",
                "trait_impact": {"empathy": +0.01},
            })
            self.personality.adjust_trait("empathy", +0.01)
            _trigger(glyph, {**trace_data, "role": "Symbolic entanglement"})
            await self.brself.bridge.traceoadcast_glyph_execution(glyph, "entangle_glyph", "entanglement", coord)
            dispatch_glyph_push(trace_data)

        elif glyph == "⮁":
            result = await propose_dna_mutation(reason="Glyph ⮁ triggered mutation")
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "propose_dna_mutation",
                "proposal_id": result.get("proposal_id"),
            })
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "DNA proposal", "proposal_id": result.get("proposal_id")})
            await self.broadcast_glyph_execution(glyph, "propose_dna_mutation", "mutation", coord)

            # 🧠 Run self-rewriting logic
            rewritten = run_self_rewrite(self.container_path, coord)
            if rewritten:
                self.memory_engine.store({
                    **trace_data,
                    "type": "glyph_trigger",
                    "action": "self_rewrite",
                    "result": True
                })
                self.bridge.trace_trigger(glyph, {**trace_data, "role": "Self-rewriting glyph"})

            dispatch_glyph_push(trace_data)

        elif glyph == "🧠":
            from backend.modules.tessaris.tessaris_trigger import TessarisTrigger
            TessarisTrigger().run_from_memory(context=trace_data)
            self.memory_engine.store({**trace_data, "type": "glyph_trigger", "action": "tessaris_memory"})
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Tessaris from memory"})
            await self.broadcast_glyph_execution(glyph, "tessaris_memory", "tessaris", coord)

        elif glyph == "🧬":
            from backend.modules.tessaris.tessaris_trigger import TessarisTrigger
            TessarisTrigger().run_from_dna(context=trace_data)
            self.memory_engine.store({**trace_data, "type": "glyph_trigger", "action": "tessaris_dna"})
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Tessaris from DNA"})
            await self.broadcast_glyph_execution(glyph, "tessaris_dna", "tessaris", coord)

        elif glyph == "🪄":
            from backend.modules.tessaris.tessaris_trigger import TessarisTrigger
            TessarisTrigger().run_from_symbol(context=trace_data)
            self.memory_engine.store({**trace_data, "type": "glyph_trigger", "action": "tessaris_symbol"})
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Tessaris from symbol"})
            await self.broadcast_glyph_execution(glyph, "tessaris_symbol", "tessaris", coord)

        elif glyph == "⚛":
            result = await run_dream(source="glyph ⚛")
            self.memory_engine.store({**trace_data, "type": "glyph_trigger", "action": "run_dream", "output": result})
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Dream generation"})
            await self.broadcast_glyph_execution(glyph, "run_dream", "dream", coord)

        elif glyph == "🧽":
            notes = await generate_reflection(prompt="Triggered by glyph 🧽")
            self.memory_engine.store({**trace_data, "type": "glyph_trigger", "action": "generate_reflection", "reflection": notes})
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Reflection trigger"})
            await self.broadcast_glyph_execution(glyph, "generate_reflection", "reflection", coord)

        elif glyph == "✦":
            self.milestone_tracker.start_new_milestone("From glyph ✦")
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "start_milestone",
                "trait_impact": {"ambition": +0.02},
            })
            self.personality.adjust_trait("ambition", +0.02)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Start milestone"})
            await self.broadcast_glyph_execution(glyph, "start_milestone", "milestone", coord)

        elif glyph == "🎯":
            goal_id = self.goal_engine.create_goal("Reflect on surroundings from glyph 🎯", priority=7)
            self.milestone_tracker.check_milestones()
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "created_goal",
                "goal_id": goal_id,
                "trait_impact": {"ambition": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.01)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Create reflection goal", "goal_id": goal_id})
            await self.broadcast_glyph_execution(glyph, "created_goal", "goal", coord)

        elif glyph == "🌟":
            self.milestone_tracker.mark_manual_milestone("glyph_star_trigger")
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "milestone_unlocked",
                "milestone": "glyph_star_trigger",
                "trait_impact": {"ambition": +0.02, "curiosity": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.02)
            self.personality.adjust_trait("curiosity", +0.01)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Milestone unlock"})
            await self.broadcast_glyph_execution(glyph, "milestone_unlocked", "milestone", coord)

        elif glyph == "🦰":
            self.goal_engine.boot_next_skill()
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "boot_next_skill",
                "trait_impact": {"curiosity": +0.02},
            })
            self.personality.adjust_trait("curiosity", +0.02)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Boot next skill"})
            await self.broadcast_glyph_execution(glyph, "boot_next_skill", "skill", coord)

        elif glyph == "⚙":
            self.goal_engine.run_top_goal()
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "run_top_goal",
                "trait_impact": {"ambition": +0.01},
            })
            self.personality.adjust_trait("ambition", +0.01)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Run top goal"})
            await self.broadcast_glyph_execution(glyph, "run_top_goal", "goal", coord)

        elif glyph == "🔬":
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "curiosity_spark",
                "trait_impact": {"curiosity": +0.03, "humility": +0.01},
            })
            self.personality.adjust_trait("curiosity", +0.03)
            self.personality.adjust_trait("humility", +0.01)
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Curiosity boost"})
            await self.broadcast_glyph_execution(glyph, "curiosity_spark", "curiosity", coord)

        else:
            self.memory_engine.store({
                **trace_data,
                "type": "glyph_trigger",
                "action": "executed_generic_glyph",
            })
            self.bridge.trace_trigger(glyph, {**trace_data, "role": "Generic glyph execution"})
            await self.broadcast_glyph_execution(glyph, "executed_generic_glyph", "generic", coord)

            # 🌀 AwarenessEngine hook for confidence tracking
            from backend.modules.consciousness.awareness_engine import AwarenessEngine
            awareness = AwarenessEngine(memory_engine=self.memory_engine, container=self.active_container)
            awareness.record_confidence(
                glyph=glyph,
                coord=coord,
                container_id=self.container_id,
                tick=current_tick,
                trigger_type="generic"
            )
            # ⛔ Log symbolic blindspots (fallback catch-all case)
            awareness.log_blindspot(
                glyph=glyph,
                coord=coord,
                container_id=self.container_id,
                tick=current_tick,
                context="fallback"
            )
        try:
            cubes = self.active_container.get("cubes", {})
            summary = summarize_glyphs(cubes)
            await websocket_manager.broadcast({
                "event": "glyph_summary",
                "data": summary,
                "source": "glyph_executor",
                "tick": current_tick,
            })
        except Exception as e:
            print(f"[⚠️] Glyph summary broadcast failed: {e}")

from typing import Any, Dict, Optional

# Import the canonical interpreters
try:
    from backend.modules.glyphos.glyph_logic import interpret_glyph, interpret_qglyph
except Exception as e:  # keep import failure visible to caller
    interpret_glyph = None
    interpret_qglyph = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


def execute_glyph_logic(payload: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Back-compat execution entrypoint used by GlyphNet terminal.

    Accepts:
      - a single glyph string: "🧠"
      - a dict with {"glyph": "..."} or {"symbol": "..."} or {"value": "..."}
      - a qglyph dict: {"qglyph": {"superposition": [...], "entangled_with": [...], "metadata": {...}}}

    Returns a normalized interpretation dict.
    """
    if _IMPORT_ERROR:
        return {"type": "error", "error": "import_failed", "detail": str(_IMPORT_ERROR)}

    ctx = (context or {}).copy()

    # qglyph path
    if isinstance(payload, dict) and "qglyph" in payload and isinstance(payload["qglyph"], dict):
        qg = payload["qglyph"]
        # merge top-level meta if present
        if "meta" in payload and isinstance(payload["meta"], dict):
            qg.setdefault("metadata", {}).update(payload["meta"])
        return interpret_qglyph(qg, ctx)

    # single glyph path (string or small dict)
    if isinstance(payload, str):
        return interpret_glyph(payload, ctx)

    if isinstance(payload, dict):
        glyph = payload.get("glyph") or payload.get("symbol") or payload.get("value")
        meta = payload.get("meta") or payload.get("metadata") or {}
        if glyph is not None:
            c2 = ctx.copy()
            c2.setdefault("metadata", meta)
            out = interpret_glyph(str(glyph), c2)
            out["type"] = "glyph"
            return out

    return {"type": "noop", "reason": "unrecognized_payload", "payload_type": str(type(payload))}


# ✅ DNA switch registration
DNA_SWITCH.register(__file__, file_type="backend")