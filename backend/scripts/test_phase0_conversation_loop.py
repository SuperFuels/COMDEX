#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

OUT_DIR = Path("data/logs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_INTENTS = {"answer", "ask", "clarify"}
EXPECTED_PHASE = "phase0_minimal_composer"
DEFAULT_TOPIC = "AION Phase 0 conversation"


@dataclass
class RunResult:
    ok: bool
    run_idx: int
    duration_ms: float
    api_latency_ms: float | None
    composed_len: int
    parsed_confidence: float | None
    teaching_path: str
    error: str | None = None


def _assert_ready(ready: dict[str, Any], *, require_all: bool = False) -> None:
    assert isinstance(ready, dict), "ready check must return a dict"
    assert ready.get("status") == "ready", f"unexpected ready status: {ready.get('status')!r}"
    assert ready.get("required_ok") is True, "required services are not ready"

    if require_all:
        assert ready.get("all_ok") is True, "all services are not ready"

    services = ready.get("services")
    assert isinstance(services, list) and services, "ready check missing services[]"

    required_names = {"API", "TCFK"}
    seen_required_ok: dict[str, bool] = {}

    for svc in services:
        assert isinstance(svc, dict), "service entry must be dict"
        name = svc.get("name")
        ok = svc.get("ok")
        assert isinstance(name, str) and name, "service missing name"
        assert isinstance(ok, bool), f"service {name!r} missing boolean ok"

        if svc.get("required") is True:
            assert ok is True, f"required service not ok: {name}"
            seen_required_ok[name] = True

    missing = required_names - set(seen_required_ok.keys())
    # Only enforce if your ready check includes those names (it does in your logs)
    assert not missing, f"missing expected required services in ready check: {sorted(missing)}"


def _extract_confidence_from_text(text: str) -> float | None:
    m = re.search(r"\bconfidence\s+is\s+([0-9]*\.?[0-9]+)\b", text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    return value


def _assert_composer(composed: Any) -> tuple[str, dict[str, Any], float | None]:
    # Expect object with .text .metadata .confidence
    assert hasattr(composed, "text"), "composed response missing .text"
    assert hasattr(composed, "metadata"), "composed response missing .metadata"
    assert hasattr(composed, "confidence"), "composed response missing .confidence"

    text = composed.text
    meta = composed.metadata
    confidence_obj = composed.confidence

    assert isinstance(text, str), "composed.text must be str"
    assert len(text.strip()) >= 80, f"response too short/empty (len={len(text.strip())})"

    # Quality floor for current phase-0 template
    assert "confidence" in text.lower(), "response missing confidence mention"
    assert "What I think I know:" in text, "response missing facts section"
    assert "I need help with:" in text, "response missing unresolved section"

    # Metadata checks
    assert isinstance(meta, dict), "composed.metadata must be dict"
    assert meta.get("phase") == EXPECTED_PHASE, f"bad phase: {meta.get('phase')!r}"

    intent = meta.get("intent")
    assert intent in ALLOWED_INTENTS, f"bad intent: {intent!r}"

    for key in ("fact_count", "goal_count", "unresolved_count"):
        assert key in meta, f"metadata missing {key}"
        assert isinstance(meta[key], int), f"metadata {key} must be int"

    assert meta["fact_count"] >= 1, "fact_count too low"
    assert meta["goal_count"] >= 1, "goal_count too low"
    assert meta["unresolved_count"] >= 0, "unresolved_count invalid"

    # Confidence checks (object + text)
    assert isinstance(confidence_obj, (int, float)), "composed.confidence must be numeric"
    assert 0.0 <= float(confidence_obj) <= 1.0, f"composed.confidence out of range: {confidence_obj}"

    parsed_conf = _extract_confidence_from_text(text)
    if parsed_conf is not None:
        assert 0.0 <= parsed_conf <= 1.0, f"text confidence out of range: {parsed_conf}"

    return text, meta, parsed_conf


def _assert_teaching_session_file(path: Path, *, expected_user_text: str, expected_topic: str) -> dict[str, Any]:
    assert path.exists(), f"teaching session file missing: {path}"
    raw = path.read_text(encoding="utf-8")
    assert raw.strip(), f"teaching session file empty: {path}"

    data = json.loads(raw)
    assert isinstance(data, dict), "teaching session JSON root must be dict"

    # Flexible schema validation (don't overfit exact implementation)
    root_keys = set(data.keys())
    possible_turns_keys = ("turns", "teaching_turns", "records")
    turns_key = next((k for k in possible_turns_keys if k in data), None)

    # Root minimums
    assert any(k in root_keys for k in ("teacher_id", "teacher", "teacher_type")), "missing teacher identity fields"
    assert any(k in root_keys for k in ("objective", "goal")), "missing objective/goal field"
    assert turns_key is not None, f"missing turns list (expected one of {possible_turns_keys})"

    turns = data[turns_key]
    assert isinstance(turns, list) and len(turns) >= 1, "teaching session turns must be non-empty list"

    t0 = turns[0]
    assert isinstance(t0, dict), "first turn must be dict"

    # Validate first turn matches what we just wrote (best-effort, schema-tolerant)
    if "user_input" in t0:
        assert t0["user_input"] == expected_user_text, "user_input mismatch in teaching session"
    if "topic" in t0:
        assert isinstance(t0["topic"], str) and t0["topic"], "turn topic missing/empty"

    correction = t0.get("correction")
    assert correction is not None, "turn missing correction object"
    assert isinstance(correction, dict), "turn.correction must be dict"
    assert "corrected_response" in correction and correction["corrected_response"], "correction missing corrected_response"
    assert "target_confidence" in correction, "correction missing target_confidence"

    tc = correction["target_confidence"]
    assert isinstance(tc, (int, float)), "target_confidence must be numeric"
    assert 0.0 <= float(tc) <= 1.0, f"target_confidence out of range: {tc}"

    return data


def _build_knowledge_state() -> AionKnowledgeState:
    return AionKnowledgeState(
        intent="answer",
        topic=DEFAULT_TOPIC,
        confidence=0.38,  # intentionally low to force "learning" style output
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


def _run_once(run_idx: int, *, verbose: bool, require_all: bool, unique_output: bool) -> RunResult:
    t0 = time.perf_counter()
    user_text = "Explain what AION is building next."

    try:
        # 1) Ready check
        ready = run_ready_check()
        if verbose:
            print("=== READY CHECK ===")
            print(json.dumps(ready, indent=2))
        _assert_ready(ready, require_all=require_all)

        # Extract API latency if present
        api_latency_ms = None
        for svc in ready.get("services", []):
            if isinstance(svc, dict) and svc.get("name") == "API":
                lat = svc.get("latency_ms")
                if isinstance(lat, (int, float)):
                    api_latency_ms = float(lat)
                break

        # 2) Minimal composer test
        composer = MinimalResponseComposer()
        ks = _build_knowledge_state()
        composed = composer.compose(user_text=user_text, ks=ks)

        text, meta, parsed_conf = _assert_composer(composed)

        if verbose:
            print("\n=== COMPOSED RESPONSE ===")
            print(text)
            print(json.dumps(meta, indent=2))

        # 3) Simulate a teacher correction session
        session = new_teaching_session(
            teacher_type="human",
            teacher_id="kevin",
            mode="manual",
            objective="Teach AION to explain roadmap simply and confidently",
            metadata={"phase": "phase0", "test_script": "test_phase0_conversation_loop.py", "run_idx": run_idx},
        )

        correction = CorrectionRecord(
            aion_original_response=text,
            corrected_response=(
                "AION already has the core runtime. Next, we are building conversation orchestration, "
                "skill runtime unification, and learning loops on top of the existing stack."
            ),
            correction_reason="Original response was honest but too hesitant and indirect for a roadmap explanation.",
            concept_label="roadmap_explanation_simple",
            target_confidence=validate_target_confidence(0.72),
            tags=["phase0", "d-lang", "roadmap", "response-clarity"],
            notes="Keep child-like honesty, but improve structure and directness.",
        )

        turn = TeachingTurn(
            turn_id="turn_001",
            user_input=user_text,
            inferred_intent="roadmap_explanation",
            topic="AION next build layers",
            aion_response=text,
            aion_confidence=float(composed.confidence),
            correction=correction,
            accepted_as_is=False,
            teaching_notes="Good honesty. Need stronger summary sentence first.",
        )

        session.add_turn(turn)

        if unique_output:
            out_file = OUT_DIR / f"phase0_teaching_session_sample_run{run_idx:03d}.json"
        else:
            out_file = OUT_DIR / "phase0_teaching_session_sample.json"

        out_file.write_text(session.to_json(), encoding="utf-8")

        if verbose:
            print(f"\n=== TEACHING SESSION WRITTEN ===\n{out_file}")

        _assert_teaching_session_file(out_file, expected_user_text=user_text, expected_topic=DEFAULT_TOPIC)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return RunResult(
            ok=True,
            run_idx=run_idx,
            duration_ms=duration_ms,
            api_latency_ms=api_latency_ms,
            composed_len=len(text),
            parsed_confidence=parsed_conf,
            teaching_path=str(out_file),
            error=None,
        )

    except Exception as e:  # broad on purpose for test harness
        duration_ms = (time.perf_counter() - t0) * 1000.0
        if verbose:
            print(f"\n❌ RUN {run_idx} FAILED: {e}")
        return RunResult(
            ok=False,
            run_idx=run_idx,
            duration_ms=duration_ms,
            api_latency_ms=None,
            composed_len=0,
            parsed_confidence=None,
            teaching_path="",
            error=str(e),
        )


def _print_summary(results: list[RunResult]) -> None:
    print("\n=== SUMMARY ===")
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    failed = total - passed
    print(json.dumps({"runs": total, "passed": passed, "failed": failed}, indent=2))

    if not results:
        return

    durations = [r.duration_ms for r in results]
    print(
        f"Duration ms  min={min(durations):.2f}  "
        f"max={max(durations):.2f}  "
        f"avg={statistics.mean(durations):.2f}"
    )

    api_latencies = [r.api_latency_ms for r in results if r.api_latency_ms is not None]
    if api_latencies:
        print(
            f"API latency ms min={min(api_latencies):.2f}  "
            f"max={max(api_latencies):.2f}  "
            f"avg={statistics.mean(api_latencies):.2f}"
        )

    confs = [r.parsed_confidence for r in results if r.parsed_confidence is not None]
    if confs:
        print(
            f"Parsed confidence min={min(confs):.2f}  "
            f"max={max(confs):.2f}  "
            f"avg={statistics.mean(confs):.2f}"
        )

    failed_runs = [r for r in results if not r.ok]
    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            print(f" - run {r.run_idx}: {r.error}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase-0 AION conversation loop test harness with assertions and summary stats."
    )
    p.add_argument("--runs", type=int, default=1, help="Number of runs to execute (default: 1)")
    p.add_argument(
        "--require-all",
        action="store_true",
        help="Require all services (not just required services) to be ready",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary/errors (suppress per-run JSON dumps)",
    )
    p.add_argument(
        "--unique-output",
        action="store_true",
        help="Write one teaching session JSON per run instead of overwriting the same file",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failed run",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    assert args.runs >= 1, "--runs must be >= 1"

    results: list[RunResult] = []
    verbose = not args.quiet

    for i in range(1, args.runs + 1):
        if verbose and args.runs > 1:
            print(f"\n===== RUN {i}/{args.runs} =====")
        result = _run_once(
            i,
            verbose=verbose,
            require_all=args.require_all,
            unique_output=args.unique_output,
        )
        results.append(result)

        if not result.ok and args.fail_fast:
            break

    _print_summary(results)

    any_fail = any(not r.ok for r in results)
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())