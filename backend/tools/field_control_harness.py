from __future__ import annotations

import argparse
import asyncio
import copy
import json
import statistics
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> float:
    return time.time()


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _mean(xs: List[float]) -> float:
    return statistics.mean(xs) if xs else 0.0


def _pstdev(xs: List[float]) -> float:
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


class HexCoreHarnessAdapter:
    """
    Thin adapter around your live HexCore runtime.

    Adjust the import path here if needed.
    """

    def __init__(self) -> None:
        from backend.modules.hexcore.hexcore import HexCore

        self.hexcore = HexCore()

    async def run_cycle(
        self,
        input_str: str,
        forced_control: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Runs a single live HexCore cycle.

        Optional forced_control is injected via a temporary override hook.
        If your HexCore uses a different override attribute, change it here.
        """
        if forced_control is not None:
            setattr(self.hexcore, "field_control_override", copy.deepcopy(forced_control))
        else:
            if hasattr(self.hexcore, "field_control_override"):
                setattr(self.hexcore, "field_control_override", None)

        decision, entry = await self.hexcore.run_loop(input_str)
        return {
            "decision": decision,
            "entry": entry,
        }


def choose_forced_control(
    mode: str,
    current_control: Optional[Dict[str, Any]],
    last_entry: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if mode == "baseline_hold":
        return copy.deepcopy(current_control) if current_control else None

    if mode == "apply_proposed":
        if not last_entry:
            return copy.deepcopy(current_control) if current_control else None
        field_operator = last_entry.get("field_operator") or {}
        proposed = ((field_operator.get("proposed_adjustments") or {}).get("proposed_control"))
        if isinstance(proposed, dict) and proposed:
            return copy.deepcopy(proposed)
        return copy.deepcopy(current_control) if current_control else None

    if mode == "bad_perturbation":
        c = copy.deepcopy(current_control) if current_control else {}
        if not c:
            return None
        c["symbolic_temperature"] = min(1.0, _safe_float(c.get("symbolic_temperature"), 0.07) + 0.08)
        c["stabilization_bias"] = max(0.0, _safe_float(c.get("stabilization_bias"), 1.0) - 0.12)
        c["resonance_gain"] = max(0.0, _safe_float(c.get("resonance_gain"), 0.5) - 0.05)
        return c

    raise ValueError(f"Unknown mode: {mode}")


def extract_row(
    *,
    run_id: str,
    mode: str,
    cycle_index: int,
    prompt: str,
    control_before: Optional[Dict[str, Any]],
    forced_control: Optional[Dict[str, Any]],
    result: Dict[str, Any],
) -> Dict[str, Any]:
    entry = result.get("entry") or {}
    symatics_packet = entry.get("symatics_packet") or {}
    raw = symatics_packet.get("raw") or {}
    field_operator = entry.get("field_operator") or {}
    field_actuation = entry.get("field_actuation") or {}
    act_decision = field_actuation.get("decision") or {}
    qqc_summary = entry.get("qqc_summary") or {}

    coherence = _safe_float(entry.get("coherence", symatics_packet.get("coherence")), 0.0)
    entropy = _safe_float(entry.get("psi", symatics_packet.get("entropy")), 0.0)
    delta_phi = _safe_float(entry.get("delta_phi", symatics_packet.get("delta_phi")), 0.0)
    reward = _safe_float(entry.get("reward"), coherence - abs(delta_phi))
    self_awareness = _safe_float(entry.get("self_awareness", symatics_packet.get("self_awareness")), 0.0)
    global_coherence = _safe_float(entry.get("global_coherence", symatics_packet.get("global_coherence")), 0.0)
    phase = _safe_float(entry.get("phi", raw.get("phase")), 0.0)
    resonance = _safe_float(symatics_packet.get("resonance", raw.get("resonance")), 0.0)
    amplitude = _safe_float(symatics_packet.get("amplitude", raw.get("amplitude")), 0.0)
    frequency = _safe_float(symatics_packet.get("frequency", raw.get("frequency")), 0.0)
    stability_score = _safe_float(field_operator.get("stability_score"), 0.0)
    alignment_error = abs(_safe_float(entry.get("alignment_error"), phase - self_awareness))

    field_quality = coherence - entropy - abs(delta_phi)

    applied_control = (
        ((field_actuation.get("apply_result") or {}).get("control"))
        or qqc_summary.get("control_applied")
        or forced_control
        or control_before
    )

    return {
        "ts": _now(),
        "run_id": run_id,
        "mode": mode,
        "cycle_index": cycle_index,
        "prompt": prompt,
        "decision": result.get("decision"),
        "control_before": control_before,
        "forced_control": forced_control,
        "applied_control": applied_control,
        "field_operator_mode": act_decision.get("mode"),
        "field_operator_reason": act_decision.get("reason"),
        "coherence": coherence,
        "entropy": entropy,
        "delta_phi": delta_phi,
        "reward": reward,
        "self_awareness": self_awareness,
        "global_coherence": global_coherence,
        "phase": phase,
        "resonance": resonance,
        "amplitude": amplitude,
        "frequency": frequency,
        "stability_score": stability_score,
        "alignment_error": alignment_error,
        "field_quality": field_quality,
        "observed_regime": symatics_packet.get("observed_regime", raw.get("observed_regime")),
        "predicted_symbol": symatics_packet.get("predicted_symbol", raw.get("predicted_symbol")),
        "raw_entry": entry,
    }


async def run_mode(
    adapter: HexCoreHarnessAdapter,
    *,
    mode: str,
    prompt: str,
    cycles: int,
    output_jsonl: Path,
) -> Dict[str, Any]:
    run_id = f"{mode}-{uuid.uuid4().hex[:10]}"
    rows: List[Dict[str, Any]] = []
    last_entry: Optional[Dict[str, Any]] = None
    current_control: Optional[Dict[str, Any]] = None

    for cycle_index in range(cycles):
        forced_control = choose_forced_control(mode, current_control, last_entry)
        result = await adapter.run_cycle(prompt, forced_control=forced_control)

        entry = result.get("entry") or {}
        if isinstance(entry.get("control"), dict):
            current_control = copy.deepcopy(entry["control"])

        row = extract_row(
            run_id=run_id,
            mode=mode,
            cycle_index=cycle_index,
            prompt=prompt,
            control_before=current_control,
            forced_control=forced_control,
            result=result,
        )
        rows.append(row)
        last_entry = entry

    _write_jsonl(output_jsonl, rows)

    coherence_vals = [_safe_float(r["coherence"]) for r in rows]
    entropy_vals = [_safe_float(r["entropy"]) for r in rows]
    delta_vals = [_safe_float(r["delta_phi"]) for r in rows]
    reward_vals = [_safe_float(r["reward"]) for r in rows]
    fq_vals = [_safe_float(r["field_quality"]) for r in rows]
    stab_vals = [_safe_float(r["stability_score"]) for r in rows]

    hold_count = sum(1 for r in rows if r.get("field_operator_mode") == "hold_current")
    constructive_count = sum(1 for r in rows if str(r.get("observed_regime") or "").lower() == "constructive")

    return {
        "run_id": run_id,
        "mode": mode,
        "cycles": cycles,
        "mean_coherence": _mean(coherence_vals),
        "mean_entropy": _mean(entropy_vals),
        "mean_delta_phi": _mean(delta_vals),
        "mean_reward": _mean(reward_vals),
        "mean_field_quality": _mean(fq_vals),
        "mean_stability_score": _mean(stab_vals),
        "std_coherence": _pstdev(coherence_vals),
        "std_reward": _pstdev(reward_vals),
        "std_field_quality": _pstdev(fq_vals),
        "hold_current_pct": (100.0 * hold_count / cycles) if cycles else 0.0,
        "constructive_pct": (100.0 * constructive_count / cycles) if cycles else 0.0,
    }


async def _amain() -> None:
    parser = argparse.ArgumentParser(description="AION field-control harness")
    parser.add_argument("--prompt", type=str, default="stabilize the field")
    parser.add_argument("--cycles", type=int, default=30)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["baseline_hold", "apply_proposed", "bad_perturbation"],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".runtime/aion_field_control"),
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runs_jsonl = output_dir / "field_control_runs.jsonl"
    summary_json = output_dir / "field_control_summary.json"

    adapter = HexCoreHarnessAdapter()
    summaries: List[Dict[str, Any]] = []

    for mode in args.modes:
        summary = await run_mode(
            adapter,
            mode=mode,
            prompt=args.prompt,
            cycles=args.cycles,
            output_jsonl=runs_jsonl,
        )
        summaries.append(summary)
        print(
            f"[{mode}] "
            f"field_quality={summary['mean_field_quality']:.6f} "
            f"reward={summary['mean_reward']:.6f} "
            f"hold={summary['hold_current_pct']:.2f}%"
        )

    with summary_json.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    print(f"\nWrote:\n  {runs_jsonl}\n  {summary_json}")


if __name__ == "__main__":
    asyncio.run(_amain())