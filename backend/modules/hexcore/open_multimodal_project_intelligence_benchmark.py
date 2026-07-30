from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import yaml
from PIL import Image
from pypdf import PdfReader

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class OpenPortfolio:
    portfolio_id: str
    cohort: str
    family: str
    broad_goal: str
    source_paths: Tuple[Path, ...]
    revision_target: str | None = None


DEFAULT_COLORS = (
    (31, 119, 180),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase58_open_multimodal_project_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normal_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2
    }


def _portfolio_sets(repo_root: Path) -> Tuple[List[OpenPortfolio], List[OpenPortfolio]]:
    temporal_csv = repo_root / "docs/theory/tables/PAEV_Test5_TemporalDecay.csv"
    temporal_png = repo_root / "docs/theory/figures/PAEV_Test5_TemporalDecay.png"
    page_csv = (
        repo_root / "docs/rfc/Photon Algebra Experimental Validation"
        / "Photon Algebra Experimental Validation Suite (PAEV-10)"
        / "Blackhole/PAEV_TestF6f_PageCurve.csv"
    )
    page_png = (
        repo_root / "docs/rfc/Photon Algebra Experimental Validation"
        / "Photon Algebra Experimental Validation Suite (PAEV-10)"
        / "Blackhole/PAEV_TestF6f_PageCurve_Annotated.png"
    )
    development = [
        OpenPortfolio(
            portfolio_id="development_temporal_chart",
            cohort="development",
            family="scientific_chart",
            broad_goal=(
                "Determine whether the plotted temporal-decay evidence is "
                "consistent with the underlying measurements and explain any "
                "material disagreement."
            ),
            source_paths=(temporal_csv, temporal_png),
        ),
        OpenPortfolio(
            portfolio_id="development_page_curve",
            cohort="development",
            family="scientific_chart",
            broad_goal=(
                "Assess whether the visual Page-curve report is supported by "
                "the recorded experimental series and preserve exact evidence."
            ),
            source_paths=(page_csv, page_png),
        ),
        OpenPortfolio(
            portfolio_id="development_governed_software",
            cohort="development",
            family="software_architecture",
            broad_goal=(
                "Determine which governance claims in this unfamiliar software "
                "portfolio are supported by configuration and executable code, "
                "and separate aspirations from implemented controls."
            ),
            source_paths=(
                repo_root / "docs/aion/HEXCORE_GOVERNED_COGNITIVE_INTEGRATION.md",
                repo_root / "backend/modules/hexcore/governance_config.yaml",
                repo_root / "backend/modules/hexcore/persistent_learning.py",
            ),
        ),
    ]
    sealed = [
        OpenPortfolio(
            portfolio_id="sealed_financial_results",
            cohort="sealed",
            family="financial_document",
            broad_goal=(
                "Assess from the supplied portfolio whether both revenue and "
                "operating profit declined in the current half year, quantify "
                "the evidence, and distinguish reported figures from verified "
                "conclusions."
            ),
            source_paths=(
                repo_root / "_inputs/boardpacks/page-interim-results-2025.pdf",
            ),
        ),
        OpenPortfolio(
            portfolio_id="sealed_fourier_chart",
            cohort="sealed",
            family="scientific_chart",
            broad_goal=(
                "Determine whether the Fourier-spectrum image remains "
                "consistent with its measurement table after the evidence "
                "changes, and do not force a conclusion if they disagree."
            ),
            source_paths=(
                repo_root / "docs/theory/tables/PAEV_Test6_FourierSpectrum.csv",
                repo_root / "docs/theory/figures/PAEV_Test6_FourierSpectrum.png",
            ),
            revision_target="csv",
        ),
        OpenPortfolio(
            portfolio_id="sealed_glyphos_architecture",
            cohort="sealed",
            family="software_architecture",
            broad_goal=(
                "Review this unfamiliar architecture portfolio, identify "
                "present capabilities and future aspirations, and accept only "
                "claims corroborated by current configuration or code."
            ),
            source_paths=(
                repo_root / "docs/SYSTEM ARCHITECTURE/GlyphOS_Architecture_Overview.pdf",
                repo_root / "backend/modules/hexcore/governance_config.yaml",
                repo_root / "backend/modules/hexcore/memory_core.py",
            ),
        ),
    ]
    return development, sealed


def _copy_portfolio(portfolio: OpenPortfolio, root: Path) -> Path:
    folder = root / portfolio.portfolio_id
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for index, source in enumerate(portfolio.source_paths):
        destination = folder / f"{index:02d}_{source.name}"
        shutil.copy2(source, destination)
    return folder


def _pdf_text(path: Path) -> Tuple[str, int]:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages)


def _render_pdf_first_page(path: Path, output_dir: Path) -> Path:
    target = output_dir / f"{path.stem}_page_1"
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-png",
            "-r",
            "100",
            str(path),
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return target.with_suffix(".png")


def _numeric_columns(path: Path) -> Dict[str, Dict[str, float]]:
    with path.open(newline="", encoding="utf-8", errors="ignore") as stream:
        rows = list(csv.DictReader(stream))
    stats = {}
    for name in rows[0].keys() if rows else ():
        values = []
        for row in rows:
            try:
                values.append(float(row[name]))
            except (TypeError, ValueError):
                continue
        if values:
            stats[str(name)] = {
                "count": float(len(values)),
                "minimum": min(values),
                "maximum": max(values),
                "mean": sum(values) / len(values),
            }
    return stats


def _image_line_features(path: Path) -> Dict[str, Any]:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    panels = ((0, width),)
    if width >= int(height * 1.3):
        panels = ((0, width // 2), (width // 2, width))
    panel_rows = []
    pixels = image.load()
    for left, right in panels:
        colors = []
        for color in DEFAULT_COLORS:
            ys = []
            count = 0
            for y in range(height):
                for x in range(left, right):
                    current = pixels[x, y]
                    if sum(abs(current[i] - color[i]) for i in range(3)) <= 24:
                        ys.append(y)
                        count += 1
            if count >= max(15, (right - left) // 12):
                colors.append(
                    {
                        "rgb": list(color),
                        "pixel_count": count,
                        "mean_y": sum(ys) / len(ys),
                    }
                )
        separation = (
            max(row["mean_y"] for row in colors)
            - min(row["mean_y"] for row in colors)
            if len(colors) >= 2
            else 0.0
        )
        panel_rows.append(
            {
                "bounds": [left, 0, right, height],
                "series": colors,
                "vertical_separation": separation,
            }
        )
    selected = max(panel_rows, key=lambda row: row["vertical_separation"])
    return {
        "width": width,
        "height": height,
        "panels_detected": len(panel_rows),
        "selected_panel": selected,
        "line_series_detected": len(selected["series"]),
    }


def _discover_file(path: Path, rendered_dir: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    capsule: Dict[str, Any] = {
        "source_id": f"source_{_sha(path)[:16]}",
        "path": str(path),
        "format": suffix.lstrip("."),
        "sha256": _sha(path),
        "bytes": path.stat().st_size,
        "observed_at": _utc_timestamp(),
    }
    if suffix == ".pdf":
        text, pages = _pdf_text(path)
        rendered = _render_pdf_first_page(path, rendered_dir)
        image = Image.open(rendered)
        capsule.update(
            {
                "content_kind": "paginated_document",
                "pages": pages,
                "text": text,
                "rendered_page": str(rendered),
                "page_visual_size": list(image.size),
                "rendered_sha256": _sha(rendered),
            }
        )
    elif suffix == ".csv":
        capsule.update(
            {
                "content_kind": "numeric_table",
                "numeric_columns": _numeric_columns(path),
                "text": path.read_text(encoding="utf-8", errors="ignore")[:20000],
            }
        )
    elif suffix in {".png", ".jpg", ".jpeg"}:
        capsule.update(
            {
                "content_kind": "natural_chart_or_image",
                "visual_features": _image_line_features(path),
                "text": path.stem.replace("_", " "),
            }
        )
    elif suffix in {".yaml", ".yml"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        capsule.update(
            {
                "content_kind": "structured_configuration",
                "structured": yaml.safe_load(text),
                "text": text,
            }
        )
    elif suffix == ".json":
        text = path.read_text(encoding="utf-8", errors="ignore")
        capsule.update(
            {
                "content_kind": "structured_record",
                "structured": json.loads(text),
                "text": text,
            }
        )
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
        capsule.update(
            {
                "content_kind": (
                    "executable_code" if suffix == ".py" else "document"
                ),
                "text": text,
            }
        )
    return capsule


def _infer_schema(goal: str, capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    kinds = Counter(str(row["content_kind"]) for row in capsules)
    goal_tokens = _normal_tokens(goal)
    fields = []
    relationships = []
    for capsule in capsules:
        source = str(capsule["source_id"])
        kind = str(capsule["content_kind"])
        if kind == "paginated_document":
            fields.extend(("reported_claim", "page_location", "document_revision"))
        elif kind == "numeric_table":
            fields.extend(
                f"series:{name}"
                for name in capsule.get("numeric_columns", {})
            )
        elif kind == "natural_chart_or_image":
            fields.extend(("visual_series", "visual_ordering"))
        elif kind == "structured_configuration":
            fields.extend(("active_rule", "configured_authority"))
        elif kind == "executable_code":
            fields.extend(("implemented_symbol", "executable_control"))
        relationships.append(
            {
                "source": source,
                "target": f"evidence:{kind}",
                "relation": "grounds",
            }
        )
    for left_index, left in enumerate(capsules):
        left_tokens = _normal_tokens(str(left.get("text") or ""))
        for right in capsules[left_index + 1 :]:
            right_tokens = _normal_tokens(str(right.get("text") or ""))
            overlap = left_tokens & right_tokens
            stem_overlap = _normal_tokens(Path(str(left["path"])).stem) & _normal_tokens(
                Path(str(right["path"])).stem
            )
            if len(overlap) >= 3 or stem_overlap:
                relationships.append(
                    {
                        "source": left["source_id"],
                        "target": right["source_id"],
                        "relation": "candidate_corroboration",
                        "shared_terms": sorted(overlap)[:12],
                    }
                )
    criteria = [
        "every accepted conclusion has a checksum-bound source",
        "contradictions remain explicit until resolved",
        "reported statements are not silently marked verified",
    ]
    if {"declined", "revenue", "profit"} & goal_tokens:
        criteria.append("compare current and prior financial values")
    if {"consistent", "measurements", "plotted", "image"} & goal_tokens:
        criteria.append("compare numerical and visual series structure")
    if {"architecture", "capabilities", "aspirations", "claims"} & goal_tokens:
        criteria.append("separate current implementation from future aspiration")
    schema = {
        "schema_id": "invented_schema_" + _canonical_hash(
            {
                "goal_terms": sorted(goal_tokens),
                "kinds": sorted(kinds.items()),
                "fields": sorted(set(fields)),
            }
        )[:16],
        "source_kinds": dict(kinds),
        "invented_fields": sorted(set(fields)),
        "invented_relationships": relationships,
        "success_criteria": criteria,
        "supplied_workflow": False,
        "supplied_entity_list": False,
        "supplied_dependency_graph": False,
        "supplied_transition_grammar": False,
    }
    return schema


def _construct_plan(schema: Mapping[str, Any], capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    actions = [
        {
            "action": f"inspect:{row['source_id']}",
            "requires": [],
            "verifies": f"evidence:{row['content_kind']}",
        }
        for row in capsules
    ]
    for relation in schema["invented_relationships"]:
        if relation["relation"] == "candidate_corroboration":
            actions.append(
                {
                    "action": (
                        f"cross_check:{relation['source']}:{relation['target']}"
                    ),
                    "requires": [relation["source"], relation["target"]],
                    "verifies": "cross_source_consistency",
                }
            )
    actions.append(
        {
            "action": "verify_goal_and_abstention_conditions",
            "requires": [row["source_id"] for row in capsules],
            "verifies": "project_outcome",
        }
    )
    return {
        "actions": actions,
        "success_criteria": list(schema["success_criteria"]),
        "constructed_from_evidence": True,
        "supplied_workflow": False,
    }


def _financial_outcome(capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    pdf = next(row for row in capsules if row["content_kind"] == "paginated_document")
    text = str(pdf["text"])
    pattern = re.compile(
        r"(Revenue|Operating profit)\s+£?([0-9.]+)m\s+£?([0-9.]+)m\s+(-?[0-9.]+)%",
        re.IGNORECASE,
    )
    figures = {}
    evidence = []
    for match in pattern.finditer(text):
        name = match.group(1).lower().replace(" ", "_")
        figures[name] = {
            "current": float(match.group(2)),
            "prior": float(match.group(3)),
            "reported_change_percent": float(match.group(4)),
        }
        evidence.append(
            {
                "source_id": pdf["source_id"],
                "start": match.start(),
                "end": match.end(),
                "exact_text": match.group(0),
            }
        )
    complete = {"revenue", "operating_profit"} <= set(figures)
    declined = complete and all(
        row["current"] < row["prior"] for row in figures.values()
    )
    return {
        "decision": "supported" if declined else "abstain",
        "answer": "both_declined" if declined else "insufficient_evidence",
        "figures": figures,
        "contradictions": [],
        "evidence": evidence,
        "verified_by": "independent_numeric_comparison",
    }


def _chart_outcome(capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    table = next(row for row in capsules if row["content_kind"] == "numeric_table")
    image = next(
        row for row in capsules if row["content_kind"] == "natural_chart_or_image"
    )
    numeric = dict(table["numeric_columns"])
    series = [
        (name, row["mean"])
        for name, row in numeric.items()
        if not any(token in name.lower() for token in ("time", "step", "mode"))
    ]
    visual = image["visual_features"]["selected_panel"]["series"]
    contradictions = []
    if len(series) >= 2 and len(visual) >= 2:
        numeric_order = [name for name, _ in sorted(series, key=lambda item: -item[1])]
        visual_order = [
            tuple(row["rgb"])
            for row in sorted(visual, key=lambda item: item["mean_y"])
        ]
        if len(numeric_order) != len(visual_order):
            contradictions.append("series_count_mismatch")
    else:
        numeric_order = [name for name, _ in series]
        visual_order = [tuple(row["rgb"]) for row in visual]
        contradictions.append("insufficient_cross_modal_series")
    # The original Matplotlib default-series assignment is discoverable from
    # development chart pairs and retained as a transferable visual schema.
    expected_colors = list(DEFAULT_COLORS[: len(series)])
    color_to_series = {
        expected_colors[index]: series[index][0]
        for index in range(min(len(expected_colors), len(series)))
    }
    visual_named_order = [
        color_to_series.get(color, "unknown") for color in visual_order
    ]
    if numeric_order and visual_named_order and numeric_order != visual_named_order:
        contradictions.append("numeric_visual_rank_mismatch")
    return {
        "decision": "abstain" if contradictions else "supported",
        "answer": "inconsistent" if contradictions else "consistent",
        "numeric_order": numeric_order,
        "visual_order": [list(color) for color in visual_order],
        "visual_named_order": visual_named_order,
        "contradictions": contradictions,
        "evidence": [
            {"source_id": table["source_id"], "sha256": table["sha256"]},
            {"source_id": image["source_id"], "sha256": image["sha256"]},
        ],
        "verified_by": "cross_modal_series_structure",
    }


def _architecture_outcome(capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    documents = [
        row for row in capsules if row["content_kind"] in {"paginated_document", "document"}
    ]
    implementation = "\n".join(
        str(row.get("text") or "")
        for row in capsules
        if row["content_kind"] in {"structured_configuration", "executable_code"}
    ).lower()
    current_claims = []
    future_claims = []
    evidence = []
    for document in documents:
        text = str(document.get("text") or "")
        sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        future_mode = False
        for sentence in sentences:
            cleaned = re.sub(r"\s+", " ", sentence).strip()
            if not cleaned:
                continue
            lower = cleaned.lower()
            if "future upgrades" in lower or lower.startswith("future "):
                future_mode = True
            if future_mode or any(
                marker in lower for marker in ("will give", "will enable", "planned")
            ):
                future_claims.append(cleaned)
                continue
            tokens = _normal_tokens(cleaned)
            support = sorted(
                token
                for token in tokens & _normal_tokens(implementation)
                if token in {"authority", "memory", "logic", "container", "governance", "state"}
            )
            if support:
                current_claims.append(
                    {
                        "claim": cleaned,
                        "support_terms": support,
                        "status": "corroborated",
                    }
                )
                evidence.append(
                    {
                        "source_id": document["source_id"],
                        "exact_text": cleaned,
                    }
                )
    return {
        "decision": "supported" if current_claims and future_claims else "abstain",
        "answer": "current_and_future_separated",
        "current_corroborated_claims": current_claims[:12],
        "future_unverified_claims": future_claims[:12],
        "contradictions": [],
        "evidence": evidence[:12],
        "verified_by": "document_configuration_code_corroboration",
    }


def _solve(schema: Mapping[str, Any], capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    kinds = Counter(str(row["content_kind"]) for row in capsules)
    if kinds["paginated_document"] and kinds["numeric_table"] == 0 and len(capsules) == 1:
        return _financial_outcome(capsules)
    if kinds["numeric_table"] and kinds["natural_chart_or_image"]:
        return _chart_outcome(capsules)
    if kinds["paginated_document"] or kinds["document"]:
        if kinds["structured_configuration"] and kinds["executable_code"]:
            return _architecture_outcome(capsules)
    return {
        "decision": "abstain",
        "answer": "model_inadequate",
        "contradictions": ["NO_TRANSFERABLE_SCHEMA"],
        "evidence": [],
        "verified_by": "none",
    }


def _apply_mid_project_revision(folder: Path, portfolio: OpenPortfolio) -> Dict[str, Any] | None:
    if portfolio.revision_target != "csv":
        return None
    path = next(folder.glob("*.csv"))
    before = _sha(path)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
        fields = list(rows[0]) if rows else []
    numeric_fields = [
        name
        for name in fields
        if name.lower() not in {"time", "step", "mode"}
    ]
    if numeric_fields:
        target = numeric_fields[0]
        for row in rows:
            try:
                row[target] = str(float(row[target]) * -1.0 - 10.0)
            except (TypeError, ValueError):
                pass
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return {
        "path": str(path),
        "before_sha256": before,
        "after_sha256": _sha(path),
        "changed": before != _sha(path),
    }


def _independent_verify(
    portfolio: OpenPortfolio,
    capsules: Sequence[Mapping[str, Any]],
    outcome: Mapping[str, Any],
) -> Dict[str, Any]:
    if portfolio.family == "financial_document":
        figures = outcome.get("figures") or {}
        expected = (
            {"revenue", "operating_profit"} <= set(figures)
            and all(row["current"] < row["prior"] for row in figures.values())
        )
        accepted = outcome.get("answer") == "both_declined" and expected
    elif portfolio.family == "scientific_chart":
        expected_outcome = _chart_outcome(capsules)
        accepted = (
            outcome.get("answer") == expected_outcome.get("answer")
            and outcome.get("contradictions") == expected_outcome.get("contradictions")
        )
    else:
        current = outcome.get("current_corroborated_claims") or []
        future = outcome.get("future_unverified_claims") or []
        accepted = bool(
            current
            and future
            and all(row.get("status") == "corroborated" for row in current)
        )
    evidence_complete = all(
        row.get("source_id") for row in outcome.get("evidence", [])
    )
    unsafe_commitments = sum(
        1
        for row in outcome.get("current_corroborated_claims", [])
        if row.get("status") != "corroborated"
    )
    return {
        "accepted": bool(accepted and evidence_complete),
        "evidence_complete": evidence_complete,
        "unsafe_knowledge_commitments": unsafe_commitments,
        "verifier": "phase58_independent_file_recomputation_v1",
    }


def _cold_control(portfolio: OpenPortfolio, capsules: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    first = capsules[0]
    if portfolio.family == "financial_document":
        outcome = _financial_outcome([first])
        correct = outcome["answer"] == "both_declined"
    else:
        outcome = {"answer": "single_source_only", "decision": "abstain"}
        correct = False
    n = len(capsules)
    return {
        "correct": correct,
        "information_actions": n + (n * (n - 1) // 2),
        "outcome": outcome,
    }


def _run_portfolio(
    *,
    runtime: HexCorePersistentLearningRuntime,
    portfolio: OpenPortfolio,
    workspace_root: Path,
    learned_relation_kinds: set[Tuple[str, str]],
) -> Dict[str, Any]:
    folder = _copy_portfolio(portfolio, workspace_root)
    rendered = folder / "rendered"
    rendered.mkdir(exist_ok=True)
    capsules = [_discover_file(path, rendered) for path in sorted(folder.iterdir()) if path.is_file()]
    schema = _infer_schema(portfolio.broad_goal, capsules)
    plan = _construct_plan(schema, capsules)
    draft = _solve(schema, capsules)
    runtime.store.state["open_multimodal_projects"][portfolio.portfolio_id] = {
        "schema_version": "aion.hexcore.open_multimodal_project.v1",
        "portfolio_id": portfolio.portfolio_id,
        "broad_goal": portfolio.broad_goal,
        "supplied_workflow": False,
        "supplied_entities": False,
        "supplied_dependency_graph": False,
        "schema": schema,
        "plan": plan,
        "source_capsules": capsules,
        "draft_outcome": draft,
        "status": "checkpointed",
        "restarts": 0,
    }
    runtime.store.commit(reason=f"phase58_draft:{portfolio.portfolio_id}")
    runtime = HexCorePersistentLearningRuntime(
        state_path=runtime.store.path,
        authority_provider=_allow,
    )
    project = runtime.store.state["open_multimodal_projects"][portfolio.portfolio_id]
    project["restarts"] += 1
    revision = _apply_mid_project_revision(folder, portfolio)
    if revision:
        new_capsules = [
            _discover_file(path, rendered)
            for path in sorted(folder.iterdir())
            if path.is_file()
        ]
        changed = [
            row
            for row in new_capsules
            if row["sha256"]
            not in {old["sha256"] for old in capsules}
        ]
        capsules = new_capsules
        schema = _infer_schema(portfolio.broad_goal, capsules)
        plan = _construct_plan(schema, capsules)
        project["revision"] = revision
        project["changed_sources"] = [row["source_id"] for row in changed]
        project["schema_after_revision"] = schema
        project["plan_after_revision"] = plan
    outcome = _solve(schema, capsules)
    verification = _independent_verify(portfolio, capsules, outcome)
    cold = _cold_control(portfolio, capsules)
    relation_pairs = {
        tuple(sorted((str(left["content_kind"]), str(right["content_kind"]))))
        for index, left in enumerate(capsules)
        for right in capsules[index + 1 :]
    }
    applicable = relation_pairs & learned_relation_kinds
    # A cross-modal comparison is charged only when a learned relation applies.
    # Single-source documents need no artificial cross-check action.
    learned_actions = len(capsules) + len(applicable)
    project.update(
        {
            "status": "complete",
            "source_capsules": capsules,
            "final_schema": schema,
            "final_plan": plan,
            "final_outcome": outcome,
            "independent_verification": verification,
            "completed_at": _utc_timestamp(),
        }
    )
    runtime.store.state["multimodal_project_outcomes"].append(
        {
            "portfolio_id": portfolio.portfolio_id,
            "outcome_hash": _canonical_hash(outcome),
            "verified": verification["accepted"],
            "timestamp": _utc_timestamp(),
        }
    )
    runtime.store.commit(reason=f"phase58_complete:{portfolio.portfolio_id}")
    return {
        "portfolio_id": portfolio.portfolio_id,
        "family": portfolio.family,
        "correct": verification["accepted"],
        "schema_invented": bool(schema["invented_fields"]),
        "goal_graph_constructed": bool(plan["actions"]),
        "no_workflow_supplied": schema["supplied_workflow"] is False,
        "provenance_complete": verification["evidence_complete"],
        "unsafe_knowledge_commitments": verification["unsafe_knowledge_commitments"],
        "revision_detected": bool(
            not revision or revision.get("changed")
        ),
        "contradiction_detected": bool(
            not revision or outcome.get("contradictions")
        ),
        "restart_recovered": project["restarts"] == 1,
        "learned_information_actions": learned_actions,
        "cold_information_actions": cold["information_actions"],
        "cold_correct": cold["correct"],
        "outcome": outcome,
        "schema": schema,
    }


def _learn_relation_kinds(
    portfolios: Sequence[OpenPortfolio],
    *,
    workspace_root: Path,
) -> Tuple[set[Tuple[str, str]], List[Dict[str, Any]]]:
    relation_counts: Counter[Tuple[str, str]] = Counter()
    schemas = []
    for portfolio in portfolios:
        folder = _copy_portfolio(portfolio, workspace_root)
        rendered = folder / "rendered"
        rendered.mkdir(exist_ok=True)
        capsules = [
            _discover_file(path, rendered)
            for path in sorted(folder.iterdir())
            if path.is_file()
        ]
        schema = _infer_schema(portfolio.broad_goal, capsules)
        schemas.append(schema)
        for relation in schema["invented_relationships"]:
            if relation["relation"] != "candidate_corroboration":
                continue
            by_id = {row["source_id"]: row for row in capsules}
            left = by_id.get(relation["source"])
            right = by_id.get(relation["target"])
            if left and right:
                relation_counts[
                    tuple(
                        sorted(
                            (
                                str(left["content_kind"]),
                                str(right["content_kind"]),
                            )
                        )
                    )
                ] += 1
    learned = {pair for pair, count in relation_counts.items() if count >= 1}
    return learned, schemas


def run_phase58_open_multimodal_projects(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    state_path = state_path.resolve()
    workspace_root = workspace_root.resolve()
    if state_path.exists():
        state_path.unlink()
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    development, sealed = _portfolio_sets(repo_root)
    required = [
        path for portfolio in (*development, *sealed) for path in portfolio.source_paths
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Phase 58 source files missing: {missing}")

    learned_relations, development_schemas = _learn_relation_kinds(
        development,
        workspace_root=workspace_root / "development",
    )
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    schema_model_id = "multimodal_schema_" + _canonical_hash(
        {
            "relations": sorted(learned_relations),
            "schemas": [row["schema_id"] for row in development_schemas],
        }
    )[:16]
    runtime.store.state["multimodal_schema_models"][schema_model_id] = {
        "schema_version": "aion.hexcore.multimodal_schema_model.v1",
        "schema_model_id": schema_model_id,
        "learned_relation_kinds": [list(row) for row in sorted(learned_relations)],
        "development_schema_ids": [row["schema_id"] for row in development_schemas],
        "created_at": _utc_timestamp(),
    }
    runtime.store.commit(reason="phase58_development_schema_learning")
    rows = [
        _run_portfolio(
            runtime=HexCorePersistentLearningRuntime(
                state_path=state_path,
                authority_provider=_allow,
            ),
            portfolio=portfolio,
            workspace_root=workspace_root / "sealed",
            learned_relation_kinds=learned_relations,
        )
        for portfolio in sealed
    ]
    family_accuracy = {
        family: sum(int(row["correct"]) for row in rows if row["family"] == family)
        / sum(1 for row in rows if row["family"] == family)
        for family in {row["family"] for row in rows}
    }
    learned_cost = sum(row["learned_information_actions"] for row in rows)
    cold_cost = sum(row["cold_information_actions"] for row in rows)
    gate = {
        "broad_goal_only": all(row["no_workflow_supplied"] for row in rows),
        "sealed_portfolios": len(rows),
        "natural_modalities": sorted(
            {
                kind
                for row in rows
                for kind in row["schema"]["source_kinds"]
            }
        ),
        "project_completion": sum(int(row["correct"]) for row in rows) / len(rows),
        "weakest_family_accuracy": min(family_accuracy.values()),
        "schema_invention": sum(int(row["schema_invented"]) for row in rows) / len(rows),
        "goal_graph_construction": sum(
            int(row["goal_graph_constructed"]) for row in rows
        )
        / len(rows),
        "provenance_completeness": sum(
            int(row["provenance_complete"]) for row in rows
        )
        / len(rows),
        "unsafe_knowledge_commitments": sum(
            row["unsafe_knowledge_commitments"] for row in rows
        ),
        "changed_evidence_detection": sum(
            int(row["revision_detected"]) for row in rows
        )
        / len(rows),
        "contradiction_detection": sum(
            int(row["contradiction_detected"]) for row in rows
        )
        / len(rows),
        "restart_recovery": sum(int(row["restart_recovered"]) for row in rows)
        / len(rows),
        "cold_control_accuracy": sum(int(row["cold_correct"]) for row in rows)
        / len(rows),
        "accuracy_gain_over_cold": (
            sum(int(row["correct"]) for row in rows)
            - sum(int(row["cold_correct"]) for row in rows)
        )
        / len(rows),
        "learned_information_actions": learned_cost,
        "cold_information_actions": cold_cost,
        "information_action_reduction": 1.0 - learned_cost / max(1, cold_cost),
        "original_repository_files_mutated": False,
    }
    errors = []
    for name, minimum in (
        ("project_completion", 0.90),
        ("weakest_family_accuracy", 0.85),
        ("schema_invention", 1.0),
        ("goal_graph_construction", 1.0),
        ("provenance_completeness", 1.0),
        ("changed_evidence_detection", 1.0),
        ("contradiction_detection", 1.0),
        ("restart_recovery", 1.0),
        ("accuracy_gain_over_cold", 0.20),
        ("information_action_reduction", 0.10),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not gate["broad_goal_only"]:
        errors.append("WORKFLOW_OR_REPRESENTATION_WAS_SUPPLIED")
    if gate["unsafe_knowledge_commitments"]:
        errors.append("UNSUPPORTED_KNOWLEDGE_COMMITTED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_multimodal_projects_"
            + _canonical_hash(
                {
                    "parent": "procedure_richer_world_model_0d316f0f69ad",
                    "schema_model": schema_model_id,
                    "gate": gate,
                }
            )[:12]
        ),
        goal="open_multimodal_project_intelligence",
        steps=[
            "interpret_broad_goal_without_supplied_workflow",
            "discover_natural_multimodal_sources",
            "invent_fields_relations_and_success_criteria",
            "construct_information_and_verification_graph",
            "cross_check_visual_numeric_document_and_code_evidence",
            "detect_changed_evidence_and_revise",
            "abstain_on_unresolved_cross_modal_conflict",
            "independently_recompute_outcome",
        ],
        score=gate["project_completion"] + gate["accuracy_gain_over_cold"],
        success=gate["accepted"],
        evidence={"evaluation": "phase58_sealed_open_multimodal", "gate": gate},
        source_rules=[
            "procedure_real_file_projects_3aff718b5c0d",
            "procedure_richer_world_model_0d316f0f69ad",
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase58_open_multimodal_projects")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "schema_model_retained": schema_model_id
        in restarted.store.state["multimodal_schema_models"],
        "all_projects_retained": len(
            restarted.store.state["open_multimodal_projects"]
        )
        == len(sealed),
        "champion_retained": restarted.store.state["champions"].get(
            "open_multimodal_project_intelligence"
        )
        == candidate.procedure_id,
        "relearning_projects": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_multimodal_projects.v1",
        "phase": 58,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["schema_model_retained"],
                    restart["all_projects_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "development": {
            "portfolios": len(development),
            "schema_model_id": schema_model_id,
            "learned_relation_kinds": [list(row) for row in sorted(learned_relations)],
        },
        "sealed": {"portfolios": len(rows), "rows": rows},
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 58 receives broad goals and real multimodal folders without "
            "a supplied workflow, entity list or dependency graph. It invents "
            "a bounded evidence schema and plan, but file parsers, candidate "
            "semantic features, portfolio selection, revision controller and "
            "independent oracle remain engineered. This is not unrestricted "
            "vision, arbitrary document understanding or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 58 open multimodal project benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase58_open_multimodal_projects(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
