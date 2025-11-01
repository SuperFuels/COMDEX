# File: backend/modules/workspace/research_engine_interface.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, runtime_checkable

@dataclass
class ResearchRequest:
    container_id: str
    query_type: str  # e.g. "codexlang", "symbolic_query", "hypothesis"
    codexlang: Optional[str] = None
    symbolic_tree: Optional[Dict[str, Any]] = None
    hypothesis: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResearchResult:
    ok: bool
    messages: list[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)  # e.g. {"innovation_score": 0.52}
    hypothesis: Optional[str] = None
    contradictions: list[Dict[str, Any]] = field(default_factory=list)
    mutations: list[Dict[str, Any]] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)  # whatever the engine returns

@runtime_checkable
class ResearchEngine(Protocol):
    def execute(self, req: ResearchRequest) -> ResearchResult: ...

# ---------- Adapters / Resolver ----------

def _adapt_execute(engine: Any, req: ResearchRequest) -> ResearchResult:
    """
    Try common method names on various engine implementations, falling back to a stub shape.
    Never throws; always returns a ResearchResult.
    """
    try:
        # Preferred unified entrypoint
        if hasattr(engine, "execute_symbolic_query"):
            out = engine.execute_symbolic_query({
                "container_id": req.container_id,
                "query_type": req.query_type,
                "codexlang": req.codexlang,
                "symbolic_tree": req.symbolic_tree,
                "hypothesis": req.hypothesis,
                "metadata": req.metadata,
            })
        elif hasattr(engine, "execute"):
            out = engine.execute(req.__dict__)
        elif hasattr(engine, "run"):
            out = engine.run(req.__dict__)
        else:
            # Bare engine object - no known method
            return ResearchResult(
                ok=False,
                messages=["Engine has no callable entrypoint (execute/run/execute_symbolic_query)."],
            )

        # Normalize common shapes into ResearchResult
        if isinstance(out, ResearchResult):
            return out

        scores = out.get("scores", {}) if isinstance(out, dict) else {}
        return ResearchResult(
            ok=bool(out.get("ok", True)) if isinstance(out, dict) else True,
            messages=out.get("messages", []) if isinstance(out, dict) else [],
            scores=scores,
            hypothesis=out.get("hypothesis"),
            contradictions=out.get("contradictions", []),
            mutations=out.get("mutations", []),
            payload=out if isinstance(out, dict) else {"raw": out},
        )

    except Exception as e:
        return ResearchResult(ok=False, messages=[f"Engine execution failed: {e}"])

def resolve_engine() -> ResearchEngine:
    """
    Best-effort import order. Returns a lightweight wrapper exposing .execute(req).
    """
    # 1) CodexExecutor
    try:
        from backend.modules.codex.codex_executor import CodexExecutor  # type: ignore
        inst = CodexExecutor()
        return type("CodexAdapter", (), {"execute": lambda _self, req: _adapt_execute(inst, req)})()
    except Exception:
        pass

    # 2) SQIReasoningEngine
    try:
        from backend.modules.sqi.sqi_reasoning_engine import SQIReasoningEngine  # type: ignore
        inst = SQIReasoningEngine()
        return type("SQIAdapter", (), {"execute": lambda _self, req: _adapt_execute(inst, req)})()
    except Exception:
        pass

    # 3) PatternMutationEngine
    try:
        from backend.modules.creative.pattern_mutation_engine import PatternMutationEngine  # type: ignore
        inst = PatternMutationEngine()
        return type("PMAdapter", (), {"execute": lambda _self, req: _adapt_execute(inst, req)})()
    except Exception:
        pass

    # 4) TessarisEngine
    try:
        from backend.modules.tessaris.tessaris_engine import TessarisEngine  # type: ignore
        inst = TessarisEngine()
        return type("TessarisAdapter", (), {"execute": lambda _self, req: _adapt_execute(inst, req)})()
    except Exception:
        pass

    # 5) Fallback heuristic engine
    class _FallbackEngine:
        def execute(self, req: ResearchRequest) -> ResearchResult:
            # Minimal "works everywhere" result
            base_score = 0.52
            msg = f"[fallback] handled {req.query_type}"
            return ResearchResult(ok=True, messages=[msg], scores={"innovation_score": base_score}, payload={"echo": req.__dict__})

    return _FallbackEngine()

def execute_with_default_engine(req: ResearchRequest) -> ResearchResult:
    engine = resolve_engine()
    return engine.execute(req)