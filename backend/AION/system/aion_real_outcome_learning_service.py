#!/usr/bin/env python3
"""Long-lived bridge from committed campaign outcomes into AION learning."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

from backend.modules.hexcore.file_locking import acquire_process_lock
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock


_STARTUP_PROCESS_LOCK = None
if __name__ == "__main__":
    # The configured LaunchAgent is the canonical owner. An unrelated orphaned
    # copy must opt in explicitly instead of racing that supervisor for its lock.
    launchd_owner = os.getenv("XPC_SERVICE_NAME") == "com.tessaris.aion.outcome-learning"
    if (os.getppid() == 1 and not launchd_owner
            and os.getenv("AION_ALLOW_ORPHANED_OUTCOME_SERVICE", "0") != "1"):
        raise SystemExit(0)
    _startup_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    _STARTUP_PROCESS_LOCK = acquire_process_lock(
        _startup_root / "backend/modules/hexcore/data/service_locks/real_outcome_learning.lock"
    )
    if _STARTUP_PROCESS_LOCK is None:
        raise SystemExit(0)

from backend.modules.hexcore.continuous_real_outcome_learning import run_once
from backend.modules.hexcore.cross_domain_consequence_repair import run_once as close_repair_loop
from backend.modules.hexcore.prospective_cross_domain_outcome_campaign import run_cycle as run_prospective_cycle
from backend.modules.hexcore.owner_valued_delayed_work_campaign import run_once as run_owner_work
from backend.modules.hexcore.open_useful_objective_acquisition import run_once as run_open_objectives
from backend.modules.hexcore.situated_cross_domain_project_engine import run as run_situated_project
from backend.modules.hexcore.autonomous_general_apprentice_evidence_registry import build_registry as build_aga_registry
from backend.modules.hexcore.autonomous_cognitive_code_challenger import run_once as run_cognitive_code_challenger
from backend.modules.hexcore.week_scale_retention_challenge import run as run_week_retention_challenge
from backend.modules.hexcore.shortlist_free_remote_authority_acquisition import close_later_challenge
from backend.modules.hexcore.cross_domain_remote_authority_transfer import close_later_challenges
from backend.modules.hexcore.multistep_institutional_intelligence import (
    close_later_challenges as close_institutional_challenges,
)
from backend.modules.hexcore.open_information_action_invention import (
    close_later_challenges as close_open_action_challenges,
)
from backend.modules.hexcore.recursive_action_language_expansion import (
    close_later_challenges as close_recursive_action_challenges,
)
from backend.modules.hexcore.open_micro_operation_invention import (
    close_later_challenges as close_micro_operation_challenges,
)
from backend.modules.hexcore.open_property_language_invention import (
    close_later_challenges as close_property_language_challenges,
)
from backend.modules.hexcore.open_critic_objective_invention import (
    close_later_challenges as close_critic_objective_challenges,
)
from backend.modules.hexcore.open_diagnostic_experiment_invention import (
    close_later_challenges as close_diagnostic_experiment_challenges,
)
from backend.modules.hexcore.open_measurement_operation_invention import (
    close_later_challenges as close_measurement_operation_challenges,
)
from backend.modules.hexcore.autonomous_upstream_change_scientist import run_once as run_upstream_scientist
from backend.modules.hexcore.autonomous_goal_consequence_arbiter import run as run_goal_arbiter
from backend.modules.hexcore.experience_compiled_project_intelligence import (
    run_prospective as run_prospective_experience_compiler,
)
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


_BENIGN_CHILD_WARNING = (
    "MallocStackLogging: can't turn off malloc stack logging because it was not enabled."
)


def _is_benign_child_log_line(line: str) -> bool:
    return _BENIGN_CHILD_WARNING in line


def _install_bounded_log_filter(path: Path, *, maximum_bytes: int = 5 * 1024 * 1024) -> None:
    """Filter known macOS subprocess noise while retaining actionable output."""
    if os.name != "posix" or os.getenv("AION_FILTER_CHILD_RUNTIME_NOISE", "1") in {"0", "false", "False"}:
        return
    read_fd, write_fd = os.pipe()
    os.dup2(write_fd, 1)
    os.dup2(write_fd, 2)
    os.close(write_fd)

    def rotate() -> None:
        for index in range(2, 0, -1):
            source = path.with_name(path.name + f".{index}")
            target = path.with_name(path.name + f".{index + 1}")
            if source.exists():
                os.replace(source, target)
        if path.exists():
            os.replace(path, path.with_name(path.name + ".1"))

    def drain() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size >= maximum_bytes:
            rotate()
        output = path.open("ab", buffering=0)
        try:
            with os.fdopen(read_fd, "rb", buffering=0) as stream:
                for raw in iter(stream.readline, b""):
                    line = raw.decode("utf-8", "replace")
                    if _is_benign_child_log_line(line):
                        continue
                    if output.tell() + len(raw) > maximum_bytes:
                        output.close()
                        rotate()
                        output = path.open("ab", buffering=0)
                    output.write(raw)
        finally:
            output.close()

    threading.Thread(target=drain, name="aion-outcome-log-filter", daemon=True).start()
    sys.stdout = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8", errors="replace")
    sys.stderr = os.fdopen(os.dup(2), "w", buffering=1, encoding="utf-8", errors="replace")


def _write_service_status(path: Path, *, cycle: int, phase: str) -> None:
    """Publish liveness independently of the slower completed-outcome file."""
    payload = {
        "schema_version": "aion.real_outcome_learning_service_status.v1",
        "status": "running",
        "cycle": cycle,
        "phase": phase,
        "pid": os.getpid(),
        "updated_at": time.time(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    _install_bounded_log_filter(repo_root / "logs/aion_real_outcome_learning_service.log")
    process_lock = _STARTUP_PROCESS_LOCK or acquire_process_lock(
        repo_root / "backend/modules/hexcore/data/service_locks/real_outcome_learning.lock")
    if process_lock is None:
        return
    interval = max(30.0, float(os.getenv("AION_OUTCOME_LEARNING_INTERVAL", "300")))
    status_path = repo_root / "results/aion_real_outcome_learning_service_status.json"
    cycle = 0

    def mark(phase: str) -> None:
        _write_service_status(status_path, cycle=cycle, phase=phase)

    while True:
        cycle += 1
        governed = governed_standalone_task(
            repo_root=repo_root,
            service_id="outcome_learning",
            task_text=(
                "Ingest independently observed outcomes, close due delayed challenges, "
                "repair cross-domain consequence errors and update reusable experience"
            ),
            operation_id=f"outcome_learning_cycle_{cycle}",
        )
        governed.__enter__()
        mark("continuous_outcome_ingestion")
        run_once(
            workspace_root=repo_root / "backend/modules/hexcore/data/continuous_real_outcome_learning",
            ledger_path=repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl",
            result_path=repo_root / "results/hexcore_continuous_real_outcome_learning.json",
        )
        mark("cross_domain_consequence_repair")
        close_repair_loop(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/cross_domain_consequence_repair/state.json",
            result_path=repo_root / "results/hexcore_cross_domain_consequence_repair.json",
        )
        mark("prospective_outcome_campaign")
        run_prospective_cycle(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/prospective_cross_domain_outcome/state.json",
            commitment_ledger=repo_root / "results/hexcore_prospective_cross_domain_commitments.jsonl",
            outcome_ledger=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
            result_path=repo_root / "results/hexcore_prospective_cross_domain_outcome.json",
        )
        mark("owner_valued_delayed_work")
        run_owner_work(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/owner_valued_delayed_work/state.json",
            public_outcome_ledger=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
            workspace_root=repo_root / "results/aion_owner_valued_work",
            result_path=repo_root / "results/hexcore_owner_valued_delayed_work.json",
        )
        mark("open_objective_acquisition")
        run_open_objectives(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json",
            public_outcome_ledger=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
            workspace_root=repo_root / "results/aion_open_useful_objectives",
            result_path=repo_root / "results/hexcore_open_useful_objectives.json",
        )
        # Cheap prospective boundary: select the verification program while
        # the specialist outcome is still hidden. Full historical compilation
        # remains on the slower mastery-service cadence.
        mark("prospective_experience_compilation")
        run_prospective_experience_compiler(
            repo_root=repo_root,
            result_path=repo_root / "results/hexcore_experience_compiled_project_intelligence.json",
        )
        mark("situated_cross_domain_project")
        run_situated_project(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json",
            outcome_ledger=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
            workspace_root=repo_root / "results/aion_situated_cross_domain_projects",
            result_path=repo_root / "results/hexcore_situated_cross_domain_project.json",
        )
        mark("cognitive_code_challenger")
        run_cognitive_code_challenger(
            repo_root=repo_root,
            objective_state_path=repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json",
            state_path=repo_root / "backend/modules/hexcore/data/cognitive_code_challenger/state.json",
            private_workspace=repo_root / "backend/modules/hexcore/data/cognitive_code_challenger/private",
            policy_path=repo_root / "data/aion/canonical_runtime/cognitive_route_champion.json",
            result_path=repo_root / "results/hexcore_later_confirmed_cognitive_code_improvement.json",
        )
        mark("retention_and_delayed_authorities")
        run_week_retention_challenge(
            repo_root=repo_root,
            result_path=repo_root / "results/hexcore_week_scale_retention_challenge.json",
        )
        close_later_challenge(
            state_path=repo_root / "backend/modules/hexcore/data/shortlist_free_remote_authority/state.json",
            result_path=repo_root / "results/hexcore_shortlist_free_remote_authority_acquisition.json",
        )
        close_later_challenges(
            state_path=repo_root / "backend/modules/hexcore/data/cross_domain_remote_authority_transfer/state.json",
            result_path=repo_root / "results/hexcore_cross_domain_remote_authority_transfer.json",
        )
        close_institutional_challenges(
            state_path=repo_root / "backend/modules/hexcore/data/multistep_institutional_intelligence/state.json",
            result_path=repo_root / "results/hexcore_multistep_institutional_intelligence.json",
        )
        close_open_action_challenges(
            state_path=repo_root / "backend/modules/hexcore/data/open_information_action_invention/state.json",
            result_path=repo_root / "results/hexcore_open_information_action_invention.json",
        )
        close_recursive_action_challenges(
            state_path=repo_root / "backend/modules/hexcore/data/recursive_action_language_expansion/state.json",
            result_path=repo_root / "results/hexcore_recursive_action_language_expansion.json",
        )
        close_micro_operation_challenges(
            atom_registry_path=repo_root / "backend/modules/hexcore/data/recursive_action_runtime/atom_registry.json",
            state_path=repo_root / "backend/modules/hexcore/data/open_micro_operation_invention/state.json",
            result_path=repo_root / "results/hexcore_open_micro_operation_invention.json",
        )
        close_property_language_challenges(
            atom_registry_path=repo_root / "backend/modules/hexcore/data/recursive_action_runtime/atom_registry.json",
            state_path=repo_root / "backend/modules/hexcore/data/open_property_language_invention/state.json",
            result_path=repo_root / "results/hexcore_open_property_language_invention.json",
        )
        close_critic_objective_challenges(
            atom_registry_path=repo_root / "backend/modules/hexcore/data/recursive_action_runtime/atom_registry.json",
            state_path=repo_root / "backend/modules/hexcore/data/open_critic_objective_invention/state.json",
            result_path=repo_root / "results/hexcore_open_critic_objective_invention.json",
        )
        close_diagnostic_experiment_challenges(
            atom_registry_path=repo_root / "backend/modules/hexcore/data/recursive_action_runtime/atom_registry.json",
            state_path=repo_root / "backend/modules/hexcore/data/open_diagnostic_experiment_invention/state.json",
            result_path=repo_root / "results/hexcore_open_diagnostic_experiment_invention.json",
        )
        close_measurement_operation_challenges(
            atom_registry_path=repo_root / "backend/modules/hexcore/data/recursive_action_runtime/atom_registry.json",
            state_path=repo_root / "backend/modules/hexcore/data/open_measurement_operation_invention/state.json",
            result_path=repo_root / "results/hexcore_open_measurement_operation_invention.json",
        )
        run_upstream_scientist(
            repo_root=repo_root,
            ledger_path=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
            state_path=repo_root / "backend/modules/hexcore/data/autonomous_upstream_change_scientist/state.json",
            output_root=repo_root / "results/aion_autonomous_upstream_investigations",
            result_path=repo_root / "results/hexcore_autonomous_upstream_change_scientist.json",
        )
        run_goal_arbiter(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/autonomous_goal_consequence_arbiter/state.json",
            result_path=repo_root / "results/hexcore_autonomous_goal_consequence_arbiter.json",
        )
        build_aga_registry(
            repo_root,
            repo_root / "results/hexcore_autonomous_general_apprentice_evidence_registry.json",
            repo_root / "results/hexcore_autonomous_general_apprentice_evidence_history.jsonl",
        )
        governed.finish({"status": "outcome_learning_cycle_complete", "cycle": cycle}, verified=False)
        governed.__exit__(None, None, None)
        mark("waiting_for_next_cycle")
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
