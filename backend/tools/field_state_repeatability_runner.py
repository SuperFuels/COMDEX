from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.tools.field_programs import canonical_field_programs


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log repeatability observations for canonical field programs.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".runtime/aion_field_control/field_state_repeatability.jsonl"),
    )
    parser.add_argument("--operator", type=str, default="Kevin Robinson")
    parser.add_argument("--hardware-mode", type=str, default="direct_scope")
    parser.add_argument("--runs-per-program", type=int, default=3)
    return parser.parse_args()


def prompt_observation(program_id: str, label: str, expected_state: str, expected_scope: str) -> Dict[str, Any]:
    print()
    print("=" * 72)
    print(f"Program: {program_id} | {label}")
    print(f"Expected state: {expected_state}")
    print(f"Expected scope behavior: {expected_scope}")
    print("=" * 72)

    observed_state = input("Observed state label: ").strip() or "unknown"
    observed_scope = input("Observed scope note: ").strip() or "not_recorded"
    observed_pickup = input("Observed pickup note: ").strip() or "not_recorded"
    pass_fail = input("Pass? [y/n]: ").strip().lower()
    notes = input("Extra notes: ").strip()

    return {
        "observed_state": observed_state,
        "observed_scope_note": observed_scope,
        "observed_pickup_note": observed_pickup,
        "pass": pass_fail == "y",
        "notes": notes,
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    programs = canonical_field_programs()

    rows: List[Dict[str, Any]] = []
    for program in programs:
        for run_idx in range(1, args.runs_per_program + 1):
            print(f"\nRun {run_idx}/{args.runs_per_program} for {program.program_id}")
            obs = prompt_observation(
                program.program_id,
                program.label,
                program.expected_state,
                program.expected_scope_behavior,
            )
            row = {
                "ts_utc": _utc_now(),
                "operator": args.operator,
                "hardware_mode": args.hardware_mode,
                "program_id": program.program_id,
                "label": program.label,
                "phase_rad": program.phase_rad,
                "expected_state": program.expected_state,
                "expected_scope_behavior": program.expected_scope_behavior,
                "expected_pickup_behavior": program.expected_pickup_behavior,
                "run_index": run_idx,
                **obs,
            }
            rows.append(row)

    with args.out.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    passed = sum(1 for r in rows if r["pass"])
    print()
    print(f"Wrote: {args.out}")
    print(f"Pass count: {passed}/{len(rows)}")


if __name__ == "__main__":
    main()