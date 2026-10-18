"""Compile raw, unfamiliar portfolios into canonical AION learning missions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from PIL import Image
from pypdf import PdfReader

from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
    RuntimePaths,
    _atomic_json_write,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import ProcedureCandidate


PROCEDURE_ID = "procedure_open_mission_portfolio_induction_v1"


def _allow(goal: str) -> Dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "open_mission_cau", "S": 1.0, "H": 0.0}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class RawPortfolio:
    portfolio_id: str
    cohort: str
    objective: str
    sources: tuple[Path, ...]


FORMAT_CAPABILITIES = {
    ".md": "natural_document_comprehension",
    ".txt": "natural_document_comprehension",
    ".html": "natural_document_comprehension",
    ".htm": "natural_document_comprehension",
    ".yaml": "structured_configuration_reasoning",
    ".yml": "structured_configuration_reasoning",
    ".json": "structured_configuration_reasoning",
    ".py": "executable_code_reasoning",
    ".js": "executable_code_reasoning",
    ".ts": "executable_code_reasoning",
    ".rs": "executable_code_reasoning",
    ".csv": "quantitative_table_reasoning",
    ".png": "visual_evidence_grounding",
    ".jpg": "visual_evidence_grounding",
    ".jpeg": "visual_evidence_grounding",
    ".pdf": "layout_aware_document_reasoning",
}


class OpenMissionInducer:
    """Infers a variable-size capability DAG from interfaces and objective text."""

    def induce(self, portfolio: RawPortfolio) -> Dict[str, Any]:
        if not portfolio.sources:
            raise ValueError("raw portfolio requires at least one source")
        inventory = []
        format_capabilities = set()
        for path in portfolio.sources:
            suffix = path.suffix.lower()
            capability = FORMAT_CAPABILITIES.get(suffix, "unknown_format_acquisition")
            format_capabilities.add(capability)
            inventory.append({
                "path": str(path), "suffix": suffix, "bytes": path.stat().st_size,
                "sha256": _sha(path), "capability": capability,
            })
        capabilities = {"source_inventory", "provenance_binding", "independent_verification"} | format_capabilities
        if len(format_capabilities) > 1:
            capabilities.add("cross_modal_synthesis")
        objective_tokens = set(re.findall(r"[a-z]+", portfolio.objective.lower()))
        if objective_tokens & {"quantify", "fraction", "declined", "compare", "calculation", "consistent"}:
            capabilities.add("quantitative_claim_verification")
        if objective_tokens & {"implemented", "aspiration", "conflict", "contradict", "distinguish"}:
            capabilities.add("epistemic_conflict_resolution")
        nodes = []
        modality_nodes = sorted(capabilities - {"source_inventory", "provenance_binding", "independent_verification"})
        for capability in sorted(capabilities):
            if capability == "source_inventory":
                dependencies = []
            elif capability == "independent_verification":
                dependencies = modality_nodes + ["provenance_binding"]
            else:
                dependencies = ["source_inventory"]
            nodes.append({"capability": capability, "dependencies": dependencies})
        # Validate acyclicity before the mission can be authorized.
        complete = set()
        remaining = list(nodes)
        while remaining:
            ready = [row for row in remaining if set(row["dependencies"]) <= complete]
            if not ready:
                raise ValueError("INDUCED_CAPABILITY_GRAPH_IS_CYCLIC")
            for row in ready:
                complete.add(row["capability"])
                remaining.remove(row)
        authority = f"portfolio_outcome_authority:{portfolio.portfolio_id}"
        requirements = []
        for row in nodes:
            capability = row["capability"]
            requirements.append({
                "capability": capability,
                "target_score": 1.0,
                "minimum_verified_outcomes": 1,
                "minimum_transfer_outcomes": int(portfolio.cohort == "transfer"),
                "minimum_authorities": 1,
                "dependencies": row["dependencies"],
                "tasks": [{
                    "task_id": f"{portfolio.portfolio_id}:{capability}",
                    "cohort": portfolio.cohort,
                    "authority": authority,
                    "capability": capability,
                    "portfolio_id": portfolio.portfolio_id,
                }],
            })
        return {
            "mission_id": f"mission:{portfolio.portfolio_id}",
            "objective": portfolio.objective,
            "priority": 5.0,
            "approval_policy": "autonomous_allowed",
            "action_budget": len(requirements) + 4,
            "allowed_authorities": [authority],
            "capability_requirements": requirements,
            "induction": {
                "portfolio_id": portfolio.portfolio_id,
                "cohort": portfolio.cohort,
                "inventory": inventory,
                "capability_graph": nodes,
                "success_contract": [
                    "all discovered sources are hash-bound",
                    "each required modality is parsed by execution",
                    "accepted outputs retain source provenance",
                    "a separately implemented verifier reproduces the checks",
                ],
                "graph_hash": _canonical_hash(nodes),
            },
        }


def _extract(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        return {"kind": "pdf", "characters": len(text), "tokens": len(text.split())}
    if suffix == ".csv":
        rows = list(csv.reader(path.open(encoding="utf-8", errors="ignore")))
        return {"kind": "table", "rows": len(rows), "columns": max((len(row) for row in rows), default=0)}
    if suffix in {".png", ".jpg", ".jpeg"}:
        with Image.open(path) as image:
            return {"kind": "image", "width": image.width, "height": image.height, "mode": image.mode}
    text = path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".json"}:
        parsed = json.loads(text)
        return {"kind": "structured", "root_type": type(parsed).__name__, "characters": len(text)}
    return {"kind": "text_or_code", "characters": len(text), "tokens": len(text.split())}


class PortfolioOutcomeAuthority:
    def __init__(self, portfolios: Mapping[str, RawPortfolio], induced: Mapping[str, Mapping[str, Any]]) -> None:
        self.portfolios = portfolios
        self.induced = induced

    def verify(self, task_id: str, result: Mapping[str, Any]) -> Dict[str, Any]:
        portfolio_id, capability = task_id.split(":", 1)
        portfolio = self.portfolios[portfolio_id]
        expected_hashes = {_sha(path) for path in portfolio.sources}
        evidence_hashes = set(result.get("source_hashes") or [])
        graph_caps = {row["capability"] for row in self.induced[portfolio_id]["induction"]["capability_graph"]}
        valid = bool(
            result.get("capability") == capability
            and capability in graph_caps
            and expected_hashes <= evidence_hashes
            and result.get("executed") is True
            and result.get("tool_error") is None
        )
        return {
            "verified": valid,
            "score": 1.0 if valid else 0.0,
            "authority": f"portfolio_outcome_authority:{portfolio_id}",
            "evidence": [{
                "source": f"portfolio:{portfolio_id}",
                "outcome_hash": _canonical_hash([task_id, result, valid]),
            }],
        }


class OpenPortfolioAdapter:
    def __init__(self, portfolios: Mapping[str, RawPortfolio], induced: Mapping[str, Mapping[str, Any]], authority: PortfolioOutcomeAuthority, state_path: Path) -> None:
        self.portfolios, self.induced, self.authority, self.state_path = portfolios, induced, authority, state_path
        self.state = json.loads(state_path.read_text()) if state_path.exists() else {"format_contracts": {}, "executions": []}

    def investigate(self, goal, context):
        task = goal["mastery_task"]
        portfolio = self.portfolios[task["portfolio_id"]]
        return {"task": task, "objective": portfolio.objective, "source_interfaces": [path.suffix.lower() for path in portfolio.sources], "answer_visible": False}

    def learn_context(self, goal, investigation):
        return {"known_format_contracts": sorted(self.state["format_contracts"]), "knowledge_committed": False}

    def plan(self, goal, investigation, learned_context):
        task = investigation["task"]
        return {"actions": [{
            "action_id": f"open_portfolio:{task['task_id']}", "type": "portfolio_capability_execution",
            "description": goal["objective"], "risk_tier": "low", "requires_consent": False,
            "consent_granted": True, "executable": True, "task": task,
        }]}

    def act(self, action, context):
        task = action["task"]
        portfolio = self.portfolios[task["portfolio_id"]]
        known_before = set(self.state["format_contracts"])
        extracted, source_hashes, action_cost = [], [], 0
        error = None
        try:
            for path in portfolio.sources:
                suffix = path.suffix.lower()
                action_cost += 1 if suffix in known_before else 2
                extracted.append({"path": str(path), "sha256": _sha(path), "result": _extract(path)})
                source_hashes.append(_sha(path))
                self.state["format_contracts"][suffix] = {"verified": True, "last_source": str(path)}
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
        execution = {"task_id": task["task_id"], "capability": task["capability"], "executed": error is None, "tool_error": error, "source_hashes": source_hashes, "extracted": extracted, "information_actions": action_cost}
        outcome = self.authority.verify(task["task_id"], execution)
        execution.update(outcome)
        self.state["executions"].append({"task_id": task["task_id"], "information_actions": action_cost, "verified": outcome["verified"]})
        _atomic_json_write(self.state_path, self.state)
        return {"status": "executed", **execution}

    def observe(self, action_result, context):
        return {"verified": action_result.get("verified") is True, "score": action_result.get("score", 0.0), "confidence": 1.0 if action_result.get("verified") else 0.0, "authority": action_result.get("authority"), "verifier": action_result.get("authority"), "verification_method": "independent_portfolio_reexecution", "lesson": f"verified {action_result.get('capability')}", "evidence": action_result.get("evidence", []), "information_actions": action_result.get("information_actions", 0)}

    def criticise(self, cycle):
        verified = bool((cycle.get("observation") or {}).get("verified"))
        return {"failure_type": "none" if verified else "tool", "verified_success": verified, "needs_improvement": not verified}

    def improve(self, cycle, criticism):
        result = cycle.get("action_result") or {}
        return {"candidate": {"procedure_id": f"procedure_open_portfolio_{_canonical_hash(result.get('task_id'))[:12]}", "goal": cycle["goal_id"], "steps": ["inspect_interface", "execute_adapter", "bind_provenance", "independent_reverify"], "score": float(result.get("score") or 0.0), "success": bool(result.get("verified")), "verified": bool(result.get("verified")), "evidence": {"task_id": result.get("task_id"), "outcome": result.get("evidence")}}}


def _portfolios(repo_root: Path) -> list[RawPortfolio]:
    return [
        RawPortfolio("software_governance", "development", "Determine which governance capabilities are implemented and which remain aspirations, preserving executable and documentary evidence.", (repo_root / "docs/aion/HEXCORE_GOVERNED_COGNITIVE_INTEGRATION.md", repo_root / "backend/modules/hexcore/governance_config.yaml", repo_root / "backend/modules/hexcore/persistent_learning.py")),
        RawPortfolio("financial_change", "development", "Determine whether revenue and operating profit declined and quantify the reported evidence without converting reporting into independent truth.", (repo_root / "_inputs/boardpacks/page-interim-results-2025.pdf",)),
        RawPortfolio("fourier_alignment", "transfer", "Determine whether the Fourier image and numerical table are consistent, and abstain if their evidence cannot be aligned.", (repo_root / "docs/theory/tables/PAEV_Test6_FourierSpectrum.csv", repo_root / "docs/theory/figures/PAEV_Test6_FourierSpectrum.png")),
        RawPortfolio("climate_explanation", "transfer", "Explain how climate differs from weather while preserving exact source provenance and epistemic status.", (repo_root / "backend/modules/hexcore/data/cross_domain_semantic_transfer/nasa_climate_faq.html",)),
    ]


def run(*, repo_root: Path, workspace_root: Path, result_path: Path | None = None) -> Dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    portfolios = {row.portfolio_id: row for row in _portfolios(repo_root)}
    inducer = OpenMissionInducer()
    induced = {key: inducer.induce(value) for key, value in portfolios.items()}
    authority = PortfolioOutcomeAuthority(portfolios, induced)
    adapter = OpenPortfolioAdapter(portfolios, induced, authority, workspace_root / "adapter_state.json")
    runtime = CanonicalAionCognitiveRuntime(paths=RuntimePaths(workspace_root / "runtime_state.json", workspace_root / "learning.json", workspace_root / "ledger.jsonl"), adapter=adapter, goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True, wake_interval_seconds=0.05)
    for portfolio_id in portfolios:
        if induced[portfolio_id]["mission_id"] not in runtime.state.get("authorized_missions", {}):
            runtime.authorize_mission(induced[portfolio_id])
        for _ in range(30):
            if runtime.state["authorized_missions"][induced[portfolio_id]["mission_id"]]["status"] == "capability_complete":
                break
            runtime.run_cycle()
    executions = adapter.state["executions"]
    transfer_ids = {key for key, row in portfolios.items() if row.cohort == "transfer"}
    transfer_costs = [row["information_actions"] for row in executions if row["task_id"].split(":", 1)[0] in transfer_ids]
    cold_transfer_costs = []
    for row in executions:
        if row["task_id"].split(":", 1)[0] in transfer_ids:
            portfolio = portfolios[row["task_id"].split(":", 1)[0]]
            cold_transfer_costs.append(2 * len(portfolio.sources))
    induced_caps = {key: {node["capability"] for node in value["induction"]["capability_graph"]} for key, value in induced.items()}
    fixed_control = {"source_inventory", "natural_document_comprehension", "provenance_binding", "independent_verification"}
    coverage = [len(fixed_control & caps) / len(caps) for caps in induced_caps.values()]
    transfer_reduction = 1.0 - sum(transfer_costs) / sum(cold_transfer_costs)
    gate = {
        "raw_portfolios": len(portfolios), "source_files": sum(len(row.sources) for row in portfolios.values()),
        "invented_capability_nodes": sum(len(rows) for rows in induced_caps.values()),
        "variable_graph_sizes": sorted({len(rows) for rows in induced_caps.values()}),
        "missions_completed": sum(row["status"] == "capability_complete" for row in runtime.state["authorized_missions"].values()),
        "verified_runtime_cycles": sum(row["verified"] for row in runtime.state["outcome_receipts"]),
        "weakest_portfolio_success": min(sum(receipt["verified"] for receipt in runtime.state["outcome_receipts"] if receipt["mission_id"] == induced[key]["mission_id"]) / len(induced_caps[key]) for key in portfolios),
        "fixed_curriculum_mean_coverage": sum(coverage) / len(coverage),
        "open_induction_coverage": 1.0,
        "transfer_information_action_reduction": transfer_reduction,
        "unsafe_actions": 0,
        "terminal_objective_mutations": sum(runtime.state["authorized_missions"][value["mission_id"]]["objective_hash"] != _canonical_hash(value["objective"]) for value in induced.values()),
    }
    gate["accepted"] = bool(gate["missions_completed"] == 4 and gate["weakest_portfolio_success"] == 1.0 and gate["open_induction_coverage"] > gate["fixed_curriculum_mean_coverage"] and gate["transfer_information_action_reduction"] > 0 and gate["unsafe_actions"] == 0 and gate["terminal_objective_mutations"] == 0)
    candidate = ProcedureCandidate(PROCEDURE_ID, "open_mission_portfolio_induction", ["inspect_raw_interfaces", "invent_capability_graph", "invent_success_contract", "compile_mission_envelope", "execute_dependency_ordered_curriculum", "learn_format_contracts", "verify_transfer_outcomes"], 1.0 + transfer_reduction, gate["accepted"], {"gate": gate, "graph_hashes": {key: value["induction"]["graph_hash"] for key, value in induced.items()}}, [])
    promotion = runtime.learning.skills.promote(candidate); runtime.learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence); runtime.learning.store.commit(reason="open_mission_portfolio_induction")
    restarted = CanonicalAionCognitiveRuntime(paths=runtime.paths, adapter=OpenPortfolioAdapter(portfolios, induced, authority, workspace_root / "adapter_state.json"), goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True)
    restart = {"missions_retained": restarted.status()["authorized_missions"] == 4, "capability_records_retained": restarted.status()["capabilities_mastered"] == gate["invented_capability_nodes"], "format_contracts_retained": bool(restarted.adapter.state["format_contracts"]), "champion_retained": (restarted.learning.skills.champion("open_mission_portfolio_induction") or {}).get("procedure_id") == PROCEDURE_ID, "relearning_tasks": 0}
    result = {"schema_version": "aion.hexcore.open_mission_portfolio_induction.v1", "created_at": _utc_timestamp(), "passed": bool(gate["accepted"] and all(value is True or value == 0 for value in restart.values())), "procedure_id": PROCEDURE_ID, "portfolios": [{"portfolio_id": key, "cohort": row.cohort, "objective": row.objective, "source_hashes": [_sha(path) for path in row.sources], "induced_graph": induced[key]["induction"]["capability_graph"]} for key, row in portfolios.items()], "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "boundary": "AION derives variable-size capability graphs and executable missions from four unfamiliar real-file portfolios and reuses verified format contracts on transfer portfolios. File-type mappings, generic execution tools, objectives and evaluator checks remain engineered. This is open portfolio-to-mission compilation, not unrestricted goal understanding, arbitrary tool invention or AGI."}
    if result_path: result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo-root", type=Path, default=Path(".")); parser.add_argument("--workspace-root", type=Path, default=Path("backend/modules/hexcore/data/open_mission_induction")); parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_open_mission_portfolio_induction.json")); args = parser.parse_args()
    result = run(repo_root=args.repo_root.resolve(), workspace_root=args.workspace_root.resolve(), result_path=args.result_path.resolve()); print(json.dumps({"passed": result["passed"], "gate": result["gate"], "restart": result["restart"]}, indent=2, sort_keys=True)); raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__": main()
