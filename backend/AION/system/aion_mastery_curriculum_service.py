#!/usr/bin/env python3
"""Persistent North-Star curriculum and executor-acquisition service."""
from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock

from backend.modules.hexcore.file_locking import acquire_process_lock


_STARTUP_PROCESS_LOCK = None
if __name__ == "__main__":
    _startup_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    _STARTUP_PROCESS_LOCK = acquire_process_lock(
        _startup_root / "backend/modules/hexcore/data/service_locks/mastery_curriculum.lock"
    )
    if _STARTUP_PROCESS_LOCK is None:
        raise SystemExit(0)

from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy
from backend.modules.hexcore.academy_executor_acquisition_worker import (
    AcademyExecutorAcquisitionWorker,
)
from backend.modules.hexcore.governed_intelligence_glyph_consolidation import run as run_glyph_consolidation
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.progressive_competency_executor import ProgressiveCompetencyExecutor
from backend.modules.hexcore.autonomous_progressive_executor_factory import run as run_executor_factory
from backend.modules.hexcore.open_toolchain_progressive_authority import run_acquisition as run_toolchain_acquisition
from backend.modules.hexcore.cross_domain_depth_acceleration import run as run_depth_acceleration
from backend.modules.hexcore.verified_objective_competency_bridge import run as run_objective_competency_bridge
from backend.modules.hexcore.compounding_intelligence_engine import run as run_compounding_intelligence
from backend.modules.hexcore.cross_domain_campaign_execution import run as run_cross_domain_campaigns
from backend.modules.hexcore.autonomous_capability_research_executive import (
    run as run_capability_research_executive,
)
from backend.modules.hexcore.resource_aware_cognitive_routing import run as run_resource_routing
from backend.modules.hexcore.open_cross_domain_authority_factory import run as run_authority_factory
from backend.modules.hexcore.open_authority_disagreement_diagnosis import run as run_disagreement_diagnosis
from backend.modules.hexcore.open_objective_family_invention import run as run_objective_family_invention
from backend.modules.hexcore.experience_compiled_project_intelligence import (
    run as run_experience_compiler,
)
from backend.modules.hexcore.hierarchical_mission_graph import run as run_hierarchical_missions
from backend.modules.hexcore.open_method_language_expansion import run as run_method_expansion
from backend.modules.hexcore.functional_glyph_lexicon import run as run_functional_lexicon
from backend.modules.hexcore.functional_glyph_method_compiler import run as run_functional_method_compiler
from backend.modules.hexcore.autonomous_functional_glyph_induction import (
    run as run_functional_glyph_induction,
)
from backend.modules.hexcore.dual_track_intelligence_portfolio import (
    run as run_dual_track_portfolio,
)
from backend.modules.hexcore.simulator_neutral_embodied_apprenticeship import (
    run as run_embodied_apprenticeship,
)
from backend.modules.hexcore.rgb_belief_state_mujoco_apprenticeship import (
    run as run_rgb_belief_apprenticeship,
)
from backend.modules.hexcore.rgb_contact_occlusion_skill_composition import (
    run as run_rgb_contact_composition,
)
from backend.modules.hexcore.rgb_articulated_sequence_skill import (
    run as run_rgb_articulated_sequence,
)
from backend.modules.hexcore.simulator_disjoint_embodied_scaleup import (
    run as run_simulator_disjoint_scaleup,
)
def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    process_lock = _STARTUP_PROCESS_LOCK or acquire_process_lock(
        repo_root / "backend/modules/hexcore/data/service_locks/mastery_curriculum.lock")
    if process_lock is None:
        return
    status_path = repo_root / "results/aion_mastery_curriculum_service_status.json"
    interval = max(5.0, float(os.getenv("AION_MASTERY_CURRICULUM_INTERVAL", "30")))
    # Live teacher consultation is proposal-only and may be slow or absent.  It
    # must never sit on the critical path of the persistent curriculum loop.
    # Operators can opt in explicitly; the cached deterministic teacher remains
    # available on every cycle.
    live_teacher = os.getenv("AION_MASTERY_LIVE_TEACHER", "0") not in {"0", "false", "False"}
    # Qualify and retain every currently supported family adapter before the
    # persistent loop selects work.  This runs once per service reconstruction;
    # the live executor still verifies every individual learning outcome.
    factory_outcome = run_executor_factory(
        repo_root=repo_root,
        result_path=repo_root / "results/hexcore_autonomous_progressive_executor_factory.json",
        state_path=repo_root / "backend/modules/hexcore/data/progressive_executor_factory/state.json",
    )
    toolchain_outcome = run_toolchain_acquisition(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/open_toolchain_progressive_authority.json",
        result_path=repo_root / "results/hexcore_open_toolchain_progressive_executor_acquisition.json",
    )
    resource_routing_outcome = run_resource_routing(
        result_path=repo_root / "results/hexcore_resource_aware_cognitive_routing.json",
        champion_path=repo_root / "data/aion/canonical_runtime/resource_route_champion.json",
    )
    compounding_outcome = None
    campaign_outcome = None
    executive_outcome = None
    authority_factory_outcome = None
    disagreement_outcome = None
    objective_family_outcome = None
    experience_compiler_outcome = None
    hierarchical_mission_outcome = None
    method_expansion_outcome = None
    dual_track_outcome = None
    embodied_outcome = None
    rgb_belief_outcome = None
    rgb_contact_outcome = None
    rgb_articulated_outcome = None
    simulator_disjoint_outcome = None
    last_compounding_epoch = 0.0
    while True:
        try:
            academy_state_path = repo_root / "backend/modules/hexcore/data/guided_foundation_academy/state.json"
            worker = AcademyExecutorAcquisitionWorker(
                repo_root=repo_root, academy_state_path=academy_state_path,
                state_path=repo_root / "backend/modules/hexcore/data/academy_executor_worker/state.json",
            )
            academy_outcome = None
            worker_outcomes = []
            # A bounded local event loop may close a request, unlock the graph,
            # and compile the next contract in one service wake.  It never
            # spins indefinitely or marks unsupported work as learned.
            for _ in range(4):
                academy = GuidedFoundationAcademy(
                    repo_root=repo_root, state_path=academy_state_path,
                )
                if academy.state.get("primary_academy_complete"):
                    academy_outcome = {
                        "cycle": {"lane": "primary_academy", "action": {"status": "academy_capstone_complete"}},
                        "summary": academy.summary(),
                    }
                    break
                open_requests = [
                    row for row in academy.state.get("executor_requests") or []
                    if row.get("status") == "open"
                ]
                runnable = any(
                    row.get("module_id") in worker.status()["supported_modules"]
                    for row in open_requests
                )
                if runnable:
                    worker_outcome = worker.step()
                    worker_outcomes.append(worker_outcome)
                    if worker_outcome.get("progressed"):
                        academy = GuidedFoundationAcademy(
                            repo_root=repo_root, state_path=academy_state_path,
                        )
                        academy_outcome = academy.step(live_teacher=live_teacher)
                        continue
                    break
                ready_exists = any(
                    row.get("status") == "ready"
                    for row in academy.state.get("modules", {}).values()
                )
                if not open_requests or ready_exists:
                    academy_outcome = academy.step(live_teacher=live_teacher)
                    continue
                worker_outcome = worker.step()
                worker_outcomes.append(worker_outcome)
                break
            academy = GuidedFoundationAcademy(
                repo_root=repo_root, state_path=academy_state_path,
            )
            if academy_outcome is None:
                academy_outcome = {"cycle": {"lane": "executor_acquisition",
                                             "action": worker_outcomes[-1] if worker_outcomes else {"status": "waiting"}},
                                   "summary": academy.summary()}
            competency_outcome = None
            competency_executor_outcome = None
            # The progressive competency ledger supersedes the one-pass broad
            # curriculum after the foundation Academy. Existing contracts are
            # retained as history but no longer define proficiency.
            if academy.state.get("primary_academy_complete"):
                bridge_outcome = run_objective_competency_bridge(
                    repo_root=repo_root,
                    result_path=repo_root / "results/hexcore_verified_objective_competency_bridge.json",
                )
                depth_outcome = run_depth_acceleration(
                    repo_root=repo_root,
                    result_path=repo_root / "results/hexcore_cross_domain_depth_acceleration.json",
                )
                competency = ProgressiveCompetencySystem(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
                )
                competency_executor = ProgressiveCompetencyExecutor(
                    system=competency,
                    state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/executor.json",
                    result_dir=repo_root / "results/progressive_competency",
                )
                # Select or refresh the authoritative active contract first.
                # Then execute that exact contract. A second ledger pass closes
                # successful work or rotates an explicitly blocked subject in
                # the same wake, eliminating hour-long no-progress loops.
                competency_outcome = competency.step()
                competency_executor_outcome = competency_executor.step()
                if (
                    competency_executor_outcome.get("progressed")
                    or competency_executor_outcome.get("status") in {
                        "executor_acquisition_required", "rejected_and_parked",
                    }
                ):
                    competency_outcome = competency.step()
                competency_snapshot = competency.snapshot()
                _atomic_competency = repo_root / "results/aion_progressive_competency_status.json"
                competency_temp = _atomic_competency.with_suffix(".tmp")
                competency_temp.write_text(json.dumps(competency_snapshot, indent=2, sort_keys=True), encoding="utf-8")
                json.loads(competency_temp.read_text(encoding="utf-8"))
                os.replace(competency_temp, _atomic_competency)
                # Publish a truthful checkpoint before the slower compounding
                # and embodied tasks complete. A stale error must not remain
                # visible after the competency transaction has succeeded.
                checkpoint = {
                    "status": "competency_cycle_checkpoint",
                    "academy_outcome": academy_outcome,
                    "progressive_competency": competency_outcome,
                    "progressive_competency_executor": competency_executor_outcome,
                    "progressive_summary": competency_snapshot.get("summary") or {},
                    "updated_at": time.time(),
                    "cycle_complete": False,
                    "next_run_after_seconds": interval,
                }
                checkpoint_temp = status_path.with_suffix(".checkpoint.tmp")
                checkpoint_temp.write_text(json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8")
                json.loads(checkpoint_temp.read_text(encoding="utf-8"))
                os.replace(checkpoint_temp, status_path)
                broad_outcome = {"status": "superseded_by_progressive_competency",
                                 "retained_contracts": True}
            else:
                broad_outcome = {"status": "parked_during_primary_academy",
                                 "retained_contracts": True}
            glyph_result_path = repo_root / "results/hexcore_governed_intelligence_glyph_consolidation.json"
            source_paths = [
                repo_root / "results/hexcore_governed_teacher_python_core_cycle.json",
                repo_root / "results/hexcore_general_apprenticeship_executor.json",
                repo_root / "results/hexcore_real_rust_apprenticeship.json",
                repo_root / "results/hexcore_rust_sql_systems_depth.json",
                repo_root / "results/hexcore_programming_intelligence_closure.json",
                repo_root / "results/hexcore_accelerated_algorithms_apprenticeship.json",
                repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
            ]
            newest_source = max((path.stat().st_mtime for path in source_paths if path.exists()), default=0.0)
            if not glyph_result_path.exists() or glyph_result_path.stat().st_mtime < newest_source:
                glyph = run_glyph_consolidation(
                    repo_root=repo_root,
                    index_path=repo_root / "backend/modules/hexcore/data/intelligence_glyphs/index.json",
                    compressed_path=repo_root / "backend/modules/hexcore/data/intelligence_glyphs/glyphs.json.gz",
                    result_path=glyph_result_path,
                )
                glyph_outcome = {"status": "rebuilt", "passed": glyph["passed"], "gate": glyph["gate"]}
            else:
                glyph_outcome = {"status": "current", "result_path": str(glyph_result_path)}
            functional_lexicon_path = repo_root / "results/hexcore_functional_glyph_lexicon.json"
            functional_compiler_path = repo_root / "results/hexcore_functional_glyph_method_compiler.json"
            functional_sources = [
                repo_root / "results/hexcore_accelerated_algorithms_apprenticeship.json",
                repo_root / "results/hexcore_hierarchical_mission_graph.json",
                repo_root / "results/immutable/aion_competency_reconstruction_failure_receipt.json",
            ]
            newest_functional_source = max((path.stat().st_mtime for path in functional_sources if path.exists()), default=0.0)
            if (not functional_lexicon_path.exists() or not functional_compiler_path.exists()
                    or functional_lexicon_path.stat().st_mtime < newest_functional_source):
                functional_lexicon_outcome = run_functional_lexicon(
                    repo_root=repo_root,
                    store_path=repo_root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
                    index_path=repo_root / "backend/modules/hexcore/data/functional_glyph_lexicon/index.json",
                    result_path=functional_lexicon_path,
                )
                functional_compiler_outcome = run_functional_method_compiler(
                    repo_root=repo_root,
                    store_path=repo_root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
                    result_path=functional_compiler_path,
                    state_path=repo_root / "backend/modules/hexcore/data/functional_glyph_method_compiler/learning.json",
                )
            else:
                functional_lexicon_outcome = json.loads(functional_lexicon_path.read_text(encoding="utf-8"))
                functional_compiler_outcome = json.loads(functional_compiler_path.read_text(encoding="utf-8"))
            induction_path = repo_root / "results/hexcore_autonomous_functional_glyph_induction.json"
            induction_sources = [
                functional_lexicon_path,
                repo_root / "results/hexcore_functional_mastery_memory.json",
                *sorted((repo_root / "backend/modules/hexcore/data/functional_mastery_memory/capsules").glob("*.json")),
            ]
            newest_induction_source = max(
                (path.stat().st_mtime for path in induction_sources if path.exists()), default=0.0
            )
            if not induction_path.exists() or induction_path.stat().st_mtime < newest_induction_source:
                functional_induction_outcome = run_functional_glyph_induction(
                    repo_root=repo_root,
                    store_path=repo_root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
                    capsule_dir=repo_root / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
                    reconstruction_result_path=repo_root / "results/hexcore_functional_mastery_memory.json",
                    result_path=induction_path,
                )
            else:
                functional_induction_outcome = json.loads(induction_path.read_text(encoding="utf-8"))
            # Functional reconstruction is deliberately more expensive than a
            # curriculum tick. Run it periodically and reuse the matched local
            # substrate tournament rather than repeatedly querying models.
            if compounding_outcome is None or time.time() - last_compounding_epoch >= 600.0:
                dual_track_outcome = run_dual_track_portfolio(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/dual_track_intelligence/state.json",
                    result_path=repo_root / "results/hexcore_dual_track_intelligence_portfolio.json",
                )
                embodied_outcome = run_embodied_apprenticeship(
                    repo_root=repo_root,
                    result_path=repo_root / "results/hexcore_simulator_neutral_embodied_apprenticeship.json",
                )
                rgb_result_path = repo_root / "results/hexcore_rgb_belief_state_mujoco_planning.json"
                rgb_source_path = repo_root / "backend/modules/hexcore/rgb_belief_state_mujoco_apprenticeship.py"
                if (not rgb_result_path.exists()
                        or rgb_result_path.stat().st_mtime < rgb_source_path.stat().st_mtime):
                    rgb_belief_outcome = run_rgb_belief_apprenticeship(
                        repo_root=repo_root,
                        result_path=rgb_result_path,
                        state_path=repo_root / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json",
                    )
                else:
                    rgb_belief_outcome = json.loads(rgb_result_path.read_text(encoding="utf-8"))
                contact_result_path = repo_root / "results/hexcore_rgb_contact_occlusion_skill_composition.json"
                contact_source_path = repo_root / "backend/modules/hexcore/rgb_contact_occlusion_skill_composition.py"
                if (not contact_result_path.exists()
                        or contact_result_path.stat().st_mtime < contact_source_path.stat().st_mtime):
                    rgb_contact_outcome = run_rgb_contact_composition(
                        repo_root=repo_root,
                        result_path=contact_result_path,
                        state_path=repo_root / "backend/modules/hexcore/data/rgb_contact_occlusion/state.json",
                        capsule_path=repo_root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_contact_occlusion.json",
                    )
                else:
                    rgb_contact_outcome = json.loads(contact_result_path.read_text(encoding="utf-8"))
                articulated_result_path = repo_root / "results/hexcore_rgb_articulated_sequence_skill.json"
                articulated_source_path = repo_root / "backend/modules/hexcore/rgb_articulated_sequence_skill.py"
                if (not articulated_result_path.exists()
                        or articulated_result_path.stat().st_mtime < articulated_source_path.stat().st_mtime):
                    rgb_articulated_outcome = run_rgb_articulated_sequence(
                        repo_root=repo_root,
                        result_path=articulated_result_path,
                        state_path=repo_root / "backend/modules/hexcore/data/rgb_articulated_sequence/state.json",
                        capsule_path=repo_root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_articulated_sequence.json",
                    )
                else:
                    rgb_articulated_outcome = json.loads(articulated_result_path.read_text(encoding="utf-8"))
                simulator_disjoint_outcome = run_simulator_disjoint_scaleup(
                    repo_root=repo_root,
                    result_path=repo_root / "results/hexcore_simulator_disjoint_embodied_scaleup.json",
                    handoff_path=repo_root / "results/aion_isaac_lab_embodied_handoff.json",
                )
                hierarchical_mission_outcome = run_hierarchical_missions(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/hierarchical_missions/state.json",
                    result_path=repo_root / "results/hexcore_hierarchical_mission_graph.json",
                )
                method_expansion_outcome = run_method_expansion(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/open_method_language_expansion/state.json",
                    registry_path=repo_root / "data/aion/canonical_runtime/method_registry.json",
                    result_path=repo_root / "results/hexcore_open_method_language_expansion.json",
                )
                compounding_outcome = run_compounding_intelligence(
                    repo_root=repo_root,
                    result_path=repo_root / "results/hexcore_compounding_intelligence_engine.json",
                    state_path=repo_root / "backend/modules/hexcore/data/compounding_intelligence/state.json",
                    live_substrates=False,
                )
                campaign_outcome = run_cross_domain_campaigns(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/cross_domain_campaign_execution/state.json",
                    result_path=repo_root / "results/hexcore_cross_domain_campaign_execution.json",
                )
                executive_outcome = run_capability_research_executive(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
                    result_path=repo_root / "results/hexcore_autonomous_capability_research_executive.json",
                )
                authority_factory_outcome = run_authority_factory(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/autonomous_authority_factory/state.json",
                    result_path=repo_root / "results/hexcore_open_cross_domain_authority_factory.json",
                )
                disagreement_outcome = run_disagreement_diagnosis(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/authority_disagreement_diagnosis/state.json",
                    outcome_ledger=repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
                    workspace_root=repo_root / "results/aion_authority_disagreement_diagnostics",
                    result_path=repo_root / "results/hexcore_open_authority_disagreement_diagnosis.json",
                )
                objective_family_outcome = run_objective_family_invention(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/open_objective_family_invention/state.json",
                    workspace_root=repo_root / "results/aion_open_objective_families",
                    result_path=repo_root / "results/hexcore_open_objective_family_invention.json",
                )
                experience_compiler_outcome = run_experience_compiler(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/experience_compiled_project_intelligence/state.json",
                    result_path=repo_root / "results/hexcore_experience_compiled_project_intelligence.json",
                )
                last_compounding_epoch = time.time()
            worker_status = worker.status()
            competency_action = (((competency_outcome or {}).get("cycle") or {}).get("action") or {})
            competency_status = str(competency_action.get("status") or "")
            executor_status = str((competency_executor_outcome or {}).get("status") or "")
            service_state = "stalled" if worker_status["stalled"] else (
                "blocked_executor_unavailable" if worker_status["status"] == "blocked_no_verified_executor"
                else "competency_executor_acquisition" if executor_status == "executor_acquisition_required"
                else "competency_rotated_after_executor_failure" if executor_status == "rejected_and_parked"
                else "competency_executor_retrying" if executor_status == "executor_rejected"
                else "competency_stalled" if competency_status.startswith("stalled")
                else "competency_retention_wait" if competency_status == "waiting_elapsed_retention"
                else "competency_waiting_for_executor" if competency_status == "executor_required"
                else "competency_curriculum_active" if competency_status == "curriculum_contract_created"
                else "active"
            )
            status = {"status": service_state, "academy_outcome": academy_outcome,
                      "executor_worker": {"outcomes": worker_outcomes, **worker_status},
                      "progressive_competency": competency_outcome,
                      "progressive_competency_executor": competency_executor_outcome,
                      "progressive_executor_registry": (
                          competency_executor.registry.summary(subjects=competency.state["subjects"])
                          if academy.state.get("primary_academy_complete") else {}
                      ),
                      "progressive_executor_factory": {
                          "passed": factory_outcome.get("passed") is True,
                          "gate": factory_outcome.get("gate") or {},
                          "procedure_id": factory_outcome.get("procedure_id"),
                      },
                      "open_toolchain_acquisition": {
                          "passed": toolchain_outcome.get("passed") is True,
                          "gate": toolchain_outcome.get("gate") or {},
                          "procedure_id": toolchain_outcome.get("procedure_id"),
                      },
                      "cross_domain_depth_acceleration": {
                          "passed": depth_outcome.get("passed") is True,
                          "gate": depth_outcome.get("gate") or {},
                          "procedure_id": depth_outcome.get("procedure_id"),
                      } if academy.state.get("primary_academy_complete") else {},
                      "verified_objective_competency_bridge": {
                          "passed": bridge_outcome.get("passed") is True,
                          "gate": bridge_outcome.get("gate") or {},
                          "procedure_id": bridge_outcome.get("procedure_id"),
                      } if academy.state.get("primary_academy_complete") else {},
                      "broad_curriculum": broad_outcome, "glyph_consolidation": glyph_outcome,
                      "functional_glyph_lexicon": {
                          "passed": bool(functional_lexicon_outcome.get("passed")),
                          "status": functional_lexicon_outcome.get("status"),
                          "gate": functional_lexicon_outcome.get("gate") or {},
                      },
                      "functional_glyph_method_compiler": {
                          "passed": bool(functional_compiler_outcome.get("passed")),
                          "status": functional_compiler_outcome.get("status"),
                          "gate": functional_compiler_outcome.get("gate") or {},
                      },
                      "autonomous_functional_glyph_induction": {
                          "passed": bool(functional_induction_outcome.get("passed")),
                          "status": functional_induction_outcome.get("status"),
                          "gate": functional_induction_outcome.get("gate") or {},
                      },
                      "compounding_intelligence": {
                          "passed": bool((compounding_outcome or {}).get("passed")),
                          "status": (compounding_outcome or {}).get("status"),
                          "gate": (compounding_outcome or {}).get("gate") or {},
                          "next_compounding_action": (compounding_outcome or {}).get("next_compounding_action"),
                      },
                      "cross_domain_campaign_execution": {
                          "passed": bool((campaign_outcome or {}).get("passed")),
                          "status": (campaign_outcome or {}).get("status"),
                          "gate": (campaign_outcome or {}).get("gate") or {},
                          "next_action": (campaign_outcome or {}).get("next_action"),
                      },
                      "autonomous_capability_research_executive": {
                          "passed": bool((executive_outcome or {}).get("passed")),
                          "status": (executive_outcome or {}).get("status"),
                          "gate": (executive_outcome or {}).get("gate") or {},
                          "next_action": (executive_outcome or {}).get("next_action"),
                      },
                      "open_cross_domain_authority_factory": {
                          "passed": bool((authority_factory_outcome or {}).get("passed")),
                          "status": (authority_factory_outcome or {}).get("status"),
                          "gate": (authority_factory_outcome or {}).get("gate") or {},
                          "next_action": (authority_factory_outcome or {}).get("next_action"),
                      },
                      "open_authority_disagreement_diagnosis": {
                          "passed": bool((disagreement_outcome or {}).get("passed")),
                          "status": (disagreement_outcome or {}).get("status"),
                          "gate": (disagreement_outcome or {}).get("gate") or {},
                      },
                      "open_objective_family_invention": {
                          "passed": bool((objective_family_outcome or {}).get("passed")),
                          "status": (objective_family_outcome or {}).get("status"),
                          "gate": (objective_family_outcome or {}).get("gate") or {},
                          "invented_family": (objective_family_outcome or {}).get("invented_family"),
                      },
                      "experience_compiled_project_intelligence": {
                          "passed": bool((experience_compiler_outcome or {}).get("passed")),
                          "status": (experience_compiler_outcome or {}).get("status"),
                          "gate": (experience_compiler_outcome or {}).get("gate") or {},
                      },
                      "hierarchical_mission_graph": {
                          "passed": bool((hierarchical_mission_outcome or {}).get("passed")),
                          "status": (hierarchical_mission_outcome or {}).get("status"),
                          "gate": (hierarchical_mission_outcome or {}).get("gate") or {},
                      },
                      "open_method_language_expansion": {
                          "passed": bool((method_expansion_outcome or {}).get("passed")),
                          "status": (method_expansion_outcome or {}).get("status"),
                          "gate": (method_expansion_outcome or {}).get("gate") or {},
                          "method": (method_expansion_outcome or {}).get("method"),
                      },
                      "resource_aware_cognitive_routing": {
                          "passed": bool(resource_routing_outcome.get("passed")),
                          "status": resource_routing_outcome.get("status"),
                          "gate": resource_routing_outcome.get("gate") or {},
                      },
                      "dual_track_intelligence": {
                          "passed": bool((dual_track_outcome or {}).get("passed")),
                          "status": (dual_track_outcome or {}).get("status"),
                          "gate": (dual_track_outcome or {}).get("gate") or {},
                          "allocation": (dual_track_outcome or {}).get("allocation") or {},
                      },
                      "simulator_neutral_embodied_apprenticeship": {
                          "passed": bool((embodied_outcome or {}).get("passed")),
                          "status": (embodied_outcome or {}).get("status"),
                          "gate": (embodied_outcome or {}).get("gate") or {},
                      },
                      "rgb_belief_state_embodied_apprenticeship": {
                          "passed": bool((rgb_belief_outcome or {}).get("passed")),
                          "status": (rgb_belief_outcome or {}).get("status"),
                          "gate": (rgb_belief_outcome or {}).get("gate") or {},
                      },
                      "rgb_contact_occlusion_skill_composition": {
                          "passed": bool((rgb_contact_outcome or {}).get("passed")),
                          "status": (rgb_contact_outcome or {}).get("status"),
                          "gate": (rgb_contact_outcome or {}).get("gate") or {},
                          "stored_skill_capsule": (rgb_contact_outcome or {}).get("stored_skill_capsule") or {},
                      },
                      "rgb_articulated_sequence_skill": {
                          "passed": bool((rgb_articulated_outcome or {}).get("passed")),
                          "status": (rgb_articulated_outcome or {}).get("status"),
                          "gate": (rgb_articulated_outcome or {}).get("gate") or {},
                          "stored_skill_capsule": (rgb_articulated_outcome or {}).get("stored_skill_capsule") or {},
                      },
                      "simulator_disjoint_embodied_scaleup": simulator_disjoint_outcome or {},
                      "updated_at": time.time(), "next_run_after_seconds": interval}
        except Exception as error:
            status = {"status": "error", "error": type(error).__name__,
                      "detail": str(error), "traceback": traceback.format_exc()[-4000:],
                      "updated_at": time.time(), "next_run_after_seconds": interval}
        temporary = status_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, status_path)
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
