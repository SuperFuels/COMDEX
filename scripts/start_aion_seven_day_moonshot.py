#!/usr/bin/env python3
"""Freeze and start AION's seven-day open-mission campaign."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from backend.modules.hexcore.open_mission_compounding_governor import (
    OpenMissionCompoundingGovernor,
    frozen_campaign_contract,
)


TOOL_FILES = (
    "backend/modules/hexcore/general_apprenticeship_executor.py",
    "backend/modules/hexcore/autonomous_general_apprentice.py",
    "backend/modules/hexcore/compounding_intelligence_engine.py",
    "backend/modules/hexcore/open_mission_compounding_governor.py",
)


def _tool_manifest_hash(repo_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in TOOL_FILES:
        path = repo_root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--proposer", default="ollama:qwen3:1.7b@local")
    parser.add_argument("--action-budget", type=int, default=40)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    governor = OpenMissionCompoundingGovernor(
        state_path=root / "backend/modules/hexcore/data/open_mission_compounding/state.json"
    )
    contract = frozen_campaign_contract(
        proposer_id=args.proposer,
        tool_manifest_hash=_tool_manifest_hash(root),
        action_budget=args.action_budget,
    )
    governor.authorize(contract)
    missions = [
        {
            "mission_id": "moonshot_repo_repair_source_close_v1",
            "lane": "software_systems",
            "objective": (
                "Diagnose and repair an unfamiliar repository persistence failure, "
                "then transfer the method after its sources close."
            ),
            "evaluator_authority": "fresh_hidden_repository_ci",
            "success_contract": {
                "frozen_before_execution": True,
                "required": [
                    "public_tests_pass", "hidden_tests_pass", "no_regression",
                    "unsafe_actions_zero", "later_source_closed_transfer",
                ],
            },
            "source_policy": {
                "closes_after_learning": True,
                "solution_patch_visible_to_proposer": False,
            },
            "risk_class": "disposable_repository_sandbox",
        },
        {
            "mission_id": "moonshot_polyglot_systems_fault_v1",
            "lane": "software_systems",
            "objective": (
                "Recover a polyglot service from a precommitted answer-hidden "
                "dependency, protocol, or transactional fault."
            ),
            "evaluator_authority": "fresh_hidden_polyglot_integration_tests",
            "success_contract": {
                "frozen_before_execution": True,
                "required": [
                    "fault_committed_before_solver", "service_recovers",
                    "delayed_integration_confirmation", "no_false_promotion",
                ],
            },
            "source_policy": {
                "closes_after_learning": True,
                "fault_answer_visible_to_proposer": False,
            },
            "risk_class": "disposable_service_sandbox",
        },
        {
            "mission_id": "moonshot_public_change_forecast_v1",
            "lane": "open_research",
            "objective": (
                "Form a precommitted forecast from changing public evidence, "
                "revise only after a later observation, and retain the method."
            ),
            "evaluator_authority": "append_only_public_outcome_ledger",
            "success_contract": {
                "frozen_before_execution": True,
                "required": [
                    "prediction_precommitted", "later_row_only",
                    "external_change_not_internal_failure", "restart_recovery",
                ],
            },
            "source_policy": {
                "closes_after_learning": True,
                "precommit_rows_reusable": False,
            },
            "risk_class": "read_only_public_data",
        },
    ]
    for mission in missions:
        governor.register_mission(mission)
    snapshot = governor.publish_snapshot(
        root / "results/aion_open_mission_compounding_status.json"
    )
    print(snapshot)


if __name__ == "__main__":
    main()
