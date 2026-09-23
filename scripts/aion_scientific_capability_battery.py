#!/usr/bin/env python3
"""Preregister and run an isolated, reproducible AION capability battery.

This measures bounded causal responsiveness, causal-rule learning, transfer,
outcome-driven repair, and restart retention.  It does not test consciousness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.modules.aion_demo.reflex_grid import _init_state, _step_core
from backend.modules.hexcore.active_causal_discovery_benchmark import (
    run_active_causal_benchmark,
)
from backend.modules.hexcore.cross_domain_causal_transfer_benchmark import (
    run_cross_domain_transfer_benchmark,
)
from backend.modules.hexcore.outcome_driven_causal_evolution_benchmark import (
    run_outcome_evolution_benchmark,
)


MASTER_SEED = 20260812
DIRECTIONS = {
    "up": ((4, 5), "4,5"),
    "down": ((6, 5), "6,5"),
    "left": ((5, 4), "5,4"),
    "right": ((5, 6), "5,6"),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable evidence: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reflex_trial(seed: int, target: str, irrelevant_tag: str) -> dict[str, Any]:
    state = _init_state(seed)
    state.update(
        {
            "position": {"x": 5, "y": 5},
            "world": {},
            "visited": {
                "5,5": 1,
                **{tile: (0 if direction == target else 9) for direction, (_, tile) in DIRECTIONS.items()},
            },
            "steps": 0,
            "run_active": False,
            # This field is deliberately causally irrelevant.
            "scientific_blind_tag": irrelevant_tag,
        }
    )
    before = json.loads(json.dumps(state))
    after = _step_core(state)
    expected_position, expected_tile = DIRECTIONS[target]
    observed_position = (after["position"]["x"], after["position"]["y"])
    return {
        "seed": seed,
        "target": target,
        "expected_tile": expected_tile,
        "observed_tile": after.get("last_tile"),
        "observed_position": list(observed_position),
        "passed": observed_position == expected_position and after.get("last_tile") == expected_tile,
        "before_hash": digest(before),
        "after_hash": digest(after),
    }


def run_reflex_suite(trial_count: int) -> dict[str, Any]:
    rng = random.Random(MASTER_SEED)
    directions = list(DIRECTIONS)
    schedule = [directions[index % len(directions)] for index in range(trial_count)]
    rng.shuffle(schedule)
    trials = []
    negative_controls = []
    for index, target in enumerate(schedule):
        seed = rng.randrange(1, 2_000_000_000)
        primary = reflex_trial(seed, target, f"primary-{index}")
        control = reflex_trial(seed, target, f"changed-only-{index}")
        trials.append(primary)
        negative_controls.append(
            {
                "seed": seed,
                "target": target,
                "same_observed_tile": primary["observed_tile"] == control["observed_tile"],
                "state_hash_changed": primary["before_hash"] != control["before_hash"],
                "passed": (
                    primary["observed_tile"] == control["observed_tile"]
                    and primary["before_hash"] != control["before_hash"]
                ),
            }
        )
    passed = all(item["passed"] for item in trials) and all(
        item["passed"] for item in negative_controls
    )
    return {
        "name": "bounded_causal_responsiveness",
        "trial_count": trial_count,
        "balanced_targets": {direction: schedule.count(direction) for direction in directions},
        "trials": trials,
        "negative_controls": negative_controls,
        "passed": passed,
        "claim_boundary": "Deterministic bounded causal responsiveness only; not awareness or agency.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output_root or (
        REPO_ROOT / "results" / "immutable" / "aion_scientific_capability_battery" / run_id
    )
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"Run directory already exists: {output_root}")

    protocol = {
        "protocol": "aion_scientific_capability_battery_v1",
        "preregistered_at": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "isolation": "Fresh temporary state files; live moonshot state is neither read nor written.",
        "consciousness_claim": False,
        "tests": {
            "bounded_causal_responsiveness": {
                "trials": 24,
                "pass": "24/24 correct interventions and 24/24 causally irrelevant controls invariant",
            },
            "active_causal_discovery": {
                "seeds_per_mode": 20,
                "pass": "All benchmark gates, including hidden-rule change and restart retention",
            },
            "cross_domain_transfer": {
                "audit_episodes": 30,
                "pass": "All benchmark gates across renamed domains and restart retention",
            },
            "outcome_driven_evolution": {
                "development_worlds": 8,
                "sealed_worlds": 10,
                "development_episodes": 24,
                "sealed_episodes": 30,
                "pass": "All gates, including sealed gain, non-regression, promotion, and restart retention",
            },
        },
        "overall_pass": "Every preregistered test passes; no averaging away failures.",
        "interpretation_boundary": (
            "Passing supports bounded learning, adaptation, transfer, repair, and retention claims only. "
            "It is not evidence of subjective experience, consciousness, or unrestricted AGI."
        ),
    }
    protocol["protocol_hash"] = digest(protocol)
    write_new(output_root / "protocol.json", protocol)

    reflex = run_reflex_suite(24)
    write_new(output_root / "bounded_causal_responsiveness.json", reflex)

    causal = run_active_causal_benchmark(
        state_path=output_root / "active_causal_state.json",
        result_path=output_root / "active_causal_discovery.json",
        seeds_per_mode=20,
    )
    transfer = run_cross_domain_transfer_benchmark(
        state_path=output_root / "cross_domain_transfer_state.json",
        result_path=output_root / "cross_domain_transfer.json",
        audit_episodes=30,
    )
    evolution = run_outcome_evolution_benchmark(
        state_path=output_root / "outcome_evolution_state.json",
        result_path=output_root / "outcome_driven_evolution.json",
        development_worlds=8,
        sealed_worlds=10,
        development_episodes=24,
        sealed_episodes=30,
    )

    results = {
        "protocol_hash": protocol["protocol_hash"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "tests": {
            "bounded_causal_responsiveness": bool(reflex.get("passed")),
            "active_causal_discovery": bool(causal.get("passed")),
            "cross_domain_transfer": bool(transfer.get("passed")),
            "outcome_driven_evolution": bool(evolution.get("passed")),
        },
    }
    results["overall_passed"] = all(results["tests"].values())
    results["evidence_hashes"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output_root.glob("*.json"))
        if path.name != "summary.json"
    }
    results["claim_boundary"] = protocol["interpretation_boundary"]
    write_new(output_root / "summary.json", results)
    print(json.dumps({"output_root": str(output_root), **results}, indent=2))
    return 0 if results["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
