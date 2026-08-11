"""Fail-closed comparison of two independently started PhysX receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def verify(first: dict, second: dict) -> dict:
    fields = ("contract_sha256", "environment_id", "seed", "outcomes", "policy_summary")
    exact = {field: first.get(field) == second.get(field) for field in fields}
    chains = {
        name: first.get("logs", {}).get(name) == second.get("logs", {}).get(name)
        for name in ("observation_chain_sha256", "action_chain_sha256", "outcome_chain_sha256")
    }
    audits = all(
        receipt.get("audit", {}).get("completed_without_failure")
        and receipt.get("audit", {}).get("deterministic_execution_requested")
        and receipt.get("determinism", {}).get("physx_enhanced_determinism")
        and receipt.get("determinism", {}).get("rtx_deterministic_requested")
        for receipt in (first, second)
    )
    passed = audits and all(exact.values()) and all(chains.values())
    return {
        "schema_version": "aion.physx.determinism_audit.v1",
        "passed": passed,
        "exact_fields": exact,
        "exact_chains": chains,
        "determinism_audits_present": audits,
        "promotion_authority": False,
        "policy_tournament_authorized": passed,
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
