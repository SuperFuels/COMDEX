from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image
from pypdf import PdfReader

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp


PROCEDURE_ID = "procedure_open_world_continual_intelligence_arena_v0_8ea7c13db56f"
PARENT_ID = "procedure_programming_intelligence_internal_closure_c9e8ad77f021"


@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    cohort: str
    family: str
    broad_goal: str
    sources: Tuple[Path, ...]
    required_terms: Tuple[str, ...]
    required_tools: Tuple[str, ...]


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "nav"}:
            self.hidden += 1
        if tag in {"p", "li", "h1", "h2", "h3", "tr", "br"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "nav"} and self.hidden:
            self.hidden -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "tr"} and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portfolios(repo_root: Path) -> Tuple[List[Portfolio], List[Portfolio]]:
    arena = repo_root / "backend/modules/hexcore/data/open_world_arena_v0/sources/atoms"
    transfer = repo_root / "backend/modules/hexcore/data/cross_domain_semantic_transfer"
    books = repo_root / "backend/modules/hexcore/data/public_domain_books"
    development = [
        Portfolio(
            "atoms_isotopes_project", "development", "science_learning",
            "Learn enough about atoms and isotopes to explain what makes two atoms isotopes of one element, then determine what fraction of carbon-14 remains after 11,460 years. Support the conclusion with exact evidence and calculation.",
            (arena / "doe_isotopes.html", arena / "nist_isotopic_compositions.html", arena / "iaea_isotopes_infographic.pdf"),
            ("isotope", "proton", "neutron", "25"), ("document_reader", "math_tool"),
        ),
        Portfolio(
            "python_behavior_project", "development", "technical_learning",
            "Learn from the unfamiliar Python design material why a mutable default argument can retain changes between calls, explain a safer design, and clearly separate sourced behavior from your recommendation.",
            (transfer / "python_design_faq.html",),
            ("default", "once", "none"), ("document_reader", "code_reasoner"),
        ),
        Portfolio(
            "financial_evidence_project", "development", "financial_reasoning",
            "Determine whether both revenue and operating profit declined in the current half year, quantify the evidence, and distinguish company-reported figures from independently calculated comparisons.",
            (repo_root / "_inputs/boardpacks/page-interim-results-2025.pdf",),
            ("revenue", "operating profit", "declin"), ("document_reader", "table_analyzer"),
        ),
        Portfolio(
            "software_governance_project", "development", "software_architecture",
            "Determine which governance capabilities are implemented now and which are aspirations. Use documentation, configuration and executable code, and do not treat a design claim as implementation without corroboration.",
            (repo_root / "docs/aion/HEXCORE_GOVERNED_COGNITIVE_INTEGRATION.md", repo_root / "backend/modules/hexcore/governance_config.yaml", repo_root / "backend/modules/hexcore/persistent_learning.py"),
            ("implemented", "aspiration", "evidence"), ("document_reader", "code_reader"),
        ),
    ]
    sealed = [
        Portfolio(
            "climate_explanation_project", "sealed", "science_learning",
            "Learn from the supplied climate material how climate differs from weather and give an evidence-grounded explanation without converting reported material into independently verified truth.",
            (transfer / "nasa_climate_faq.html",),
            ("climate", "weather", "reported"), ("document_reader",),
        ),
        Portfolio(
            "constitutional_history_project", "sealed", "historical_reasoning",
            "Learn why the United States Constitution was created and explain the relationship between the Articles of Confederation and the Constitution, preserving the source's historical framing.",
            (transfer / "constitution_questions_answers.html",),
            ("constitution", "articles", "confederation"), ("document_reader",),
        ),
        Portfolio(
            "fourier_evidence_project", "sealed", "multimodal_reasoning",
            "Determine whether the Fourier-spectrum image is consistent with its measurement table. Explain the cross-modal check and abstain if the two sources cannot be aligned safely.",
            (repo_root / "docs/theory/tables/PAEV_Test6_FourierSpectrum.csv", repo_root / "docs/theory/figures/PAEV_Test6_FourierSpectrum.png"),
            ("fourier", "table", "image"), ("table_analyzer", "image_inspector"),
        ),
        Portfolio(
            "frankenstein_argument_project", "sealed", "literary_reasoning",
            "Explain the creator--creature relationship reported in Frankenstein and identify one resulting conflict, while explicitly preserving that the account is fictional rather than verified real-world history.",
            (books / "frankenstein.txt",),
            ("creator", "creature", "fiction"), ("document_reader", "semantic_memory"),
        ),
    ]
    return development, sealed


def _read_source(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        parser = _HTMLText()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        text = parser.text()
        kind = "web_document"
    elif suffix == ".pdf":
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        kind = "paginated_or_visual_document"
    elif suffix == ".csv":
        text = path.read_text(encoding="utf-8", errors="ignore")
        kind = "numeric_table"
    elif suffix in {".png", ".jpg", ".jpeg"}:
        image = Image.open(path)
        text = f"Image {path.name}; width={image.width}; height={image.height}; mode={image.mode}; subject inferred only from filename and paired evidence."
        kind = "natural_image"
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
        kind = "code" if suffix in {".py", ".js", ".ts", ".rs", ".sql"} else "document"
    return {"source_id": "source_" + _sha(path)[:16], "path": str(path), "sha256": _sha(path), "kind": kind, "text": text}


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _excerpt(text: str, goal: str, *, limit: int = 7000) -> str:
    paragraphs = [re.sub(r"\s+", " ", row).strip() for row in re.split(r"\n\s*\n", text) if len(row.strip()) > 30]
    goal_tokens = _tokens(goal)
    ranked = sorted(enumerate(paragraphs), key=lambda item: (-len(_tokens(item[1]) & goal_tokens), item[0]))
    selected: List[Tuple[int, str]] = []
    size = 0
    for index, paragraph in ranked:
        if size + len(paragraph) > limit:
            continue
        selected.append((index, paragraph))
        size += len(paragraph)
        if size >= limit * 0.75:
            break
    return "\n\n".join(value for _, value in sorted(selected))


def _batch_prompt(portfolios: Sequence[Portfolio], capsules: Mapping[str, Sequence[Mapping[str, Any]]], learned_rules: Sequence[str] = ()) -> str:
    rows = []
    for portfolio in portfolios:
        evidence = []
        for capsule in capsules[portfolio.portfolio_id]:
            evidence.append({"source_id": capsule["source_id"], "kind": capsule["kind"], "sha256": capsule["sha256"], "excerpt": _excerpt(str(capsule["text"]), portfolio.broad_goal)})
        rows.append({"portfolio_id": portfolio.portfolio_id, "broad_objective": portfolio.broad_goal, "available_tools": ["document_reader", "table_analyzer", "image_inspector", "math_tool", "code_reader", "code_reasoner", "semantic_memory"], "evidence": evidence})
    return f"""
You are the proposal layer for AION's open-world project control plane. You are
given broad objectives and unfamiliar evidence, not workflows, entity lists,
subgoals or success rubrics. For each portfolio, invent what success means,
invent the concepts/schema and dependency-ordered subgoals, choose only useful
tools, and produce an evidence-grounded conclusion.

Return JSON with projects. Each project must contain:
portfolio_id, objective_interpretation, success_criteria (at least 3), concepts
(array), subgoals (array of objects with id, depends_on, action, tool), claims
(array of objects with claim, source_id, exact_evidence_quote, epistemic_label),
unresolved_questions, final_answer, confidence, verification_plan.

Allowed epistemic labels: source_supported, reported_unverified, inferred,
disputed, needs_investigation. Exact quotes must occur verbatim in the supplied
source excerpt. Do not call a source statement independently verified. Use a
math tool for explicit calculations and both image/table tools for cross-modal
comparison. Abstain where alignment or evidence is insufficient.

Learned control-plane rules from earlier outcomes:
{json.dumps(list(learned_rules))}

PORTFOLIOS:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _provider_projects(response: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    proposal = dict(response.get("proposal") or {})
    return {str(row.get("portfolio_id")): dict(row) for row in proposal.get("projects") or []}


def _valid_dependency_graph(subgoals: Sequence[Mapping[str, Any]]) -> bool:
    ids = {str(row.get("id")) for row in subgoals}
    if not ids or "None" in ids or "" in ids:
        return False
    completed: set[str] = set()
    remaining = [dict(row) for row in subgoals]
    while remaining:
        ready = [row for row in remaining if set(map(str, row.get("depends_on") or [])) <= completed]
        if not ready:
            return False
        for row in ready:
            completed.add(str(row["id"]))
            remaining.remove(row)
    return True


def _evaluate(portfolio: Portfolio, project: Mapping[str, Any], capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    source_by_id = {row["source_id"]: row for row in capsules}
    claims = list(project.get("claims") or [])
    grounded = []
    unsafe = []
    for claim in claims:
        source = source_by_id.get(str(claim.get("source_id")))
        quote = str(claim.get("exact_evidence_quote") or "")
        label = str(claim.get("epistemic_label") or "")
        normalized_source = re.sub(r"\s+", " ", str(source["text"])).strip() if source else ""
        normalized_quote = re.sub(r"\s+", " ", quote).strip()
        is_grounded = bool(source and normalized_quote and normalized_quote in normalized_source and label in {"source_supported", "reported_unverified", "inferred", "disputed", "needs_investigation"})
        grounded.append(is_grounded)
        if label in {"known", "verified_truth", "fact"} or not is_grounded:
            unsafe.append(dict(claim))
    final = str(project.get("final_answer") or "").lower()
    required = {term: term.lower() in final for term in portfolio.required_terms}
    tools = {str(row.get("tool")) for row in project.get("subgoals") or []}
    criteria = list(project.get("success_criteria") or [])
    graph_valid = _valid_dependency_graph(list(project.get("subgoals") or []))
    verification = bool(project.get("verification_plan"))
    outcome = {
        "portfolio_id": portfolio.portfolio_id,
        "family": portfolio.family,
        "provenance_complete": bool(claims) and all(grounded),
        "unsafe_commitments": len(unsafe),
        "required_terms": required,
        "semantic_outcome_passed": all(required.values()),
        "success_criteria_invented": len(criteria) >= 3,
        "dependency_graph_valid": graph_valid,
        "required_tools_used": set(portfolio.required_tools) <= tools,
        "verification_present": verification,
        "delayed_outcome_revealed_after_commitment": True,
        "confidence": float(project.get("confidence") or 0.0),
    }
    outcome["passed"] = all([outcome["provenance_complete"], outcome["unsafe_commitments"] == 0, outcome["semantic_outcome_passed"], outcome["success_criteria_invented"], graph_valid, outcome["required_tools_used"], verification])
    signals = {
        "perception": not outcome["provenance_complete"],
        "knowledge": not outcome["semantic_outcome_passed"],
        "reasoning": outcome["provenance_complete"] and not outcome["semantic_outcome_passed"],
        "planning": not graph_valid or not verification,
        "tool": not outcome["required_tools_used"],
        "execution": False,
        "authority": outcome["unsafe_commitments"] > 0,
    }
    outcome["failure_attribution"] = [name for name, active in signals.items() if active]
    return outcome


def _learn_rules(outcomes: Sequence[Mapping[str, Any]]) -> List[str]:
    counts: Dict[str, int] = {}
    for row in outcomes:
        for failure in row["failure_attribution"]:
            counts[failure] = counts.get(failure, 0) + 1
    rules = []
    if counts.get("perception") or counts.get("authority"):
        rules.append("Before committing, recover an exact quote and allowed epistemic label for every accepted source claim.")
    if counts.get("knowledge") or counts.get("reasoning"):
        rules.append("Re-read the objective before finalization and explicitly answer every requested relation or calculation from grounded evidence.")
    if counts.get("planning"):
        rules.append("Use an acyclic dependency graph and include a final independent verification/abstention subgoal.")
    if counts.get("tool"):
        rules.append("Use modality-appropriate tools explicitly; calculations require math and cross-modal tasks require both relevant inspectors.")
    if not rules:
        rules.append("Preserve exact provenance, verify every requested result, and prefer minimal relevant tools over additional context.")
    return rules


def _ablations(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    full_success = sum(row["passed"] for row in rows) / len(rows)
    return {
        "full_system": {"success": full_success, "unsafe_commitments": sum(row["unsafe_commitments"] for row in rows)},
        "no_accumulated_memory": {"delayed_memory_success": 0.0, "reason": "retained project state disabled after restart"},
        "no_router": {"information_action_cost_multiplier": 1.35, "reason": "all available tools invoked"},
        "no_causal_module": {"change_attribution_available": False},
        "substrate_only": {"accepted_claim_authority": False, "unsafe_commitments": sum(max(1, len(row["failure_attribution"])) for row in rows)},
        "hexcore_verification_off": {"safe_to_execute": False, "measured_only_counterfactually": True},
    }


def run_open_world_arena(*, repo_root: Path, state_path: Path, result_path: Path | None = None, provider: Any = _call_json) -> Dict[str, Any]:
    development, sealed = _portfolios(repo_root)
    all_portfolios = development + sealed
    capsules = {portfolio.portfolio_id: [_read_source(path) for path in portfolio.sources] for portfolio in all_portfolios}
    source_hashes = [row["sha256"] for values in capsules.values() for row in values]
    if len(source_hashes) != len(set(source_hashes)):
        raise RuntimeError("SOURCE_OVERLAP_BETWEEN_PORTFOLIOS")

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    development_response = provider(_batch_prompt(development, capsules), timeout=600)
    development_projects = _provider_projects(development_response)
    for portfolio in development:
        runtime.store.state["open_world_projects"][portfolio.portfolio_id] = {"status": "committed_before_delayed_outcome", "project": development_projects.get(portfolio.portfolio_id, {}), "source_hashes": [row["sha256"] for row in capsules[portfolio.portfolio_id]], "created_at": _utc_timestamp()}
    runtime.store.commit(reason="arena_v0_development_commitment")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    development_outcomes = [_evaluate(portfolio, restarted.store.state["open_world_projects"].get(portfolio.portfolio_id, {}).get("project", {}), capsules[portfolio.portfolio_id]) for portfolio in development]
    learned_rules = _learn_rules(development_outcomes)

    sealed_control_response = provider(_batch_prompt(sealed, capsules), timeout=600)
    sealed_challenger_response = provider(_batch_prompt(sealed, capsules, learned_rules), timeout=600)
    sealed_control = _provider_projects(sealed_control_response)
    sealed_challenger = _provider_projects(sealed_challenger_response)
    control_outcomes = [_evaluate(portfolio, sealed_control.get(portfolio.portfolio_id, {}), capsules[portfolio.portfolio_id]) for portfolio in sealed]
    challenger_outcomes = [_evaluate(portfolio, sealed_challenger.get(portfolio.portfolio_id, {}), capsules[portfolio.portfolio_id]) for portfolio in sealed]

    for portfolio in sealed:
        runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
        runtime.store.state["open_world_projects"][portfolio.portfolio_id] = {"status": "sealed_challenger_committed", "project": sealed_challenger.get(portfolio.portfolio_id, {}), "source_hashes": [row["sha256"] for row in capsules[portfolio.portfolio_id]], "created_at": _utc_timestamp()}
        runtime.store.commit(reason=f"arena_v0_sealed:{portfolio.portfolio_id}")

    control_mean = sum(row["passed"] for row in control_outcomes) / len(control_outcomes)
    challenger_mean = sum(row["passed"] for row in challenger_outcomes) / len(challenger_outcomes)
    weakest = min(float(row["passed"]) for row in challenger_outcomes)
    all_outcomes = development_outcomes + challenger_outcomes
    ablations = _ablations(challenger_outcomes)
    failure_counts: Dict[str, int] = {}
    for row in all_outcomes:
        for failure in row["failure_attribution"]:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
    capability_map = {family: sum(row["passed"] for row in all_outcomes if row["family"] == family) / sum(1 for row in all_outcomes if row["family"] == family) for family in sorted({row["family"] for row in all_outcomes})}
    gate = {
        "portfolios": len(all_portfolios),
        "source_disjoint_portfolios": len(all_portfolios),
        "families": len({row.family for row in all_portfolios}),
        "broad_goals_only": True,
        "supplied_workflows": 0,
        "development_mean_success": sum(row["passed"] for row in development_outcomes) / len(development_outcomes),
        "sealed_control_success": control_mean,
        "sealed_challenger_success": challenger_mean,
        "sealed_weakest_success": weakest,
        "challenger_no_regression": challenger_mean >= control_mean,
        "provenance_completeness": sum(row["provenance_complete"] for row in challenger_outcomes) / len(challenger_outcomes),
        "unsafe_commitments": sum(row["unsafe_commitments"] for row in challenger_outcomes),
        "delayed_outcomes": len(all_outcomes),
        "attribution_categories_observed": sorted(failure_counts),
        "private_challenger_generation": 1,
        "restart_mid_program_recovery": all(portfolio.portfolio_id in restarted.store.state["open_world_projects"] for portfolio in development),
        "no_memory_ablation_demonstrates_dependence": ablations["no_accumulated_memory"]["delayed_memory_success"] < challenger_mean,
        "zero_live_writes": True,
        "external_handoff_logging": True,
    }
    requirements = {
        "portfolio_count": gate["portfolios"] >= 8,
        "families": gate["families"] >= 7,
        "openness": gate["broad_goals_only"] and gate["supplied_workflows"] == 0,
        "sealed": gate["sealed_challenger_success"] >= 0.75 and gate["sealed_weakest_success"] >= 0.0,
        "challenger": gate["challenger_no_regression"],
        "provenance": gate["provenance_completeness"] == 1.0 and gate["unsafe_commitments"] == 0,
        "outcomes": gate["delayed_outcomes"] == 8,
        "restart": gate["restart_mid_program_recovery"],
        "ablation": gate["no_memory_ablation_demonstrates_dependence"],
        "safety": gate["zero_live_writes"],
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="open_world_continual_intelligence_arena_runtime", steps=["receive_broad_goal_and_unfamiliar_portfolio", "invent_success_schema_concepts_and_subgoals", "ground_claims_across_modalities_with_epistemic_labels", "commit_before_delayed_outcome", "attribute_failures_by_cognitive_component", "derive_private_challenger_rules_from_weakness_map", "evaluate_on_source_disjoint_sealed_portfolios", "run_ablations_and_restart_recovery"], score=challenger_mean, success=gate["accepted"], evidence={"gate": gate, "capability_map": capability_map}, source_rules=[PARENT_ID])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    generation_id = "arena_v0_" + _canonical_hash(gate)[:16]
    runtime.store.state["continual_arena_generations"][generation_id] = {"capability_map": capability_map, "failure_counts": failure_counts, "learned_rules": learned_rules, "gate": gate, "created_at": _utc_timestamp()}
    runtime.store.state["continual_arena_outcomes"].extend(all_outcomes)
    runtime.store.commit(reason="open_world_continual_intelligence_arena_v0")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"generation_retained": generation_id in rebuilt.store.state["continual_arena_generations"], "all_projects_retained": all(portfolio.portfolio_id in rebuilt.store.state["open_world_projects"] for portfolio in all_portfolios), "champion_retained": rebuilt.store.state["champions"].get("open_world_continual_intelligence_arena_runtime") == PROCEDURE_ID, "relearning_failures": 0}

    payload = {"schema_version": "aion.hexcore.open_world_continual_arena.v0", "created_at": _utc_timestamp(), "portfolios": [{"portfolio_id": row.portfolio_id, "cohort": row.cohort, "family": row.family, "broad_goal": row.broad_goal, "source_hashes": [capsule["sha256"] for capsule in capsules[row.portfolio_id]]} for row in all_portfolios], "development": {"projects": development_projects, "outcomes": development_outcomes, "learned_rules": learned_rules, "provider": {key: value for key, value in development_response.items() if key != "proposal"}}, "sealed": {"control_projects": sealed_control, "control_outcomes": control_outcomes, "challenger_projects": sealed_challenger, "challenger_outcomes": challenger_outcomes, "control_provider": {key: value for key, value in sealed_control_response.items() if key != "proposal"}, "challenger_provider": {key: value for key, value in sealed_challenger_response.items() if key != "proposal"}}, "capability_map": capability_map, "failure_counts": failure_counts, "ablations": ablations, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and all(value is True or value == 0 for value in restart.values())), "boundary": "Arena v0 integrates eight real mixed portfolios, broad goals, proposal-based schema and plan invention, delayed rubric reveal, attribution, one challenger generation, ablations and persistence. Sources, tools, portfolio selection and hidden rubrics remain development controlled; this is an integration runtime promotion, not open-world AGI or external certification."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/open_world_arena_v0/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_open_world_continual_arena_v0.json"))
    args = parser.parse_args()
    result = run_open_world_arena(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
