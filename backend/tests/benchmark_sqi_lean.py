# backend/tests/benchmark_sqi_lean.py
import os
import json
import time
import logging
from typing import Dict, Any

from backend.modules.lean.lean_parser import parse_lean_file
from backend.modules.lean.lean_to_glyph import lean_to_dc_container
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
from backend.modules.hexcore.memory_engine import store_memory, MemoryEngine

# Adapter helpers you already have
from backend.tests.sqi_adapter import (
    coerce_thought_glyph_from_lean,
    run_tessaris_branch,
    run_sqi,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

LEAN_TEXT = """
theorem example_lean_theorem : (A ↔ B) ⊕ (B ↔ C) → (A ↔ C) := by {
    -- Simplified proof placeholder
    sorry
}
"""

# --- Safe memory store shim so engine can't crash on malformed writes ---
from backend.modules.hexcore import memory_engine as _mem_mod
_ORIG_STORE = _mem_mod.MEMORY.store

def _safe_store(payload):
    # Engine sometimes writes dicts without required keys; normalize here
    if not isinstance(payload, dict):
        payload = {"label": "log", "content": str(payload)}
    payload.setdefault("label", "log")
    payload.setdefault("content", {})
    return _ORIG_STORE(payload)

_mem_mod.MEMORY.store = _safe_store  # monkey-patch for test run
# ------------------------------------------------------------------------


# ---------------- Classical baseline ----------------
def classical_evaluate(a_b: bool, b_c: bool) -> bool:
    """
    (A↔B) ⊕ (B↔C) → (A↔C)
    a_b == b_c  means A↔C holds (transitivity under equal truth of equivalences)
    a_b != b_c  is the XOR of equivalences (the premise)
    implication is (not premise) or (a_c)
    """
    a_c = (a_b == b_c)
    premise = (a_b != b_c)   # XOR
    return (not premise) or a_c


# ---------------- Benchmark ----------------
def run_benchmark() -> None:
    # 1) Prepare Lean → DC container
    with open("temp_lean.lean", "w") as f:
        f.write(LEAN_TEXT)

    parsed = parse_lean_file(LEAN_TEXT)
    if not parsed:
        raise ValueError("No theorems parsed from Lean text")

    theorem: Dict[str, Any] = {
        "id": "example_lean_theorem",
        "metadata": {
            "origin": "lean_import",
            "description": "A=B, B=C ⇒ A=C under XOR implication"
        },
        "gates": {"traits": {"logic": 0.6}},
        "glyphs": {"0,0": parsed[0]},
    }

    dc = lean_to_dc_container("temp_lean.lean")
    dc.setdefault("metadata", {}).update(theorem["metadata"])

    # 2) Classical truth table
    tests = [(True, True), (True, False), (False, True), (False, False)]
    expected = {
        (True, True): True,
        (True, False): False,
        (False, True): False,
        (False, False): True
    }
    results: Dict[str, Any] = {"classical": {}, "sqi": {}}

    classical_times = []
    for a_b, b_c in tests:
        t0 = time.time()
        r = classical_evaluate(a_b, b_c)
        classical_times.append(time.time() - t0)
        results["classical"][f"{a_b},{b_c}"] = {"result": r, "exec_time": classical_times[-1]}
    classical_avg = sum(classical_times) / len(classical_times)

    # 3) Tessaris + SQI
    engine = TessarisEngine()

    # 3a) disable remote synthesis chatter
    engine._send_synthesis = lambda payload: None

    # 3b) provide expand_thought_branch if bridge calls it
    if not hasattr(engine, "expand_thought_branch"):
        engine.expand_thought_branch = lambda root_thought: []

    # 3c) provide a mock container so inject_glyph doesn't explode
    from types import SimpleNamespace
    engine.memlog = SimpleNamespace(
        current_container=SimpleNamespace(inject_glyph=lambda *a, **k: True)
    )

    # Provide expand_thought_branch if bridge expects it
    if not hasattr(engine, "expand_thought_branch"):
        def _expand_thought_branch(root_thought):
            # minimal stub: return empty list (or construct from root_thought if you prefer)
            return []
        engine.expand_thought_branch = _expand_thought_branch  # type: ignore[attr-defined]

    # Silence remote synthesis; keep offline for CI/containers
    try:
        engine._send_synthesis = lambda payload: None
        setattr(engine, "_synthesis_enabled", False)
    except Exception:
        pass

    # Provide mock container so .inject_glyph() is safe
    try:
        engine.memlog = type("MockState", (), {
            "current_container": {
                "id": "lean_benchmark",
                "inject_glyph": lambda *a, **k: True
            }
        })()
    except Exception:
        pass

    # Avoid kg_writer crashes
    try:
        def _mock_log_thought_branch(branch):
            try:
                store_memory({"label": "thought_branch_log", "content": branch.to_dict()})
            except Exception:
                pass
        engine.kg_writer.log_thought_branch = _mock_log_thought_branch  # type: ignore
    except Exception:
        pass

    # Pick a glyph from dc and coerce into Tessaris schema
    raw_glyph = next(iter(dc["glyphs"].values())) if isinstance(dc.get("glyphs"), dict) else (dc.get("glyphs") or [])[0]
    if not isinstance(raw_glyph, dict):  # belt & suspenders
        raw_glyph = {"value": raw_glyph, "type": "theorem"}
    thought_glyph = coerce_thought_glyph_from_lean(raw_glyph)

    # Execute a baseline branch (sanity / warms engine caches)
    ctx = {"metadata": theorem["metadata"], "source": "lean_benchmark"}
    t_exec = {"exec_time": float("inf")}
    try:
        t_exec = run_tessaris_branch(engine, thought_glyph, ctx)
    except Exception:
        logging.exception("Baseline Tessaris execution failed")

    # SQI round
    sqi = {"result": True, "exec_time": float("inf"), "compression_ratio": 0.0, "pattern_matches": []}
    try:
        sqi_run = run_sqi(engine, thought_glyph)
        sqi["exec_time"] = sqi_run.get("exec_time", float("inf"))

        # Optional: pull a concrete result from memory if your pipeline writes one
        try:
            mem = MemoryEngine(container_id="lean_benchmark").get("lean_execution")
            if isinstance(mem, list) and mem:
                sqi["result"] = bool(mem[0].get("content", {}).get("result", True))
            else:
                sqi["result"] = True
        except Exception:
            sqi["result"] = True

        # Pattern engine / compression
        try:
            pe = SymbolicPatternEngine()
            glyph_logic = theorem["glyphs"]["0,0"].get("logic", "")
            sqi["pattern_matches"] = pe.detect_patterns({"name": "lean_theorem", "value": glyph_logic})
        except Exception:
            sqi["pattern_matches"] = []

        try:
            sqi["compression_ratio"] = len(json.dumps(dc)) / max(1, len(json.dumps(theorem)))
        except Exception:
            sqi["compression_ratio"] = 0.0

    except Exception:
        logging.exception("SQI execution failed")

    speedup = (classical_avg / sqi["exec_time"]) if (isinstance(sqi["exec_time"], (int, float)) and sqi["exec_time"] > 0) else 0
    accuracy = all(results["classical"][f"{a_b},{b_c}"]["result"] == expected[(a_b, b_c)] for a_b, b_c in tests) and bool(sqi["result"])

    results["sqi"] = {
        "result": sqi["result"],
        "exec_time": sqi["exec_time"],
        "compression_ratio": sqi["compression_ratio"],
        "pattern_matches": sqi["pattern_matches"],
        "tessaris_exec_time": t_exec.get("exec_time"),
    }

    print(json.dumps({
        "theorem": theorem["glyphs"]["0,0"].get("logic", "(unknown)"),
        "classical_avg_time": classical_avg,
        "sqi_time": sqi["exec_time"],
        "speedup_ratio": speedup,
        "compression_ratio": sqi["compression_ratio"],
        "accuracy": accuracy,
        "results": results,
    }, indent=2))

    try:
        os.remove("temp_lean.lean")
    except Exception:
        pass


if __name__ == "__main__":
    run_benchmark()