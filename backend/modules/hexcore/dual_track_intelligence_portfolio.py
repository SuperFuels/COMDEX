"""Persistent 70/30 practical and embodied intelligence portfolio.

This is a control plane, not a competency award.  It converts the owner's
resource allocation into committed, inspectable missions and asks the existing
mission/capability authority whether each mission may execute or must first
close a learning gap.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.mission_capability_action_harness import (
    MissionCapabilityActionHarness,
)
from backend.modules.hexcore.progressive_competency_system import LEVEL_INDEX


PROCEDURE_ID = "procedure_dual_track_practical_embodied_portfolio_v1"
ALLOCATION = {"practical_apprenticeship": 7, "embodied_physical": 3}


PRACTICAL_MISSIONS: tuple[dict[str, Any], ...] = (
    {
        "mission_id": "practical_secure_service",
        "objective": "Build and test an unfamiliar secure software service with transactional storage, failure recovery, and observable operations.",
        "authority": "fresh repository tests, adversarial checks, and executable service outcomes",
    },
    {
        "mission_id": "practical_public_data",
        "objective": "Investigate a changing public dataset, form a falsifiable forecast, and revise the analysis after a later independently published observation.",
        "authority": "official public-data publication and later observation",
    },
    {
        "mission_id": "practical_formal_reasoning",
        "objective": "Solve an unfamiliar mathematical or algorithmic problem and construct a machine-checkable witness plus hostile counterexamples.",
        "authority": "independent recomputation and property checker",
    },
    {
        "mission_id": "practical_evidence_synthesis",
        "objective": "Research a technical decision across conflicting documents and produce a provenance-complete recommendation with explicit uncertainty.",
        "authority": "exact source spans, contradiction checks, and later source revision",
    },
    {
        "mission_id": "practical_product_business",
        "objective": "Turn an unfamiliar customer problem into a prioritised product plan, measurable experiment, budget model, and go or no-go decision.",
        "authority": "precommitted metrics and later usage or market evidence",
    },
    {
        "mission_id": "practical_security_review",
        "objective": "Threat-model an unfamiliar application, discover exploitable assumptions, and verify a minimal repair without weakening legitimate behaviour.",
        "authority": "executable attack cases, regression tests, and security scanner",
    },
    {
        "mission_id": "practical_cross_domain_system",
        "objective": "Plan and build a useful application that combines software, data analysis, evidence research, project management, and delayed operational measurement.",
        "authority": "independent component tests and later integrated outcome",
    },
)

EMBODIED_MISSIONS: tuple[dict[str, Any], ...] = (
    {
        "mission_id": "embodied_system_identification",
        "objective": "Discover unknown gravity, actuation, damping, and inertia through safe diagnostic interventions in an unfamiliar physical environment.",
        "authority": "MuJoCo-owned hidden dynamics and committed prediction error",
    },
    {
        "mission_id": "embodied_closed_loop_control",
        "objective": "Learn a closed-loop physical controller that reaches a target safely under unfamiliar mass and gravity.",
        "authority": "MuJoCo trajectory, safety envelope, and terminal task score",
    },
    {
        "mission_id": "embodied_transfer",
        "objective": "Transfer an acquired physical method to source-disjoint dynamics and abstain when observations cannot identify a safe action.",
        "authority": "sealed MuJoCo worlds, cold control, and out-of-distribution test",
    },
)


def _canonical_digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _contract(row: Mapping[str, Any], *, lane: str,
              harness: MissionCapabilityActionHarness) -> dict[str, Any]:
    mission = {
        "goal_id": row["mission_id"],
        "objective": row["objective"],
    }
    readiness = harness.evaluate(mission, register_learning=False)
    precommit = {
        "mission_id": row["mission_id"],
        "lane": lane,
        "objective": row["objective"],
        "independent_authority": row["authority"],
        "readiness_decision": readiness["decision"],
        "required_subjects": [item["subject_id"] for item in readiness.get("requirements") or []],
        "success_contract": [
            "define observable success before action",
            "use a private or sandboxed execution surface",
            "retain negative as well as positive evidence",
            "award competence only from an independent outcome",
        ],
        "ambient_authority_expansion": False,
    }
    return {
        **precommit,
        "precommitment_digest": _canonical_digest(precommit),
        "capability_readiness": readiness,
        "status": (
            "ready_for_governed_execution"
            if readiness["decision"] in {"execute", "execute_with_strong_verification"}
            else "learning_or_contract_acquisition_required"
        ),
    }


def run(*, repo_root: Path,
        state_path: Path | None = None,
        result_path: Path | None = None,
        activate_learning: bool = True) -> dict[str, Any]:
    """Create or reconstruct one exact ten-slot 70/30 portfolio generation."""
    root = repo_root.resolve()
    state_path = state_path or root / "backend/modules/hexcore/data/dual_track_intelligence/state.json"
    result_path = result_path or root / "results/hexcore_dual_track_intelligence_portfolio.json"
    previous = _load(state_path)
    harness = MissionCapabilityActionHarness(repo_root=root)
    practical = [_contract(row, lane="practical_apprenticeship", harness=harness)
                 for row in PRACTICAL_MISSIONS]
    embodied = [_contract(row, lane="embodied_physical", harness=harness)
                for row in EMBODIED_MISSIONS]
    portfolio = practical + embodied
    learning_dispatch: dict[str, Any] = {"status": "no_learning_dispatch_required"}
    if activate_learning:
        blocked_practical = [
            row for row in practical
            if row["status"] == "learning_or_contract_acquisition_required"
            and row.get("capability_readiness", {}).get("requirements")
        ]
        if blocked_practical:
            selected = min(
                blocked_practical,
                key=lambda row: min(
                    LEVEL_INDEX.get(str(req.get("overall_level")), 0)
                    for req in row["capability_readiness"]["requirements"]
                ),
            )
            weakest = min(
                selected["capability_readiness"]["requirements"],
                key=lambda req: (
                    LEVEL_INDEX.get(str(req.get("overall_level")), 0),
                    str(req.get("subject_id")),
                ),
            )
            harness.system.prioritize_for_mission(
                subject_id=str(weakest["subject_id"]),
                mission=str(selected["objective"]),
                evidence=f"dual_track_portfolio:{selected['precommitment_digest']}",
            )
            learning_dispatch = {
                "status": "progressive_learning_prioritised",
                "mission_id": selected["mission_id"],
                "subject_id": weakest["subject_id"],
                "reason": "lowest_evidenced_capability_blocking_practical_work",
            }
    portfolio_digest = _canonical_digest({"allocation": ALLOCATION, "portfolio": portfolio})
    generation = int(previous.get("generation") or 0)
    if previous.get("portfolio_digest") != portfolio_digest:
        generation += 1
    state = {
        "schema_version": "aion.dual_track_intelligence.v1",
        "procedure_id": PROCEDURE_ID,
        "generation": max(1, generation),
        "allocation": ALLOCATION,
        "portfolio_digest": portfolio_digest,
        "portfolio": portfolio,
        "learning_dispatch": learning_dispatch,
        "updated_at": time.time(),
    }
    _atomic_json(state_path, state)
    counts = {
        lane: sum(item["lane"] == lane for item in portfolio)
        for lane in ALLOCATION
    }
    gate = {
        "portfolio_objectives": len(portfolio),
        "practical_objectives": counts["practical_apprenticeship"],
        "embodied_objectives": counts["embodied_physical"],
        "exact_70_30_allocation": counts == ALLOCATION,
        "precommitments_complete": all(bool(item["precommitment_digest"]) for item in portfolio),
        "independent_authorities_declared": all(bool(item["independent_authority"]) for item in portfolio),
        "ambient_authority_expansions": sum(bool(item["ambient_authority_expansion"]) for item in portfolio),
        "ready_now": sum(item["status"] == "ready_for_governed_execution" for item in portfolio),
        "learning_first": sum(item["status"] != "ready_for_governed_execution" for item in portfolio),
        "practical_learning_dispatch_active": learning_dispatch["status"] == "progressive_learning_prioritised",
    }
    passed = (
        gate["exact_70_30_allocation"]
        and gate["precommitments_complete"]
        and gate["independent_authorities_declared"]
        and gate["ambient_authority_expansions"] == 0
    )
    result = {
        **state,
        "passed": passed,
        "status": "PORTFOLIO_CONTROL_PLANE_PROMOTED" if passed else "REJECTED",
        "gate": gate,
        "claim_boundary": (
            "The 70/30 resource portfolio is executable and persistent; its missions are not "
            "counted as learned until their independent outcome contracts close."
        ),
    }
    _atomic_json(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root), indent=2, sort_keys=True))
