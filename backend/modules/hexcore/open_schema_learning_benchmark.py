from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.aion_equities.document_ingestion_runtime import (
    DocumentIngestionRuntime,
)
from backend.modules.aion_equities.document_text_loader import (
    DocumentTextLoader,
)
from backend.modules.aion_equities.source_document_store import (
    SourceDocumentStore,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


DEVELOPMENT_DOMAINS = (
    "river archive",
    "ceramic workshop",
    "forest survey",
)
SEALED_DOMAINS = (
    "orbital greenhouse",
    "linguistic conservatory",
    "deep sea observatory",
    "nomadic energy cooperative",
    "heritage seed bank",
    "polar communications station",
)
ENTITY_VOCABULARIES = (
    ("avel", "brin", "coda", "drel", "eska", "fenn"),
    ("gora", "havel", "iora", "juno", "kest", "luma"),
    ("moro", "nira", "orun", "pava", "quin", "rhel"),
    ("sora", "tavin", "ulma", "voro", "wren", "xara"),
    ("yori", "zenn", "arvo", "bela", "cair", "duma"),
    ("eira", "faro", "glen", "hira", "isla", "jori"),
)


@dataclass(frozen=True)
class Proposition:
    entity: str
    state: str

    @property
    def key(self) -> str:
        return f"{self.entity}::{self.state}"


@dataclass(frozen=True)
class Rule:
    antecedents: Tuple[Proposition, ...]
    operator: str
    consequence: Proposition

    @property
    def signature(self) -> Dict[str, Any]:
        return {
            "antecedent_operator": self.operator,
            "antecedent_arity": len(self.antecedents),
            "consequence_arity": 1,
            "temporal_direction": "forward",
        }

    @property
    def schema_id(self) -> str:
        return "schema_" + _canonical_hash(self.signature)[:12]


@dataclass(frozen=True)
class GoalContract:
    operator: str
    requirements: Tuple[Proposition, ...]
    threshold: int = 0


@dataclass(frozen=True)
class SchemaProject:
    project_id: str
    domain: str
    objective: str
    facts: Tuple[Proposition, ...]
    rules: Tuple[Rule, ...]
    goal: GoalContract
    expected_status: str
    missing_rule: Rule | None
    style: int


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase41_open_schema_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normal(text: Any) -> str:
    value = re.sub(r"[^a-z0-9 -]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", value).strip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prop_text(prop: Proposition, style: int = 0) -> str:
    forms = (
        f"{prop.entity} is {prop.state}",
        f"{prop.entity} remains {prop.state}",
        f"{prop.entity} has status {prop.state}",
    )
    return forms[style % len(forms)]


def _parse_prop(text: str) -> Proposition | None:
    clean = _normal(text)
    for pattern in (
        r"(.+?) is ([a-z-]+)$",
        r"(.+?) remains ([a-z-]+)$",
        r"(.+?) has status ([a-z-]+)$",
    ):
        match = re.match(pattern, clean)
        if match:
            return Proposition(_normal(match.group(1)), _normal(match.group(2)))
    return None


def _rule_text(rule: Rule, style: int) -> str:
    antecedents = [_prop_text(prop, style) for prop in rule.antecedents]
    consequence = _prop_text(rule.consequence, style + 1)
    if rule.operator == "all":
        joined = " and ".join(antecedents)
        forms = (
            f"If {joined}, then {consequence}.",
            f"{consequence.capitalize()} follows provided that {joined}.",
            f"Once {joined}, the record shows {consequence}.",
        )
    else:
        joined = " or ".join(antecedents)
        forms = (
            f"If either {joined}, then {consequence}.",
            f"{consequence.capitalize()} follows when any of {joined} holds.",
            f"Whenever one of {joined} is established, {consequence}.",
        )
    return forms[style % len(forms)]


def _goal_text(goal: GoalContract, style: int) -> str:
    props = [_prop_text(prop, style) for prop in goal.requirements]
    if goal.operator == "all":
        return (
            "The final recommendation requires all of these conditions: "
            + "; ".join(props)
            + "."
        )
    if goal.operator == "any":
        return (
            "Any one of the following is sufficient for a positive finding: "
            + "; ".join(props)
            + "."
        )
    if goal.operator == "threshold":
        return (
            f"At least {goal.threshold} of the following must hold: "
            + "; ".join(props)
            + "."
        )
    return (
        "The explanation must establish, in order: "
        + "; then ".join(props)
        + "."
    )


def _project(
    index: int,
    *,
    domain: str,
    vocabulary: Sequence[str],
    development: bool,
) -> SchemaProject:
    e0, e1, e2, e3, e4, e5 = vocabulary
    p0 = Proposition(e0, "awake")
    p1 = Proposition(e1, "open")
    p2 = Proposition(e2, "stable")
    p3 = Proposition(e3, "ready")
    p4 = Proposition(e4, "clear")
    decoy = Proposition(e5, "present")
    rules = (
        Rule((p0,), "all", p1),
        Rule((p1,), "all", p2),
        Rule((p0, p2), "all", p3),
        Rule((p1, decoy), "any", p4),
    )
    goal_kind = ("all", "any", "threshold", "sequence")[index % 4]
    goal = {
        "all": GoalContract("all", (p3, p4)),
        # Both alternatives depend on the p1 -> p2 relation, making a missing
        # relation decision-relevant rather than merely interesting.
        "any": GoalContract("any", (p2, p3)),
        "threshold": GoalContract("threshold", (p2, p3, p4), 2),
        "sequence": GoalContract("sequence", (p1, p2, p3)),
    }[goal_kind]
    case = index % 5
    missing_rule = rules[1] if case == 0 else None
    active_rules = tuple(rule for rule in rules if rule != missing_rule)
    facts: Tuple[Proposition, ...] = (p0, decoy)
    expected = "supported"
    if case == 1:
        # Explicit contradictory state means false, not merely unknown.
        conflicting = tuple(
            Proposition(requirement.entity, f"not-{requirement.state}")
            for requirement in goal.requirements
        )
        facts = (p0, decoy, *conflicting)
        active_rules = tuple(
            rule
            for rule in active_rules
            if rule.consequence.entity
            not in {requirement.entity for requirement in goal.requirements}
        )
        expected = "unsupported"
    elif missing_rule is not None:
        expected = "supported_after_query"
    return SchemaProject(
        project_id=(
            f"phase41:{'development' if development else 'sealed'}:{index:03d}"
        ),
        domain=domain,
        objective=(
            f"Determine whether the unfamiliar {domain} satisfies its "
            "governing objective. Infer any relation and decision schemas, "
            "construct a cited explanation, and identify precisely what "
            "knowledge is missing rather than guessing."
        ),
        facts=facts,
        rules=active_rules,
        goal=goal,
        expected_status=expected,
        missing_rule=missing_rule,
        style=(index // 3) % 3,
    )


def _projects(
    count: int,
    *,
    development: bool,
) -> List[SchemaProject]:
    domains = DEVELOPMENT_DOMAINS if development else SEALED_DOMAINS
    rows = []
    for index in range(count):
        domain = domains[index % len(domains)]
        vocabulary = ENTITY_VOCABULARIES[index % len(ENTITY_VOCABULARIES)]
        # Prefixes ensure no entity identity overlaps between development and
        # sealed projects even when a vocabulary family is reused.
        prefix = f"{'dev' if development else 'seal'}{index}-"
        rows.append(
            _project(
                index,
                domain=domain,
                vocabulary=tuple(prefix + token for token in vocabulary),
                development=development,
            )
        )
    return rows


def _register(
    ingestion: DocumentIngestionRuntime,
    artifact_dir: Path,
    project: SchemaProject,
    *,
    name: str,
    text: str,
    kind: str,
    authority: str = "independent_auditor",
) -> Dict[str, Any]:
    directory = artifact_dir / project.project_id.replace(":", "_")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    checksum = _sha(text)
    return ingestion.register_source_document(
        company_ref=project.project_id,
        source_type="other",
        fiscal_period_ref="phase41",
        source_file_ref=str(path),
        parsed_text_ref=str(path),
        published_at="2026-07-29T00:00:00Z",
        provenance_hash=f"sha256:{checksum}",
        document_id=f"{project.project_id}/document/{name}",
        ingestion_status="parsed",
        payload_patch={
            "kind": kind,
            "authority": authority,
            "verified": True,
            "content_checksum": checksum,
        },
    )


def _install(
    project: SchemaProject,
    *,
    ingestion: DocumentIngestionRuntime,
    artifact_dir: Path,
    include_clarification: bool = False,
) -> List[Dict[str, Any]]:
    fact_text = " ".join(
        (
            "The independent survey records "
            + _prop_text(prop, project.style)
            + "."
        )
        for prop in project.facts
    )
    documents = [
        _register(
            ingestion,
            artifact_dir,
            project,
            name="observations",
            text=fact_text,
            kind="facts",
        ),
        _register(
            ingestion,
            artifact_dir,
            project,
            name="governing_objective",
            text=(
                "The governing council issued this decision contract. "
                + _goal_text(project.goal, project.style)
            ),
            kind="goal",
            authority="governing_board",
        ),
    ]
    for index, rule in enumerate(project.rules):
        documents.append(
            _register(
                ingestion,
                artifact_dir,
                project,
                name=f"relation_{index}",
                text=(
                    "A verified field manual states the following relation. "
                    + _rule_text(rule, project.style + index)
                ),
                kind="rule",
            )
        )
    if include_clarification and project.missing_rule is not None:
        documents.append(
            _register(
                ingestion,
                artifact_dir,
                project,
                name="verified_clarification",
                text=(
                    "The requested independent check established the missing "
                    "relation. "
                    + _rule_text(project.missing_rule, project.style + 2)
                ),
                kind="rule",
                authority="governing_board",
            )
        )
    return documents


def _loaded(
    documents: Sequence[Mapping[str, Any]],
    loader: DocumentTextLoader,
) -> List[Dict[str, Any]]:
    return [
        {
            "document": dict(document),
            "text": loader.load_text(
                parsed_text_ref=str(document.get("parsed_text_ref") or "")
            ),
        }
        for document in documents
    ]


def _split_props(text: str, operator: str) -> Tuple[Proposition, ...]:
    separator = r"\s+and\s+" if operator == "all" else r"\s+or\s+"
    clean = re.sub(r"^(either|any of|one of)\s+", "", text.strip(), flags=re.I)
    return tuple(
        prop
        for part in re.split(separator, clean, flags=re.I)
        if (prop := _parse_prop(part.strip())) is not None
    )


def _parse_rule(sentence: str) -> Rule | None:
    clean = sentence.strip().rstrip(".")
    patterns = (
        (r"If either (.+?), then (.+)$", "any", False),
        (r"If (.+?), then (.+)$", "all", False),
        (r"(.+?) follows when any of (.+?) holds$", "any", True),
        (r"(.+?) follows provided that (.+)$", "all", True),
        (r"Once (.+?), the record shows (.+)$", "all", False),
        (
            r"Whenever one of (.+?) is established, (.+)$",
            "any",
            False,
        ),
    )
    for raw, operator, reversed_order in patterns:
        match = re.search(raw, clean, flags=re.I)
        if not match:
            continue
        antecedent_text = (
            match.group(2) if reversed_order else match.group(1)
        )
        consequence_text = (
            match.group(1) if reversed_order else match.group(2)
        )
        antecedents = _split_props(antecedent_text, operator)
        consequence = _parse_prop(consequence_text)
        if antecedents and consequence:
            return Rule(antecedents, operator, consequence)
    return None


def _sentences(text: str) -> List[str]:
    return [
        value.strip()
        for value in re.split(r"(?<=[.!?])\s+", text.strip())
        if value.strip()
    ]


def _parse_facts(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    facts = []
    for row in rows:
        if row["document"].get("kind") != "facts":
            continue
        for index, sentence in enumerate(_sentences(str(row["text"])), start=1):
            match = re.search(r"records (.+)$", sentence.rstrip("."), re.I)
            if not match:
                continue
            prop = _parse_prop(match.group(1))
            if prop:
                facts.append(
                    {
                        "proposition": prop,
                        "document_id": row["document"]["document_id"],
                        "source_file_ref": row["document"]["source_file_ref"],
                        "provenance_hash": row["document"]["provenance_hash"],
                        "sentence": index,
                    }
                )
    return facts


def _parse_rules(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rules = []
    for row in rows:
        if row["document"].get("kind") != "rule":
            continue
        for index, sentence in enumerate(_sentences(str(row["text"])), start=1):
            parsed = _parse_rule(sentence)
            if parsed:
                rules.append(
                    {
                        "rule": parsed,
                        "document_id": row["document"]["document_id"],
                        "source_file_ref": row["document"]["source_file_ref"],
                        "provenance_hash": row["document"]["provenance_hash"],
                        "sentence": index,
                    }
                )
    return rules


def _parse_goal(rows: Sequence[Mapping[str, Any]]) -> GoalContract | None:
    text = next(
        str(row["text"])
        for row in rows
        if row["document"].get("kind") == "goal"
    )
    sentence = next(
        value
        for value in _sentences(text)
        if (
            "requires all" in value.lower()
            or "is sufficient" in value.lower()
            or "at least" in value.lower()
            or "in order:" in value.lower()
        )
    ).rstrip(".")
    if "requires all of these conditions:" in sentence.lower():
        tail = re.split(
            r"requires all of these conditions:",
            sentence,
            flags=re.I,
        )[1]
        operator, threshold = "all", 0
    elif "is sufficient for a positive finding:" in sentence.lower():
        tail = re.split(
            r"is sufficient for a positive finding:",
            sentence,
            flags=re.I,
        )[1]
        operator, threshold = "any", 0
    elif "at least" in sentence.lower():
        match = re.search(
            r"At least (\d+) of the following must hold:\s*(.+)$",
            sentence,
            re.I,
        )
        if not match:
            return None
        threshold, tail, operator = int(match.group(1)), match.group(2), "threshold"
    else:
        tail = re.split(r"in order:", sentence, flags=re.I)[1]
        operator, threshold = "sequence", 0
    parts = re.split(r";(?:\s*then)?\s*", tail)
    requirements = tuple(
        prop
        for part in parts
        if (prop := _parse_prop(part.strip())) is not None
    )
    return GoalContract(operator, requirements, threshold)


def _forward_chain(
    facts: Sequence[Mapping[str, Any]],
    rules: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    known: Dict[str, Dict[str, Any]] = {
        fact["proposition"].key: {
            "proposition": fact["proposition"],
            "depth": 0,
            "proof": [fact["document_id"]],
            "citation": {
                key: fact[key]
                for key in (
                    "document_id",
                    "source_file_ref",
                    "provenance_hash",
                    "sentence",
                )
            },
        }
        for fact in facts
    }
    applied = []
    changed = True
    while changed:
        changed = False
        for item in rules:
            rule: Rule = item["rule"]
            present = [
                antecedent.key in known
                for antecedent in rule.antecedents
            ]
            enabled = (
                all(present) if rule.operator == "all" else any(present)
            )
            if not enabled or rule.consequence.key in known:
                continue
            supporting = [
                known[antecedent.key]
                for antecedent in rule.antecedents
                if antecedent.key in known
            ]
            depth = max(row["depth"] for row in supporting) + 1
            proof = [
                ref
                for row in supporting
                for ref in row["proof"]
            ] + [item["document_id"]]
            known[rule.consequence.key] = {
                "proposition": rule.consequence,
                "depth": depth,
                "proof": list(dict.fromkeys(proof)),
                "citation": {
                    key: item[key]
                    for key in (
                        "document_id",
                        "source_file_ref",
                        "provenance_hash",
                        "sentence",
                    )
                },
            }
            applied.append(
                {
                    "schema_id": rule.schema_id,
                    "signature": rule.signature,
                    "antecedents": [
                        antecedent.key for antecedent in rule.antecedents
                    ],
                    "consequence": rule.consequence.key,
                    "depth": depth,
                    "document_id": item["document_id"],
                }
            )
            changed = True
    return known, applied


def _goal_status(
    goal: GoalContract,
    known: Mapping[str, Mapping[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    present = [requirement.key in known for requirement in goal.requirements]
    if goal.operator == "all":
        supported = all(present)
    elif goal.operator == "any":
        supported = any(present)
    elif goal.operator == "threshold":
        supported = sum(present) >= goal.threshold
    else:
        depths = [
            int(known[requirement.key]["depth"])
            for requirement in goal.requirements
            if requirement.key in known
        ]
        supported = (
            len(depths) == len(goal.requirements)
            and all(left < right for left, right in zip(depths, depths[1:]))
        )
    return supported, {
        "operator": goal.operator,
        "requirements": [prop.key for prop in goal.requirements],
        "present": present,
        "threshold": goal.threshold,
    }


def _missing_knowledge(
    goal: GoalContract,
    known: Mapping[str, Mapping[str, Any]],
    rules: Sequence[Mapping[str, Any]],
) -> List[Proposition]:
    producers: Dict[str, List[Rule]] = {}
    for item in rules:
        rule: Rule = item["rule"]
        producers.setdefault(rule.consequence.key, []).append(rule)
    known_entities = {
        row["proposition"].entity: row["proposition"].state
        for row in known.values()
        if int(row["depth"]) == 0
    }
    missing: Dict[str, Proposition] = {}
    visited: set[str] = set()

    def visit(prop: Proposition) -> None:
        if prop.key in known or prop.key in visited:
            return
        visited.add(prop.key)
        if prop.entity in known_entities:
            # A conflicting observed state is evidence of falsity, not absence.
            return
        candidates = producers.get(prop.key, [])
        if not candidates:
            missing[prop.key] = prop
            return
        for rule in candidates:
            unresolved = [
                antecedent
                for antecedent in rule.antecedents
                if antecedent.key not in known
            ]
            if rule.operator == "any" and len(unresolved) < len(rule.antecedents):
                continue
            for antecedent in unresolved:
                visit(antecedent)

    for requirement in goal.requirements:
        visit(requirement)
    return list(missing.values())


def _evaluate(
    project: SchemaProject,
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    facts = _parse_facts(rows)
    rules = _parse_rules(rows)
    goal = _parse_goal(rows)
    if goal is None:
        raise ValueError("goal schema could not be induced")
    known, applied = _forward_chain(facts, rules)
    supported, goal_trace = _goal_status(goal, known)
    missing = _missing_knowledge(goal, known, rules)
    if supported:
        status = "supported"
    elif missing:
        status = "unknown"
    else:
        status = "unsupported"
    schemas = {
        item["rule"].schema_id: item["rule"].signature
        for item in rules
    }
    citations = [
        row["citation"]
        for row in known.values()
        if row["proposition"].key in goal_trace["requirements"]
    ]
    provenance_complete = all(
        citation.get("document_id")
        and citation.get("source_file_ref")
        and citation.get("provenance_hash")
        and citation.get("sentence")
        for citation in citations
    )
    return {
        "status": status,
        "goal": goal_trace,
        "facts": [fact["proposition"].key for fact in facts],
        "schemas": schemas,
        "rules_parsed": len(rules),
        "known": {
            key: {
                "depth": value["depth"],
                "proof": value["proof"],
            }
            for key, value in known.items()
        },
        "applied_relations": applied,
        "missing": [prop.key for prop in missing],
        "clarifying_questions": [
            f"Which verified relation or observation establishes {prop.key}?"
            for prop in missing
        ],
        "citations": citations,
        "provenance_complete": provenance_complete,
    }


def _expected_schema_ids(project: SchemaProject) -> set[str]:
    rules = list(project.rules)
    if project.missing_rule is not None:
        rules.append(project.missing_rule)
    return {rule.schema_id for rule in rules}


def _run_project(
    project: SchemaProject,
    *,
    ingestion: DocumentIngestionRuntime,
    loader: DocumentTextLoader,
    artifact_dir: Path,
) -> Dict[str, Any]:
    documents = _install(
        project,
        ingestion=ingestion,
        artifact_dir=artifact_dir,
    )
    before = _evaluate(project, _loaded(documents, loader))
    queried = before["status"] == "unknown"
    final = before
    if queried:
        documents = _install(
            project,
            ingestion=ingestion,
            artifact_dir=artifact_dir,
            include_clarification=True,
        )
        final = _evaluate(project, _loaded(documents, loader))
    expected_final = (
        "supported"
        if project.expected_status in {"supported", "supported_after_query"}
        else "unsupported"
    )
    expected_missing = (
        project.missing_rule.consequence.key
        if project.missing_rule is not None
        else None
    )
    expected_schemas = _expected_schema_ids(project)
    observed_schemas = set(final["schemas"])
    explanation_depth = max(
        (item["depth"] for item in final["applied_relations"]),
        default=0,
    )
    # One-hop control cannot recursively chain invented relations.
    one_hop_known = set(before["facts"])
    for item in before["applied_relations"]:
        if item["depth"] == 1:
            one_hop_known.add(item["consequence"])
    goal_requirements = before["goal"]["requirements"]
    if before["goal"]["operator"] == "any":
        control_supported = any(key in one_hop_known for key in goal_requirements)
    elif before["goal"]["operator"] == "threshold":
        control_supported = (
            sum(key in one_hop_known for key in goal_requirements)
            >= before["goal"]["threshold"]
        )
    else:
        control_supported = all(key in one_hop_known for key in goal_requirements)
    control_status = "supported" if control_supported else "unsupported"
    return {
        "project_id": project.project_id,
        "domain": project.domain,
        "objective": project.objective,
        "expected_status": project.expected_status,
        "before_query": before,
        "final": final,
        "query_required": project.missing_rule is not None,
        "query_issued": queried,
        "missing_identified": (
            expected_missing in before["missing"]
            if expected_missing is not None
            else before["status"] != "unknown"
        ),
        "final_correct": final["status"] == expected_final,
        "schema_exact": observed_schemas == expected_schemas,
        "schema_ids": sorted(observed_schemas),
        "explanation_depth": explanation_depth,
        "multi_hop_demonstrated": explanation_depth >= 2,
        "provenance_complete": final["provenance_complete"],
        "one_hop_control_correct": control_status == expected_final,
    }


def run_open_schema_learning_benchmark(
    *,
    state_path: Path,
    artifact_dir: Path,
    result_path: Path | None = None,
    development_projects: int = 18,
    sealed_projects: int = 48,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    artifact_dir = artifact_dir.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    ingestion = DocumentIngestionRuntime(
        source_document_store=SourceDocumentStore(
            artifact_dir / "source_store"
        )
    )
    loader = DocumentTextLoader(base_dir=artifact_dir)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_natural_document_comprehension_34693b852de2"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="open_schema_learning",
            steps=["phase40_natural_document_comprehension"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase40_dependency"},
        )
    )
    development_rows = [
        _run_project(
            project,
            ingestion=ingestion,
            loader=loader,
            artifact_dir=artifact_dir / "development",
        )
        for project in _projects(development_projects, development=True)
    ]
    schema_library: Dict[str, Dict[str, Any]] = {}
    for row in development_rows:
        for schema_id, signature in row["final"]["schemas"].items():
            entry = schema_library.setdefault(
                schema_id,
                {
                    "signature": signature,
                    "development_domains": set(),
                    "development_uses": 0,
                    "sealed_domains": set(),
                    "sealed_uses": 0,
                },
            )
            entry["development_domains"].add(row["domain"])
            entry["development_uses"] += 1
    sealed_rows = []
    for project in _projects(sealed_projects, development=False):
        row = _run_project(
            project,
            ingestion=ingestion,
            loader=loader,
            artifact_dir=artifact_dir / "sealed",
        )
        for schema_id, signature in row["final"]["schemas"].items():
            entry = schema_library.setdefault(
                schema_id,
                {
                    "signature": signature,
                    "development_domains": set(),
                    "development_uses": 0,
                    "sealed_domains": set(),
                    "sealed_uses": 0,
                },
            )
            entry["sealed_domains"].add(row["domain"])
            entry["sealed_uses"] += 1
        row["verified_memory_commit"] = bool(
            row["final_correct"]
            and row["schema_exact"]
            and row["provenance_complete"]
        )
        runtime.store.state["schema_learning_projects"][
            project.project_id
        ] = row
        runtime.store.commit(reason=f"phase41_project:{project.project_id}")
        sealed_rows.append(row)
    serial_library = {
        schema_id: {
            **entry,
            "development_domains": sorted(entry["development_domains"]),
            "sealed_domains": sorted(entry["sealed_domains"]),
            "cross_domain_validated": bool(
                entry["development_domains"]
                and len(entry["sealed_domains"]) >= 3
            ),
        }
        for schema_id, entry in schema_library.items()
    }
    runtime.store.state["invented_document_schemas"] = serial_library
    runtime.store.commit(reason="phase41_schema_library")
    domains = {}
    for domain in SEALED_DOMAINS:
        members = [row for row in sealed_rows if row["domain"] == domain]
        domains[domain] = {
            "projects": len(members),
            "accuracy": sum(int(row["final_correct"]) for row in members)
            / len(members),
            "schema_accuracy": sum(int(row["schema_exact"]) for row in members)
            / len(members),
        }
    missing_cases = [row for row in sealed_rows if row["query_required"]]
    gate = {
        "sealed_projects": len(sealed_rows),
        "goal_accuracy": sum(
            int(row["final_correct"]) for row in sealed_rows
        ) / len(sealed_rows),
        "weakest_domain_accuracy": min(
            row["accuracy"] for row in domains.values()
        ),
        "schema_recovery_accuracy": sum(
            int(row["schema_exact"]) for row in sealed_rows
        ) / len(sealed_rows),
        "cross_domain_validated_schemas": sum(
            int(entry["cross_domain_validated"])
            for entry in serial_library.values()
        ),
        "invented_schemas": len(serial_library),
        "multi_hop_rate": sum(
            int(row["multi_hop_demonstrated"]) for row in sealed_rows
        ) / len(sealed_rows),
        "missing_knowledge_accuracy": (
            sum(int(row["missing_identified"]) for row in missing_cases)
            / len(missing_cases)
            if missing_cases else 1.0
        ),
        "query_recovery_accuracy": (
            sum(int(row["final_correct"]) for row in missing_cases)
            / len(missing_cases)
            if missing_cases else 1.0
        ),
        "unnecessary_queries": sum(
            int(row["query_issued"] and not row["query_required"])
            for row in sealed_rows
        ),
        "provenance_complete": sum(
            int(row["provenance_complete"]) for row in sealed_rows
        ) / len(sealed_rows),
        "verified_memory_commits": sum(
            int(row["verified_memory_commit"]) for row in sealed_rows
        ),
        "one_hop_control_accuracy": sum(
            int(row["one_hop_control_correct"]) for row in sealed_rows
        ) / len(sealed_rows),
    }
    errors = []
    requirements = (
        ("goal_accuracy", 0.90),
        ("weakest_domain_accuracy", 0.85),
        ("schema_recovery_accuracy", 0.90),
        ("multi_hop_rate", 0.70),
        ("missing_knowledge_accuracy", 0.90),
        ("query_recovery_accuracy", 0.90),
        ("provenance_complete", 1.0),
    )
    for name, minimum in requirements:
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["cross_domain_validated_schemas"] < 2:
        errors.append("FEWER_THAN_TWO_CROSS_DOMAIN_SCHEMAS")
    if gate["unnecessary_queries"]:
        errors.append("UNNECESSARY_CLARIFICATION")
    if gate["verified_memory_commits"] != sealed_projects:
        errors.append("VERIFIED_PROJECTS_NOT_RETAINED")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_schema_learning_"
            + _canonical_hash(
                {"parent": parent_id, "gate": gate, "schemas": serial_library}
            )[:12]
        ),
        goal="open_schema_learning",
        steps=[
            "ingest_unfamiliar_document_schemas",
            "induce_relation_operators_from_structure",
            "invent_and_validate_schema_signatures",
            "construct_recursive_explanatory_graph",
            "distinguish_false_from_unknown",
            "ask_for_exact_missing_relation",
            "verify_recovery_across_unrelated_domains",
            "cite_commit_and_restart",
        ],
        score=gate["goal_accuracy"] + gate["schema_recovery_accuracy"],
        success=gate["accepted"],
        evidence={"evaluation": "phase41_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase41_open_schema_learning")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "projects_retained": len(
            restarted.store.state["schema_learning_projects"]
        ) == sealed_projects,
        "schemas_retained": (
            restarted.store.state["invented_document_schemas"]
            == serial_library
        ),
        "champion_retained": (
            restarted.store.state["champions"].get("open_schema_learning")
            == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["projects_retained"],
                restart["schemas_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.open_schema_learning.v1",
        "benchmark": "source_disjoint_open_schema_multi_hop_learning",
        "passed": passed,
        "gate": gate,
        "domain_metrics": domains,
        "schema_library": serial_library,
        "development": {
            "projects": len(development_rows),
            "domains": list(DEVELOPMENT_DOMAINS),
        },
        "sealed": {
            "projects": len(sealed_rows),
            "domains": list(SEALED_DOMAINS),
            "rows": sealed_rows,
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "gold_isolation": {
            "solver_receives_expected_schema": False,
            "solver_receives_expected_goal_operator": False,
            "solver_receives_missing_relation": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 41 invents structural signatures for bounded conditional "
            "relation and goal operators, validates them across disjoint "
            "symbolic domains, constructs recursive proof graphs, and asks for "
            "missing relations. The natural-language grammar, binary factual "
            "states, finite operator family, documents and executable oracle "
            "remain engineered. This is not unrestricted ontology induction, "
            "scientific theory invention, arbitrary language understanding or "
            "AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore Phase 41 open-schema benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-projects", type=int, default=18)
    parser.add_argument("--sealed-projects", type=int, default=48)
    args = parser.parse_args()
    result = run_open_schema_learning_benchmark(
        state_path=args.state_path,
        artifact_dir=args.artifact_dir,
        result_path=args.result_path,
        development_projects=args.development_projects,
        sealed_projects=args.sealed_projects,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
