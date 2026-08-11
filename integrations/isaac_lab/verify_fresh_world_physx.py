#!/usr/bin/env python3
"""Compare independent fresh-world executions and authorize a tournament."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def replay_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return row["arm_id"], row["episode"], row["seed"]


def verify(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_rows = {replay_key(row): row for row in first.get("children", [])}
    second_rows = {replay_key(row): row for row in second.get("children", [])}
    same_keys = bool(first_rows) and first_rows.keys() == second_rows.keys()
    comparisons = {}
    if same_keys:
        for key in sorted(first_rows):
            a, b = first_rows[key], second_rows[key]
            comparisons["|".join(map(str, key))] = {
                field: a.get(field) == b.get(field)
                for field in (
                    "initial_observation_sha256", "initial_component_sha256",
                    "observation_chain_sha256",
                    "action_chain_sha256", "outcome_chain_sha256",
                )
            }
    isolation = all(
        receipt.get("fresh_world_verified")
        and receipt.get("audit", {}).get("single_episode_per_process")
        and not receipt.get("audit", {}).get("sequential_world_reuse")
        for receipt in (first, second)
    )
    exact = same_keys and bool(comparisons) and all(
        all(fields.values()) for fields in comparisons.values()
    )
    passed = isolation and exact
    return {
        "schema_version": "aion.physx.fresh_world_reproducibility_audit.v1",
        "passed": passed,
        "fresh_world_isolation_verified": isolation,
        "same_precommitted_executions": same_keys,
        "exact_causal_replays": exact,
        "comparisons": comparisons,
        "policy_tournament_authorized": passed,
        "promotion_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("first")
    parser.add_argument("second")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(json.loads(Path(args.first).read_text()), json.loads(Path(args.second).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
