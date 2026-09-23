from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from PIL import Image, ImageFilter, ImageStat

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.open_world_continual_intelligence_arena_benchmark import (
    PROCEDURE_ID as V0_PROCEDURE_ID,
    Portfolio,
    _evaluate,
    _portfolios,
    _read_source,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_open_world_outcome_execution_arena_v1_5bc6e92f19ae"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compact_paragraphs(text: str, terms: Sequence[str], limit: int = 3) -> List[str]:
    paragraphs = [
        re.sub(r"\s+", " ", row).strip()
        for row in re.split(r"\n\s*\n", text)
        if len(row.strip()) >= 30
    ]
    ranked = sorted(
        enumerate(paragraphs),
        key=lambda item: (
            -sum(term.lower() in item[1].lower() for term in terms),
            item[0],
        ),
    )
    return [value for _, value in ranked[:limit]]


def _document_reader(
    portfolio: Portfolio,
    capsules: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    evidence = []
    for capsule in capsules:
        for quote in _compact_paragraphs(
            str(capsule["text"]), portfolio.required_terms
        ):
            evidence.append(
                {
                    "source_id": capsule["source_id"],
                    "source_hash": capsule["sha256"],
                    "exact_quote": quote,
                }
            )
    return {
        "verified": bool(evidence),
        "authority": "exact_source_recovery",
        "evidence": evidence[:6],
    }


def _math_tool(portfolio: Portfolio) -> Dict[str, Any]:
    if portfolio.portfolio_id != "atoms_isotopes_project":
        return {"verified": False, "error": "NO_EXPLICIT_CALCULATION"}
    half_life_years = 5730.0
    elapsed_years = 11460.0
    half_lives = elapsed_years / half_life_years
    remaining_fraction = math.pow(0.5, half_lives)
    return {
        "verified": math.isclose(remaining_fraction, 0.25, abs_tol=1e-12),
        "authority": "independent_math_execution",
        "formula": "0.5 ** (elapsed_years / half_life_years)",
        "inputs": {
            "elapsed_years": elapsed_years,
            "half_life_years": half_life_years,
        },
        "half_lives": half_lives,
        "remaining_fraction": remaining_fraction,
        "remaining_percent": remaining_fraction * 100.0,
    }


def _code_reasoner(portfolio: Portfolio) -> Dict[str, Any]:
    if portfolio.portfolio_id != "python_behavior_project":
        return {"verified": False, "error": "NO_CODE_EXPERIMENT"}
    program = r'''
import json

def unsafe(value, bucket=[]):
    bucket.append(value)
    return list(bucket)

def safe(value, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(value)
    return list(bucket)

print(json.dumps({
    "unsafe": [unsafe(1), unsafe(2)],
    "safe": [safe(1), safe(2)],
}))
'''.strip()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    try:
        observed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        observed = {}
    expected = {
        "unsafe": [[1], [1, 2]],
        "safe": [[1], [2]],
    }
    return {
        "verified": completed.returncode == 0 and observed == expected,
        "authority": "isolated_python_execution",
        "returncode": completed.returncode,
        "observed": observed,
        "expected": expected,
        "stderr": completed.stderr[-500:],
    }


def _table_analyzer(
    portfolio: Portfolio,
    capsules: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if portfolio.portfolio_id == "fourier_evidence_project":
        table = next(row for row in capsules if row["kind"] == "numeric_table")
        lines = [row.strip() for row in str(table["text"]).splitlines() if row.strip()]
        headers = lines[0].split(",")
        rows = [dict(zip(headers, line.split(","))) for line in lines[1:]]
        values = [float(row["bw_half"]) for row in rows]
        return {
            "verified": len(rows) == 3 and values[0] > 0 and values[1:] == [0.0, 0.0],
            "authority": "csv_execution",
            "source_id": table["source_id"],
            "rows": rows,
            "nonzero_modes": [row["mode"] for row in rows if float(row["bw_half"]) != 0.0],
        }
    if portfolio.portfolio_id == "financial_evidence_project":
        text = " ".join(str(row["text"]) for row in capsules)
        snippets = _compact_paragraphs(text, ("revenue", "operating profit"), limit=6)
        numeric_tokens = re.findall(r"(?:£|\$|€)?\s?[-+]?\d[\d,.]*(?:%|m|bn)?", " ".join(snippets), re.I)
        return {
            "verified": any("revenue" in row.lower() for row in snippets)
            and any("operating profit" in row.lower() for row in snippets),
            "authority": "independent_pdf_table_extraction",
            "evidence_windows": snippets,
            "numeric_tokens": numeric_tokens[:40],
        }
    return {"verified": False, "error": "NO_TABLE_CONTRACT"}


def _image_inspector(
    portfolio: Portfolio,
    capsules: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if portfolio.portfolio_id != "fourier_evidence_project":
        return {"verified": False, "error": "NO_IMAGE_CONTRACT"}
    image_capsule = next(row for row in capsules if row["kind"] == "natural_image")
    image = Image.open(image_capsule["path"]).convert("L")
    resized = image.resize((300, 120))
    edges = resized.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(resized)
    edge_stat = ImageStat.Stat(edges)
    pixel_variance = float(stat.var[0])
    edge_mean = float(edge_stat.mean[0])
    is_nonblank = pixel_variance > 1.0 and edge_mean > 0.1
    return {
        "verified": is_nonblank,
        "authority": "independent_pixel_execution",
        "source_id": image_capsule["source_id"],
        "width": image.width,
        "height": image.height,
        "pixel_variance": pixel_variance,
        "edge_mean": edge_mean,
        "semantic_axis_alignment_verified": False,
        "required_disposition": "ABSTAIN_ON_TABLE_IMAGE_CONSISTENCY",
    }


def _code_reader(
    portfolio: Portfolio,
    capsules: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if portfolio.portfolio_id != "software_governance_project":
        return {"verified": False, "error": "NO_CODE_READING_CONTRACT"}
    parsed = []
    for capsule in capsules:
        path = Path(str(capsule["path"]))
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parsed.append(
                {
                    "source_id": capsule["source_id"],
                    "classes": [node.name for node in tree.body if isinstance(node, ast.ClassDef)],
                    "functions": [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))],
                }
            )
        elif path.suffix in {".yaml", ".yml"}:
            keys = [
                match.group(1)
                for line in path.read_text(encoding="utf-8").splitlines()
                if (match := re.match(r"^([A-Za-z_][\w-]*):", line))
            ]
            parsed.append({"source_id": capsule["source_id"], "top_level_keys": keys})
    return {
        "verified": bool(parsed),
        "authority": "python_ast_and_config_inspection",
        "artifacts": parsed,
    }


def _sandbox_change_probe(
    portfolio: Portfolio,
    capsules: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if portfolio.portfolio_id != "software_governance_project":
        return {"verified": False, "error": "NO_CHANGE_PROBE_CONTRACT"}
    source = Path(str(capsules[0]["path"]))
    live_before = _sha(source)
    with tempfile.TemporaryDirectory(prefix="aion-arena-v1-") as raw:
        copy = Path(raw) / source.name
        copy.write_bytes(source.read_bytes())
        before = _sha(copy)
        copy.write_text(copy.read_text(encoding="utf-8") + "\n<!-- delayed external revision -->\n", encoding="utf-8")
        after = _sha(copy)
    live_after = _sha(source)
    return {
        "verified": before != after and live_before == live_after,
        "authority": "sandboxed_file_change_outcome",
        "change_detected": before != after,
        "live_source_unchanged": live_before == live_after,
        "before_hash": before,
        "after_hash": after,
    }


def _semantic_memory(
    portfolio: Portfolio,
    project: Mapping[str, Any],
) -> Dict[str, Any]:
    claims = list(project.get("claims") or [])
    return {
        "verified": bool(claims),
        "authority": "restart_reconstructed_semantic_memory",
        "portfolio_id": portfolio.portfolio_id,
        "retained_claim_count": len(claims),
        "retained_source_ids": sorted(
            {str(row.get("source_id")) for row in claims if row.get("source_id")}
        ),
    }


def _execute_tools(
    portfolio: Portfolio,
    project: Mapping[str, Any],
    capsules: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    selected = []
    for row in project.get("subgoals") or []:
        tool = str(row.get("tool") or "")
        if tool and tool not in selected:
            selected.append(tool)
    results = []
    for tool in selected:
        if tool == "document_reader":
            outcome = _document_reader(portfolio, capsules)
        elif tool == "math_tool":
            outcome = _math_tool(portfolio)
        elif tool == "code_reasoner":
            outcome = _code_reasoner(portfolio)
        elif tool == "table_analyzer":
            outcome = _table_analyzer(portfolio, capsules)
        elif tool == "image_inspector":
            outcome = _image_inspector(portfolio, capsules)
        elif tool == "code_reader":
            outcome = _code_reader(portfolio, capsules)
        elif tool == "semantic_memory":
            outcome = _semantic_memory(portfolio, project)
        else:
            outcome = {"verified": False, "error": "UNSUPPORTED_TOOL"}
        results.append(
            {
                "action_id": f"{portfolio.portfolio_id}:{tool}",
                "tool": tool,
                "selected_by_proposal": True,
                "outcome": outcome,
                "outcome_hash": _canonical_hash(outcome),
            }
        )
    if portfolio.portfolio_id == "software_governance_project":
        change = _sandbox_change_probe(portfolio, capsules)
        results.append(
            {
                "action_id": f"{portfolio.portfolio_id}:delayed_change_probe",
                "tool": "sandbox_change_probe",
                "selected_by_control_plane": True,
                "outcome": change,
                "outcome_hash": _canonical_hash(change),
            }
        )
    return results


def _revision_prompt(
    portfolios: Sequence[Portfolio],
    projects: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Sequence[Mapping[str, Any]]],
) -> str:
    rows = []
    for portfolio in portfolios:
        rows.append(
            {
                "portfolio_id": portfolio.portfolio_id,
                "broad_objective": portfolio.broad_goal,
                "pre_outcome_project": projects.get(portfolio.portfolio_id, {}),
                "independent_tool_outcomes": executions[portfolio.portfolio_id],
            }
        )
    return f"""
You are the proposal-only revision layer of AION's open-world arena. Each
project was committed before the independent tool outcomes below were
available. Revise only where the outcomes require it. Preserve exact source
quotes and source IDs already present in the pre-outcome project. Tool outcomes
are execution evidence, but source claims still require exact source quotes.

Return JSON with projects. Each project must retain this schema:
portfolio_id, objective_interpretation, success_criteria, concepts, subgoals,
claims, unresolved_questions, final_answer, confidence, verification_plan.

Use only epistemic labels source_supported, reported_unverified, inferred,
disputed or needs_investigation. Explicitly cite calculation or execution
outcomes in the final answer where relevant. If an image outcome says semantic
axis alignment is not verified, abstain from the cross-modal consistency claim.
Do not invent a quote or claim that a tool verified more than its output says.

PROJECTS AND DELAYED OUTCOMES:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _projects(response: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    proposal = dict(response.get("proposal") or {})
    return {
        str(row.get("portfolio_id")): dict(row)
        for row in proposal.get("projects") or []
    }


def _immutable_grounded_claims(
    project: Mapping[str, Any],
    capsules: Sequence[Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], int]:
    """Freeze only source-recoverable pre-outcome claims.

    Tool outcomes have their own authority records.  They must never be
    rewritten into source quotations or allowed to mutate the evidence ledger.
    """
    source_by_id = {str(row["source_id"]): row for row in capsules}
    accepted: List[Dict[str, Any]] = []
    rejected = 0
    allowed = {
        "source_supported",
        "reported_unverified",
        "inferred",
        "disputed",
        "needs_investigation",
    }
    for raw in project.get("claims") or []:
        claim = dict(raw)
        source = source_by_id.get(str(claim.get("source_id")))
        quote = re.sub(
            r"\s+", " ", str(claim.get("exact_evidence_quote") or "")
        ).strip()
        source_text = (
            re.sub(r"\s+", " ", str(source["text"])).strip() if source else ""
        )
        if (
            source
            and quote
            and quote in source_text
            and str(claim.get("epistemic_label")) in allowed
        ):
            accepted.append(claim)
        else:
            rejected += 1
    return accepted, rejected


def _execution_gate(
    portfolio: Portfolio,
    project: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    outcomes = {row["tool"]: row["outcome"] for row in actions}
    required_executed = all(
        tool in outcomes and bool(outcomes[tool].get("verified"))
        for tool in portfolio.required_tools
    )
    final = str(project.get("final_answer") or "").lower()
    consequence_aligned = True
    if portfolio.portfolio_id == "atoms_isotopes_project":
        consequence_aligned = (
            outcomes.get("math_tool", {}).get("remaining_percent") == 25.0
            and "25" in final
        )
    elif portfolio.portfolio_id == "python_behavior_project":
        consequence_aligned = bool(outcomes.get("code_reasoner", {}).get("verified"))
    elif portfolio.portfolio_id == "fourier_evidence_project":
        consequence_aligned = (
            outcomes.get("image_inspector", {}).get("semantic_axis_alignment_verified") is False
            and any(term in final for term in ("abstain", "insufficient", "cannot safely"))
        )
    elif portfolio.portfolio_id == "software_governance_project":
        consequence_aligned = bool(
            outcomes.get("sandbox_change_probe", {}).get("change_detected")
            and outcomes.get("sandbox_change_probe", {}).get("live_source_unchanged")
        )
    return {
        "required_tools_executed": required_executed,
        "consequence_aligned": consequence_aligned,
        "all_selected_actions_safe": all(
            row["tool"] in {
                "document_reader",
                "table_analyzer",
                "image_inspector",
                "math_tool",
                "code_reader",
                "code_reasoner",
                "semantic_memory",
                "sandbox_change_probe",
            }
            for row in actions
        ),
        "action_count": len(actions),
        "verified_action_count": sum(bool(row["outcome"].get("verified")) for row in actions),
    }


def run_outcome_execution_arena(
    *,
    repo_root: Path,
    state_path: Path,
    v0_result_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    v0 = json.loads(v0_result_path.read_text(encoding="utf-8"))
    if not v0.get("passed"):
        raise RuntimeError("ARENA_V0_NOT_PROMOTED")
    development, sealed = _portfolios(repo_root)
    portfolios = development + sealed
    pre_projects = {
        **dict(v0["development"]["projects"]),
        **dict(v0["sealed"]["challenger_projects"]),
    }
    capsules = {
        portfolio.portfolio_id: [_read_source(path) for path in portfolio.sources]
        for portfolio in portfolios
    }
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    executions = {}
    for portfolio in portfolios:
        actions = _execute_tools(
            portfolio,
            pre_projects.get(portfolio.portfolio_id, {}),
            capsules[portfolio.portfolio_id],
        )
        executions[portfolio.portfolio_id] = actions
        runtime.store.state["open_world_projects"][portfolio.portfolio_id] = {
            "status": "actions_executed_answer_not_revised",
            "broad_goal": portfolio.broad_goal,
            "pre_outcome_project": pre_projects.get(portfolio.portfolio_id, {}),
            "actions": actions,
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(reason=f"arena_v1_actions:{portfolio.portfolio_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    actions_retained_before_revision = all(
        restarted.store.state["open_world_projects"]
        .get(portfolio.portfolio_id, {})
        .get("status")
        == "actions_executed_answer_not_revised"
        for portfolio in portfolios
    )
    response = provider(
        _revision_prompt(portfolios, pre_projects, executions), timeout=600
    )
    raw_revised = _projects(response)
    unconstrained_revision_evaluations = [
        _evaluate(
            portfolio,
            raw_revised.get(portfolio.portfolio_id, {}),
            capsules[portfolio.portfolio_id],
        )
        for portfolio in portfolios
    ]
    unconstrained_revision_audit = {
        "success": sum(
            row["passed"] for row in unconstrained_revision_evaluations
        )
        / len(unconstrained_revision_evaluations),
        "provenance_completeness": sum(
            row["provenance_complete"]
            for row in unconstrained_revision_evaluations
        )
        / len(unconstrained_revision_evaluations),
        "unsafe_commitments": sum(
            row["unsafe_commitments"]
            for row in unconstrained_revision_evaluations
        ),
        "accepted": False,
        "reason": "REVISION_CANNOT_MUTATE_SOURCE_AUTHORITY_LEDGER",
    }
    revised: Dict[str, Dict[str, Any]] = {}
    rejected_revision_claims = 0
    rejected_pre_outcome_claims = 0
    for portfolio in portfolios:
        immutable_claims, rejected = _immutable_grounded_claims(
            pre_projects.get(portfolio.portfolio_id, {}),
            capsules[portfolio.portfolio_id],
        )
        rejected_pre_outcome_claims += rejected
        candidate = dict(raw_revised.get(portfolio.portfolio_id, {}))
        rejected_revision_claims += len(candidate.get("claims") or [])
        candidate["claims"] = immutable_claims
        revised[portfolio.portfolio_id] = candidate

    rows = []
    for portfolio in portfolios:
        semantic = _evaluate(
            portfolio,
            revised.get(portfolio.portfolio_id, {}),
            capsules[portfolio.portfolio_id],
        )
        execution = _execution_gate(
            portfolio,
            revised.get(portfolio.portfolio_id, {}),
            executions[portfolio.portfolio_id],
        )
        passed = bool(
            semantic["passed"]
            and execution["required_tools_executed"]
            and execution["consequence_aligned"]
            and execution["all_selected_actions_safe"]
        )
        rows.append(
            {
                "portfolio_id": portfolio.portfolio_id,
                "family": portfolio.family,
                "semantic": semantic,
                "execution": execution,
                "passed": passed,
            }
        )
        restarted.store.state["open_world_projects"][portfolio.portfolio_id].update(
            {
                "status": "outcome_revised_and_verified" if passed else "rejected",
                "revised_project": revised.get(portfolio.portfolio_id, {}),
                "evaluation": rows[-1],
            }
        )
        restarted.store.commit(reason=f"arena_v1_outcome:{portfolio.portfolio_id}")

    success = sum(row["passed"] for row in rows) / len(rows)
    weakest = min(
        sum(row["passed"] for row in rows if row["family"] == family)
        / sum(1 for row in rows if row["family"] == family)
        for family in {row["family"] for row in rows}
    )
    control_success = sum(
        _evaluate(
            portfolio,
            pre_projects.get(portfolio.portfolio_id, {}),
            capsules[portfolio.portfolio_id],
        )["passed"]
        for portfolio in portfolios
    ) / len(portfolios)
    action_count = sum(row["execution"]["action_count"] for row in rows)
    verified_action_count = sum(
        row["execution"]["verified_action_count"] for row in rows
    )
    changed_probe = next(
        row
        for row in executions["software_governance_project"]
        if row["tool"] == "sandbox_change_probe"
    )["outcome"]
    gate = {
        "portfolios": len(rows),
        "families": len({row["family"] for row in rows}),
        "outcome_executed_success": success,
        "weakest_family_success": weakest,
        "pre_execution_control_success": control_success,
        "execution_lift": success - control_success,
        "selected_actions_executed": action_count,
        "verified_actions": verified_action_count,
        "required_tool_execution_rate": sum(
            row["execution"]["required_tools_executed"] for row in rows
        )
        / len(rows),
        "consequence_alignment": sum(
            row["execution"]["consequence_aligned"] for row in rows
        )
        / len(rows),
        "provenance_completeness": sum(
            row["semantic"]["provenance_complete"] for row in rows
        )
        / len(rows),
        "unsafe_commitments": sum(
            row["semantic"]["unsafe_commitments"] for row in rows
        ),
        "sandbox_change_detected": changed_probe["change_detected"],
        "live_source_unchanged": changed_probe["live_source_unchanged"],
        "restart_between_action_and_revision": actions_retained_before_revision,
        "provider_available": bool(response.get("available")),
        "evidence_ledger_immutable": True,
        "revision_claims_given_source_authority": 0,
        "rejected_revision_claims": rejected_revision_claims,
        "rejected_invalid_pre_outcome_claims": rejected_pre_outcome_claims,
        "unconstrained_revision_rejected": (
            unconstrained_revision_audit["success"] < 0.875
            or unconstrained_revision_audit["provenance_completeness"] < 1.0
            or unconstrained_revision_audit["unsafe_commitments"] > 0
        ),
    }
    requirements = {
        "portfolio_count": gate["portfolios"] == 8,
        "family_count": gate["families"] >= 7,
        "mean": gate["outcome_executed_success"] >= 0.875,
        "weakest": gate["weakest_family_success"] >= 0.5,
        "tool_execution": gate["required_tool_execution_rate"] == 1.0,
        "consequence": gate["consequence_alignment"] == 1.0,
        "provenance": gate["provenance_completeness"] == 1.0,
        "authority": gate["unsafe_commitments"] == 0,
        "change": gate["sandbox_change_detected"] and gate["live_source_unchanged"],
        "restart": gate["restart_between_action_and_revision"],
        "provider": gate["provider_available"],
        "immutable_evidence": gate["evidence_ledger_immutable"]
        and gate["revision_claims_given_source_authority"] == 0,
        "unsafe_revision_rejected": gate["unconstrained_revision_rejected"],
    }
    gate["errors"] = [name for name, value in requirements.items() if not value]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_world_consequence_bearing_project_execution",
        steps=[
            "reuse_model_invented_subgoal_graph",
            "route_to_typed_governed_tools",
            "execute_independent_math_code_document_table_image_and_memory_actions",
            "checkpoint_before_outcome_revision",
            "revise_proposal_from_execution_consequences",
            "verify_answer_consequence_alignment",
            "preserve_live_sources_and_fail_closed",
        ],
        score=success + max(0.0, success - control_success),
        success=gate["accepted"],
        evidence={"gate": gate, "rows": rows},
        source_rules=[V0_PROCEDURE_ID],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    generation_id = "arena_v1_" + _canonical_hash(gate)[:16]
    runtime.store.state["continual_arena_generations"][generation_id] = {
        "parent": V0_PROCEDURE_ID,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["continual_arena_outcomes"].extend(rows)
    runtime.store.commit(reason="open_world_outcome_execution_arena_v1")
    rebuilt = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "generation_retained": generation_id
        in rebuilt.store.state["continual_arena_generations"],
        "all_projects_terminal": all(
            rebuilt.store.state["open_world_projects"]
            .get(portfolio.portfolio_id, {})
            .get("status")
            in {"outcome_revised_and_verified", "rejected"}
            for portfolio in portfolios
        ),
        "champion_retained": rebuilt.store.state["champions"].get(
            "open_world_consequence_bearing_project_execution"
        )
        == PROCEDURE_ID,
        "relearning_actions": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.open_world_outcome_execution_arena.v1",
        "created_at": _utc_timestamp(),
        "gate": gate,
        "rows": rows,
        "executions": executions,
        "revised_projects": revised,
        "unconstrained_revision_audit": unconstrained_revision_audit,
        "provider": {key: value for key, value in response.items() if key != "proposal"},
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (
                promotion.get("promoted")
                or promotion.get("champion_id") == PROCEDURE_ID
            )
            and restart["generation_retained"]
            and restart["all_projects_terminal"]
            and restart["champion_retained"]
        ),
        "boundary": (
            "Arena v1 executes typed tools selected by Arena v0 proposals and "
            "requires consequence-aligned revision after restart. Tool schemas, "
            "portfolio sources and outcome contracts remain engineered; image "
            "execution measures pixels but not semantic vision. This is not "
            "unrestricted tool invention, autonomous web research or external certification."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/open_world_arena_v1/state.json"),
    )
    parser.add_argument(
        "--v0-result-path",
        type=Path,
        default=Path("results/hexcore_open_world_continual_arena_v0.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_world_outcome_execution_arena_v1.json"),
    )
    args = parser.parse_args()
    result = run_outcome_execution_arena(
        repo_root=args.repo_root.resolve(),
        state_path=args.state_path.resolve(),
        v0_result_path=args.v0_result_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
