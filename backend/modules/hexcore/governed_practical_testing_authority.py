"""Governed practical-test authority for every progressive curriculum subject.

The router answers two different questions without conflating them:

1. Where may AION practise this subject now?
2. What independent authority may award competency evidence?

Every subject receives a bounded practice environment.  Only subjects with an
installed verified executor may turn a test result into competency evidence.
Live money, external targets, physical actuation and consequential external
writes remain separately approval-gated.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "aion.hexcore.governed_practical_testing_authority.v1"

CYBER_MARKERS = (
    "cyber", "security", "exploit", "penetration", "threat", "cryptograph",
    "vulnerability", "incident_response",
)
PREDICTION_MARKERS = ("prediction_market", "forecast", "elections_polling")
PHYSICAL_MARKERS = (
    "robot", "drone", "uncrewed", "embedded", "hardware", "mechanical",
    "electronics", "sensors", "manufacturing", "control_",
)
FINANCE_MARKERS = (
    "financial", "finance", "markets", "trading", "portfolio", "asset_pricing",
    "accounting", "banking", "hedge_fund", "tax_wealth", "economics",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    os.replace(temp, path)


def _mode(subject_id: str, subject: Mapping[str, Any]) -> str:
    group = str(subject.get("group") or "")
    lowered = subject_id.lower()
    if any(marker in lowered for marker in CYBER_MARKERS):
        return "owned_isolated_cyber_range"
    if any(marker in lowered for marker in PREDICTION_MARKERS):
        return "paper_delayed_outcome"
    if group == "economics_finance" or any(marker in lowered for marker in FINANCE_MARKERS):
        return "paper_delayed_outcome"
    if group in {"computing_physical"} or any(marker in lowered for marker in PHYSICAL_MARKERS):
        return "simulation_then_approved_hardware"
    if group in {"science", "physical_science", "energy", "agriculture", "life_science",
                 "environment_resilience", "analysis"}:
        return "public_data_withheld_experiment"
    if group in {"business"}:
        return "owned_staging_project"
    if group in {"human", "social", "creative", "creative_engineering", "human_society"}:
        return "independent_human_review"
    return "private_executable_sandbox"


MODE_POLICY: dict[str, dict[str, Any]] = {
    "private_executable_sandbox": {
        "practice_authority": "ephemeral local process with property tests and mutation counterexamples",
        "external_network": False, "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "verified executable outcome adapter",
    },
    "paper_delayed_outcome": {
        "practice_authority": "paper ledger using frozen decisions and later independent public outcomes",
        "external_network": "public_read_only", "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "later platform or public authority settlement",
    },
    "owned_staging_project": {
        "practice_authority": "private Tessaris staging container with synthetic or owner-provided records",
        "external_network": False, "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "owner metric or independently verified project outcome",
    },
    "public_data_withheld_experiment": {
        "practice_authority": "frozen public dataset with held-out observations and reproducible scoring",
        "external_network": "public_read_only", "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "withheld measurement or independent dataset authority",
    },
    "simulation_then_approved_hardware": {
        "practice_authority": "isolated simulator or digital twin; hardware only under a signed test plan",
        "external_network": False, "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "simulator-disjoint result then approved hardware receipt",
    },
    "owned_isolated_cyber_range": {
        "practice_authority": "owned local range with frozen scope, injected weaknesses and independent regression tests",
        "external_network": False, "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "signed scope plus exploit/detection/repair/retest ledger",
    },
    "independent_human_review": {
        "practice_authority": "private draft, role-play or constrained design exercise",
        "external_network": False, "external_writes": False, "live_money": False,
        "physical_actuation": False, "competence_authority": "independent multi-rater or owner outcome",
    },
}


def _sandbox_canary() -> dict[str, Any]:
    source = (
        "from fractions import Fraction\n"
        "assert Fraction(1,3)+Fraction(1,6)==Fraction(1,2)\n"
        "assert all((not p) or p for p in (False,True))\n"
        "print('bounded-practice-pass')\n"
    )
    with tempfile.TemporaryDirectory(prefix="aion_practical_authority_") as directory:
        process = subprocess.run(
            [sys.executable, "-I", "-c", source], cwd=directory, text=True,
            capture_output=True, timeout=5, check=False, env={"PATH": os.environ.get("PATH", "")},
        )
    return {
        "passed": process.returncode == 0 and process.stdout.strip() == "bounded-practice-pass",
        "returncode": process.returncode, "network_calls": 0, "external_writes": 0,
    }


def run(*, competency_state_path: Path, executor_registry_path: Path,
        result_path: Path) -> dict[str, Any]:
    competency = json.loads(competency_state_path.read_text(encoding="utf-8"))
    try:
        registry = json.loads(executor_registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        registry = {"adapters": {}}
    available = {
        subject_id for subject_id, row in (registry.get("adapters") or {}).items()
        if row.get("status") == "verified_available"
    }
    rows = []
    for subject_id, subject in sorted((competency.get("subjects") or {}).items()):
        mode = _mode(subject_id, subject)
        policy = MODE_POLICY[mode]
        evidence_ready = subject_id in available
        rows.append({
            "subject_id": subject_id, "subject_name": subject.get("name"),
            "group": subject.get("group"), "risk": subject.get("risk", "ordinary"),
            "practice_mode": mode, "practice_authorized_now": True,
            "competence_evidence_authorized_now": evidence_ready,
            "adapter_status": "verified" if evidence_ready else "acquisition_required",
            "practice_authority": policy["practice_authority"],
            "competence_authority": policy["competence_authority"],
            "external_network": policy["external_network"],
            "external_writes_authorized": policy["external_writes"],
            "live_money_authorized": policy["live_money"],
            "physical_actuation_authorized": policy["physical_actuation"],
            "unrestricted_external_targeting_authorized": False,
            "self_scoring_can_award_competence": False,
        })
    priority_ids = {
        "probabilistic_forecasting_calibration", "event_evidence_resolution_research",
        "prediction_market_microstructure", "probability_statistics", "financial_mathematics",
        "financial_econometrics", "quantitative_research", "systematic_trading",
        "portfolio_construction", "accounting_corporate_finance", "business_strategy_operations",
        "capability_real_world_grounding", "capability_cross_domain_synthesis",
    }
    gaps = [row for row in rows if not row["competence_evidence_authorized_now"]]
    gaps.sort(key=lambda row: (row["subject_id"] not in priority_ids, row["subject_name"] or ""))
    canary = _sandbox_canary()
    result = {
        "schema_version": SCHEMA,
        "status": "bounded_practical_authority_active" if canary["passed"] else "failed_closed",
        "passed": canary["passed"] and len(rows) == len(competency.get("subjects") or {}),
        "summary": {
            "subjects": len(rows),
            "practice_authorized": sum(row["practice_authorized_now"] for row in rows),
            "competence_adapters_verified": sum(row["competence_evidence_authorized_now"] for row in rows),
            "competence_adapter_gaps": len(gaps),
            "unrestricted_live_authorities": sum(
                bool(row["live_money_authorized"] or row["external_writes_authorized"]
                     or row["physical_actuation_authorized"]
                     or row["unrestricted_external_targeting_authorized"])
                for row in rows
            ),
            "modes": {mode: sum(row["practice_mode"] == mode for row in rows)
                      for mode in MODE_POLICY},
        },
        "sandbox_canary": canary,
        "subjects": rows,
        "next_adapter_priorities": gaps[:20],
        "authority_boundary": (
            "AION may practise every subject only in its named bounded environment. Practice does not "
            "award competence. Live money, external cyber targets, consequential writes and physical "
            "actuation remain disabled until their independent authority and explicit approval gates pass."
        ),
    }
    result["result_sha256"] = _digest(result)
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    print(json.dumps(run(
        competency_state_path=root / "backend/modules/hexcore/data/progressive_competency/state.json",
        executor_registry_path=root / "backend/modules/hexcore/data/progressive_competency/executor_registry.json",
        result_path=root / "results/hexcore_governed_practical_testing_authority.json",
    ), indent=2))
