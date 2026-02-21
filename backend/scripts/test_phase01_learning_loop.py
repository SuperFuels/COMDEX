#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_learning.teaching_memory_store import TeachingMemoryStore
from backend.modules.aion_learning.teaching_retriever import TeachingRetriever
from backend.modules.aion_learning.teaching_applier import apply_teaching_to_ks
from backend.modules.aion_runtime.aion_ready_check import run_ready_check
from backend.modules.aion_conversation.minimal_response_composer import (
    MinimalResponseComposer,
    AionKnowledgeState,
)
from backend.modules.aion_learning.teaching_session_schema import (
    new_teaching_session,
    TeachingTurn,
    CorrectionRecord,
    validate_target_confidence,
)

# Optional (Phase 0.1 local shim persistence)
# This harness does NOT require a production learner yet.
# It stores teaching concepts in a local json file and applies them to KS before compose.
TEACHING_MEMORY_FILE = Path("data/logs/phase0_learning_memory.json")

OUT_DIR = Path("data/logs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STORE = TeachingMemoryStore(TEACHING_MEMORY_FILE)
RETRIEVER = TeachingRetriever(min_score=1.0)


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _extract_confidence_from_text(text: str) -> Optional[float]:
    # Matches either:
    #   "My confidence is 0.38."
    #   "(confidence: 0.62)"
    patterns = [
        r"\bconfidence\s+is\s+([0-9]*\.?[0-9]+)\b",
        r"\(\s*confidence\s*:\s*([0-9]*\.?[0-9]+)\s*\)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
    return None


def _load_learning_memory() -> Dict[str, Any]:
    """
    Backward-compatible local loader used by tests and phase0.1 harness.

    We keep this even though STORE exists because:
    - tests may patch/read the raw json file directly
    - it avoids hard coupling to TeachingMemoryStore internals
    """
    if not TEACHING_MEMORY_FILE.exists():
        return {"concepts": {}}
    try:
        data = json.loads(TEACHING_MEMORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"concepts": {}}
        concepts = data.get("concepts")
        if not isinstance(concepts, dict):
            data["concepts"] = {}
        return data
    except Exception:
        return {"concepts": {}}


def _save_learning_memory(mem: Dict[str, Any]) -> None:
    TEACHING_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEACHING_MEMORY_FILE.write_text(json.dumps(mem, indent=2), encoding="utf-8")


def _normalize_concepts_from_mem(mem: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    concepts = mem.get("concepts", {}) or {}
    if not isinstance(concepts, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in concepts.items():
        if isinstance(k, str) and isinstance(v, dict):
            out[k] = v
    return out


def _remember_correction(concept_label: str, correction: CorrectionRecord) -> None:
    """
    Persist via STORE if available, then mirror to raw json fallback format expected by this harness/tests.
    """
    routing_hints = {
        "intents": ["answer", "roadmap_explanation"],
        "topic_keywords": [
            "aion",
            "phase",
            "conversation",
            "roadmap",
            "building",
            "next",
            "orchestration",
            "learning",
            "loop",
        ],
        "phrases": [
            "what aion is building next",
            "explain what aion is building next",
            "aion roadmap",
        ],
    }

    # Primary path (new store abstraction)
    try:
        STORE.upsert_concept(
            concept_label=concept_label,
            corrected_response=correction.corrected_response,
            target_confidence=float(correction.target_confidence),
            tags=list(correction.tags or []),
            notes=correction.notes,
            correction_reason=correction.correction_reason,
            routing_hints=routing_hints,
        )
    except Exception:
        # Fallback below still guarantees persistence for harness
        pass

    # Raw JSON mirror (backward compatible for tests/helpers)
    mem = _load_learning_memory()
    concepts = mem.setdefault("concepts", {})
    concepts[concept_label] = {
        "concept_label": concept_label,
        "corrected_response": correction.corrected_response,
        "target_confidence": float(correction.target_confidence),
        "tags": list(correction.tags or []),
        "notes": correction.notes,
        "correction_reason": correction.correction_reason,
        "routing_hints": routing_hints,
        "updated_at": time.time(),
    }
    _save_learning_memory(mem)


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t]


def _manual_match_roadmap_concept(
    ks: AionKnowledgeState, user_text: str, concept: Dict[str, Any]
) -> Tuple[bool, float, List[str]]:
    """
    Deterministic scoring for Phase 0.1 tests. This is intentionally explicit and stable.
    """
    score = 0.0
    reasons: List[str] = []

    user_l = (user_text or "").lower()
    topic_l = str(getattr(ks, "topic", "") or "").lower()
    intent_l = str(getattr(ks, "intent", "") or "").lower()

    # Intent match (light signal)
    if intent_l in {"answer", "roadmap_explanation"}:
        score += 1.0
        reasons.append(f"intent:{intent_l}")

    # Topic/user token overlap
    topic_tokens = {t for t in _tokenize(topic_l) if len(t) >= 4}
    user_tokens = {t for t in _tokenize(user_l) if len(t) >= 4}
    overlap = sorted(topic_tokens & user_tokens)
    if overlap:
        score += min(2.0, 0.75 * len(overlap))
        reasons.append(f"topic_overlap:{overlap}")

    # Routing hints (if present)
    routing = concept.get("routing_hints", {}) if isinstance(concept, dict) else {}
    if not isinstance(routing, dict):
        routing = {}

    hinted_keywords = set()
    for kw in routing.get("topic_keywords", []) or []:
        if isinstance(kw, str):
            hinted_keywords.add(kw.lower())

    default_keywords = {
        "aion",
        "building",
        "next",
        "roadmap",
        "plan",
        "future",
        "layers",
        "phase",
        "orchestration",
        "learning",
        "loop",
    }
    keyword_pool = hinted_keywords or default_keywords
    kw_overlap = sorted(user_tokens & keyword_pool)
    if kw_overlap:
        score += min(2.5, 0.75 * len(kw_overlap))
        reasons.append(f"user_keyword_overlap:{kw_overlap}")

    phrases: List[str] = []
    for p in (routing.get("phrases", []) or []):
        if isinstance(p, str):
            phrases.append(p.lower())
    if not phrases:
        phrases = [
            "what aion is building next",
            "explain what aion is building next",
            "aion roadmap",
            "what is aion building next",
        ]

    phrase_hits = [p for p in phrases if p in user_l]
    if phrase_hits:
        score += 3.0
        reasons.append(f"phrase_hits:{phrase_hits}")

    # Threshold tuned to:
    # - apply to explicit roadmap prompts
    # - not apply to generic prompts / poems / unrelated text
    apply_threshold = 5.0
    should_apply = score >= apply_threshold
    return should_apply, round(score, 2), reasons


def _apply_teaching_to_ks(ks: AionKnowledgeState, user_text: str) -> Dict[str, Any]:
    return apply_teaching_to_ks(
        ks=ks,
        user_text=user_text,
        store=STORE,
        retriever=RETRIEVER,
        apply_threshold=5.0,
    )


def _build_base_knowledge_state() -> AionKnowledgeState:
    return AionKnowledgeState(
        intent="answer",
        topic="AION Phase 0 conversation",
        confidence=0.38,  # intentionally low baseline
        known_facts=[
            "AION runtime modules are already active through launch_tessaris_stack.sh",
            "TCFK fusion provides live coherence telemetry",
        ],
        goals=[
            "build a stable conversation loop",
            "store teacher corrections in structured schema",
        ],
        unresolved=[
            "response generation path",
            "teaching session format",
        ],
        fusion_snapshot={"sigma": 0.81, "psi_tilde": 0.74},
        source_refs=["TCFK", "RAL", "Theta Orchestrator"],
    )


def _make_correction_for_baseline(baseline_text: str) -> CorrectionRecord:
    return CorrectionRecord(
        aion_original_response=baseline_text,
        corrected_response=(
            "AION already has the core runtime online. Next, it is building a stronger conversation layer: "
            "conversation orchestration, skill runtime unification, and learning loops that apply teacher corrections "
            "to future responses."
        ),
        correction_reason=(
            "Original response was honest but too hesitant and indirect for a roadmap explanation."
        ),
        concept_label="roadmap_explanation_simple",
        target_confidence=validate_target_confidence(0.72),
        tags=["phase0", "roadmap", "response-clarity", "teaching-loop"],
        notes="Keep honesty, but lead with a direct summary sentence and clearer roadmap wording.",
    )


def _write_teaching_session(
    user_text: str,
    baseline_text: str,
    baseline_conf: float,
    correction: CorrectionRecord,
    run_idx: int,
) -> Path:
    session = new_teaching_session(
        teacher_type="human",
        teacher_id="kevin",
        mode="manual",
        objective="Teach AION to explain roadmap simply and confidently",
        metadata={
            "phase": "phase0_1",
            "test_script": "test_phase01_learning_loop.py",
            "run": run_idx,
        },
    )

    turn = TeachingTurn(
        turn_id=f"turn_{run_idx:03d}",
        user_input=user_text,
        inferred_intent="roadmap_explanation",
        topic="AION next build layers",
        aion_response=baseline_text,
        aion_confidence=baseline_conf,
        correction=correction,
        accepted_as_is=False,
        teaching_notes="Good honesty. Need stronger summary sentence first.",
    )
    session.add_turn(turn)

    out_file = OUT_DIR / f"phase01_teaching_session_run{run_idx:03d}.json"
    out_file.write_text(session.to_json(), encoding="utf-8")
    return out_file


def _compose_once(user_text: str, apply_teaching: bool = False) -> Dict[str, Any]:
    composer = MinimalResponseComposer()

    # Build fresh KS and deep-copy for safety (future-proof against nested mutation)
    ks = deepcopy(_build_base_knowledge_state())

    teaching_meta: Dict[str, Any] = {
        "teaching_applied": False,
        "applied_concepts": [],
        "teaching_match_score": 0.0,
        "teaching_match_reasons": [],
    }
    if apply_teaching:
        teaching_meta = _apply_teaching_to_ks(ks, user_text)

    start_ms = _now_ms()
    composed = composer.compose(user_text=user_text, ks=ks)
    duration_ms = _now_ms() - start_ms

    # enrich metadata locally (non-breaking)
    metadata = dict(getattr(composed, "metadata", {}) or {})
    metadata.update(teaching_meta)
    metadata["phase"] = "phase0_1_learning_loop_harness"
    metadata["compose_duration_ms"] = round(duration_ms, 3)

    parsed_conf = _extract_confidence_from_text(str(composed.text))
    object_conf = _safe_float(getattr(composed, "confidence", None), 0.0)
    effective_conf = parsed_conf if parsed_conf is not None else object_conf

    # Freeze values into plain Python types now (prevents mutation/alias bugs)
    text = str(composed.text)
    confidence = float(object_conf if object_conf else effective_conf)
    parsed_confidence = float(effective_conf)

    return {
        "text": text,
        "confidence": confidence,
        "parsed_confidence": parsed_confidence,
        "metadata": metadata,
        "duration_ms": float(duration_ms),
    }


def _assert_improvement(baseline: Dict[str, Any], improved: Dict[str, Any]) -> List[str]:
    failures: List[str] = []

    if baseline["text"] == improved["text"]:
        failures.append("text did not change after teaching")

    # Correct comparison: baseline vs improved
    b_conf = _safe_float(
        baseline.get("parsed_confidence", baseline.get("confidence", 0.0)), 0.0
    )
    a_conf = _safe_float(
        improved.get("parsed_confidence", improved.get("confidence", 0.0)), 0.0
    )
    if a_conf <= b_conf:
        failures.append(
            f"confidence did not increase (baseline={b_conf:.2f}, improved={a_conf:.2f})"
        )

    md = improved.get("metadata", {}) or {}
    if not md.get("teaching_applied"):
        failures.append("metadata.teaching_applied != true")

    applied = md.get("applied_concepts") or []
    if "roadmap_explanation_simple" not in applied:
        failures.append("roadmap_explanation_simple not in metadata.applied_concepts")

    return failures


def run_once(run_idx: int, quiet: bool = False) -> Dict[str, Any]:
    t0 = _now_ms()

    # 1) Ready check
    ready = run_ready_check()
    ready_ok = bool(ready.get("required_ok")) and bool(ready.get("all_ok"))

    # Extract API latency for summary
    api_latency_ms = None
    for svc in ready.get("services", []) or []:
        if svc.get("name") == "API":
            api_latency_ms = svc.get("latency_ms")
            break

    user_text = "Explain what AION is building next."

    # 2) Baseline compose (no teaching applied)
    baseline = _compose_once(user_text=user_text, apply_teaching=False)

    # Freeze baseline values immediately (belt-and-braces against accidental mutation)
    baseline_text = str(baseline["text"])
    baseline_conf = float(baseline["parsed_confidence"])
    baseline_meta = dict(baseline.get("metadata", {}) or {})

    # 3) Create/write teaching correction session (simulated human teacher)
    correction = _make_correction_for_baseline(baseline_text)
    teaching_file = _write_teaching_session(
        user_text=user_text,
        baseline_text=baseline_text,
        baseline_conf=baseline_conf,
        correction=correction,
        run_idx=run_idx,
    )

    # 4) Persist correction into local phase0.1 memory shim
    _remember_correction("roadmap_explanation_simple", correction)

    # 5) Re-compose with teaching applied
    improved = _compose_once(user_text=user_text, apply_teaching=True)

    # Freeze improved values too
    improved_text = str(improved["text"])
    improved_conf = float(improved["parsed_confidence"])
    improved_meta = dict(improved.get("metadata", {}) or {})

    # 6) Assertions
    failures: List[str] = []
    if not ready_ok:
        failures.append("ready check failed")

    failures.extend(
        _assert_improvement(
            {
                **baseline,
                "text": baseline_text,
                "parsed_confidence": baseline_conf,
                "metadata": baseline_meta,
            },
            {
                **improved,
                "text": improved_text,
                "parsed_confidence": improved_conf,
                "metadata": improved_meta,
            },
        )
    )
    passed = len(failures) == 0

    total_ms = _now_ms() - t0

    result = {
        "run": run_idx,
        "passed": passed,
        "failures": failures,
        "ready_status": ready.get("status"),
        "ready_required_ok": bool(ready.get("required_ok")),
        "ready_all_ok": bool(ready.get("all_ok")),
        "api_latency_ms": api_latency_ms,
        "baseline_confidence": baseline_conf,
        "improved_confidence": improved_conf,
        "baseline_text": baseline_text,
        "improved_text": improved_text,
        "baseline_metadata": baseline_meta,
        "improved_metadata": improved_meta,
        "teaching_file": str(teaching_file),
        "duration_ms": round(total_ms, 3),
    }

    if not quiet:
        print(f"===== RUN {run_idx} =====")
        print("=== READY CHECK ===")
        print(json.dumps(ready, indent=2))

        print("\n=== BASELINE RESPONSE ===")
        print(baseline_text)
        print(json.dumps(baseline_meta, indent=2))

        print("\n=== IMPROVED RESPONSE (TEACHING APPLIED) ===")
        print(improved_text)
        print(json.dumps(improved_meta, indent=2))

        print(f"\n=== TEACHING SESSION WRITTEN ===\n{teaching_file}")

        if failures:
            print("\n=== ASSERTION FAILURES ===")
            for f in failures:
                print(f"- {f}")

    return result


def _fmt_stats(values: List[float]) -> str:
    if not values:
        return "n/a"
    return f"min={min(values):.2f}  max={max(values):.2f}  avg={statistics.mean(values):.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0.1 learning-loop proof harness")
    parser.add_argument("--runs", type=int, default=1, help="number of runs")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    parser.add_argument("--fail-fast", action="store_true", help="stop on first failure")
    parser.add_argument(
        "--reset-learning-memory",
        action="store_true",
        help="clear local phase0.1 teaching memory before running",
    )
    args = parser.parse_args()

    if args.runs < 1:
        print("runs must be >= 1")
        return 2

    if args.reset_learning_memory:
        # Prefer store abstraction, but also ensure raw file is gone for deterministic tests
        try:
            STORE.clear()
        except Exception:
            pass
        if TEACHING_MEMORY_FILE.exists():
            TEACHING_MEMORY_FILE.unlink()

    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    for i in range(1, args.runs + 1):
        res = run_once(run_idx=i, quiet=args.quiet)
        results.append(res)
        if res["passed"]:
            passed += 1
        else:
            failed += 1
            if args.fail_fast:
                break

    summary = {
        "runs": len(results),
        "passed": passed,
        "failed": failed,
    }

    durations = [float(r["duration_ms"]) for r in results]
    api_latencies = [
        float(r["api_latency_ms"]) for r in results if r.get("api_latency_ms") is not None
    ]
    baseline_conf = [float(r["baseline_confidence"]) for r in results]
    improved_conf = [float(r["improved_confidence"]) for r in results]
    confidence_deltas = [ic - bc for ic, bc in zip(improved_conf, baseline_conf)]

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"Duration ms        {_fmt_stats(durations)}")
    print(f"API latency ms     {_fmt_stats(api_latencies)}")
    print(f"Baseline conf      {_fmt_stats(baseline_conf)}")
    print(f"Improved conf      {_fmt_stats(improved_conf)}")
    print(f"Confidence delta   {_fmt_stats(confidence_deltas)}")

    # Save machine-readable summary
    summary_file = OUT_DIR / "phase01_learning_loop_summary.json"
    summary_file.write_text(
        json.dumps(
            {
                "summary": summary,
                "durations_ms": durations,
                "api_latency_ms": api_latencies,
                "baseline_confidences": baseline_conf,
                "improved_confidences": improved_conf,
                "confidence_deltas": confidence_deltas,
                "results": [
                    {
                        "run": r["run"],
                        "passed": r["passed"],
                        "failures": r["failures"],
                        "baseline_confidence": r["baseline_confidence"],
                        "improved_confidence": r["improved_confidence"],
                        "teaching_file": r["teaching_file"],
                        "duration_ms": r["duration_ms"],
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if not args.quiet:
        print(f"\n=== SUMMARY WRITTEN ===\n{summary_file}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())