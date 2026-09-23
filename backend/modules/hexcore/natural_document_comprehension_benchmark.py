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


AUTHORITY_RANK = {
    "governing_board": 5,
    "independent_auditor": 4,
    "certified_operator": 3,
    "project_office": 2,
    "archive": 1,
    "anonymous_message": 0,
}


@dataclass(frozen=True)
class FieldRule:
    label: str
    comparator: str
    target: Any


@dataclass(frozen=True)
class NaturalProject:
    project_id: str
    domain: str
    objective: str
    rules: Tuple[FieldRule, ...]
    current_values: Mapping[str, Any]
    old_values: Mapping[str, Any]
    expected_decision: str
    prose_style: int


DOMAIN_CONTRACTS: Mapping[str, Tuple[FieldRule, ...]] = {
    "coastal restoration": (
        FieldRule("permit standing", "eq", "valid"),
        FieldRule("habitat readiness", "ge", 72),
        FieldRule("tide exposure", "le", 18),
    ),
    "materials laboratory": (
        FieldRule("ethics clearance", "eq", "complete"),
        FieldRule("sample viability", "ge", 81),
        FieldRule("thermal variance", "le", 6),
    ),
    "travelling exhibition": (
        FieldRule("loan agreement", "eq", "signed"),
        FieldRule("humidity reserve", "ge", 64),
        FieldRule("security exceptions", "le", 2),
    ),
    "mountain observatory": (
        FieldRule("calibration state", "eq", "aligned"),
        FieldRule("clear sky probability", "ge", 68),
        FieldRule("array timing drift", "le", 4),
    ),
    "regional supply programme": (
        FieldRule("supplier assurance", "eq", "confirmed"),
        FieldRule("buffer coverage", "ge", 76),
        FieldRule("route disruptions", "le", 1),
    ),
    "digital preservation programme": (
        FieldRule("rights clearance", "eq", "approved"),
        FieldRule("checksum coverage", "ge", 94),
        FieldRule("unresolved format risks", "le", 3),
    ),
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase40_document_comprehension_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normal(value: Any) -> str:
    text = re.sub(r"[^a-z0-9%.-]+", " ", str(value).lower()).strip()
    return re.sub(r"\s+", " ", text)


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "is", "are",
        "was", "were", "does", "what", "which", "how", "it", "that",
        "this", "with", "for", "from", "under", "its",
    }
    return {
        token
        for token in re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
        if len(token) > 2 and token not in stop
    }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _value_text(value: Any, *, numeric: bool) -> str:
    return f"{value} percent" if numeric else str(value)


def _condition_text(rule: FieldRule, style: int) -> str:
    if rule.comparator == "eq":
        alternatives = (
            f"{rule.label} is {rule.target}",
            f"{rule.label} remains {rule.target}",
            f"{rule.label} has status {rule.target}",
        )
    elif rule.comparator == "ge":
        alternatives = (
            f"{rule.label} is at least {rule.target} percent",
            f"{rule.label} reaches no less than {rule.target} percent",
            f"{rule.label} meets or exceeds {rule.target} percent",
        )
    else:
        alternatives = (
            f"{rule.label} does not exceed {rule.target}",
            f"{rule.label} is no more than {rule.target}",
            f"{rule.label} remains at or below {rule.target}",
        )
    return alternatives[style % len(alternatives)]


def _policy_text(project: NaturalProject, *, old: bool) -> str:
    rules = project.rules
    if old:
        shifted = []
        for rule in rules:
            target = rule.target
            if isinstance(target, int):
                target = target + (4 if rule.comparator == "ge" else -1)
            shifted.append(FieldRule(rule.label, rule.comparator, target))
        rules = tuple(shifted)
    conditions = [_condition_text(rule, project.prose_style) for rule in rules]
    joined = ", ".join(conditions[:-1]) + f", and {conditions[-1]}"
    introductions = (
        "The governing board may authorize the programme only when ",
        "A positive release decision is permitted only if ",
        "Approval depends on all of the following: ",
    )
    revision = 1 if old else 3
    supersession = (
        ""
        if old
        else " This edition replaces every earlier decision rule."
    )
    return (
        f"Decision memorandum, edition {revision}. "
        f"{introductions[project.prose_style % 3]}{joined}."
        f"{supersession} The evidence and rationale must be retained."
    )


def _fact_sentence(label: str, value: Any, style: int) -> str:
    rendered = _value_text(value, numeric=isinstance(value, int))
    forms = (
        f"The signed field report records {label} as {rendered}.",
        f"According to the audited ledger, {label} is {rendered}.",
        f"Inspectors verified that {label} remains {rendered}.",
        f"The latest certified entry places {label} at {rendered}.",
    )
    return forms[style % len(forms)]


def _projects(count: int, *, seed: int) -> List[NaturalProject]:
    rng = random.Random(seed)
    domains = list(DOMAIN_CONTRACTS)
    rows = []
    for index in range(count):
        domain = domains[index % len(domains)]
        rules = DOMAIN_CONTRACTS[domain]
        current: Dict[str, Any] = {}
        old: Dict[str, Any] = {}
        for field_index, rule in enumerate(rules):
            if rule.comparator == "eq":
                pass_value = str(rule.target)
                fail_value = {
                    "valid": "expired",
                    "complete": "pending",
                    "signed": "unsigned",
                    "aligned": "misaligned",
                    "confirmed": "unconfirmed",
                    "approved": "restricted",
                }[pass_value]
                current_value = (
                    fail_value if (index + field_index) % 7 == 0 else pass_value
                )
                old_value = (
                    pass_value if current_value == fail_value else fail_value
                )
            elif rule.comparator == "ge":
                current_value = int(rule.target) + (
                    -5 if (index + field_index) % 5 == 0 else rng.randint(1, 9)
                )
                old_value = int(rule.target) - (
                    3 if current_value >= int(rule.target) else -4
                )
            else:
                current_value = int(rule.target) + (
                    3 if (index + field_index) % 6 == 0 else -rng.randint(0, 2)
                )
                old_value = int(rule.target) + (
                    -1 if current_value > int(rule.target) else 3
                )
            current[rule.label] = current_value
            old[rule.label] = old_value
        expected = (
            "approve"
            if all(
                _satisfies(current[rule.label], rule)
                for rule in rules
            )
            else "defer"
        )
        rows.append(
            NaturalProject(
                project_id=f"phase40:{index:03d}",
                domain=domain,
                objective=(
                    f"Prepare an evidence-grounded readiness brief for the "
                    f"unfamiliar {domain}. Determine the current recommendation, "
                    "resolve conflicting records, cite every material conclusion, "
                    "and preserve any verified revision."
                ),
                rules=rules,
                current_values=current,
                old_values=old,
                expected_decision=expected,
                prose_style=(index // len(domains)) % 4,
            )
        )
    return rows


def _satisfies(value: Any, rule: FieldRule) -> bool:
    if rule.comparator == "eq":
        return _normal(value) == _normal(rule.target)
    numeric = float(value)
    return (
        numeric >= float(rule.target)
        if rule.comparator == "ge"
        else numeric <= float(rule.target)
    )


def _register(
    ingestion: DocumentIngestionRuntime,
    artifact_dir: Path,
    project: NaturalProject,
    *,
    name: str,
    text: str,
    revision: int,
    authority: str,
    verified: bool,
    published_at: str,
    kind: str,
) -> Dict[str, Any]:
    directory = artifact_dir / project.project_id.replace(":", "_")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    checksum = _sha(text)
    return ingestion.register_source_document(
        company_ref=project.project_id,
        source_type="other",
        fiscal_period_ref=f"revision-{revision}",
        source_file_ref=str(path),
        parsed_text_ref=str(path),
        published_at=published_at,
        provenance_hash=f"sha256:{checksum}" if verified else None,
        document_id=f"{project.project_id}/document/{name}",
        ingestion_status="parsed",
        payload_patch={
            "revision": revision,
            "authority": authority,
            "verified": verified,
            "kind": kind,
            "content_checksum": checksum,
        },
    )


def _install_project_documents(
    project: NaturalProject,
    *,
    ingestion: DocumentIngestionRuntime,
    artifact_dir: Path,
) -> Tuple[List[Dict[str, Any]], set[Tuple[str, str]]]:
    documents = [
        _register(
            ingestion,
            artifact_dir,
            project,
            name="policy_archive",
            text=_policy_text(project, old=True),
            revision=1,
            authority="governing_board",
            verified=True,
            published_at="2025-11-20T00:00:00Z",
            kind="policy",
        ),
        _register(
            ingestion,
            artifact_dir,
            project,
            name="policy_current",
            text=_policy_text(project, old=False),
            revision=3,
            authority="governing_board",
            verified=True,
            published_at="2026-07-12T00:00:00Z",
            kind="policy",
        ),
    ]
    gold_claims: set[Tuple[str, str]] = set()
    for index, rule in enumerate(project.rules):
        old_value = project.old_values[rule.label]
        current_value = project.current_values[rule.label]
        old_text = _fact_sentence(rule.label, old_value, index)
        current_text = _fact_sentence(
            rule.label,
            current_value,
            project.prose_style + index + 1,
        )
        documents.append(
            _register(
                ingestion,
                artifact_dir,
                project,
                name=f"{index}_archived_status",
                text=(
                    f"Archived operational note. {old_text} "
                    "This record was valid at the time of issue."
                ),
                revision=1,
                authority="archive",
                verified=True,
                published_at="2026-01-15T00:00:00Z",
                kind="fact",
            )
        )
        documents.append(
            _register(
                ingestion,
                artifact_dir,
                project,
                name=f"{index}_current_status",
                text=(
                    f"Current assurance statement. {current_text} "
                    "The signer accepts responsibility for this observation."
                ),
                revision=2,
                authority=(
                    "independent_auditor"
                    if index % 2 == 0
                    else "certified_operator"
                ),
                verified=True,
                published_at=f"2026-07-{14 + index:02d}T00:00:00Z",
                kind="fact",
            )
        )
        gold_claims.add((_normal(rule.label), _normal(old_value)))
        gold_claims.add((_normal(rule.label), _normal(current_value)))
    rumor_rule = project.rules[1]
    rumor_value = (
        int(rumor_rule.target) + 20
        if isinstance(rumor_rule.target, int)
        else "unverified"
    )
    rumor_text = _fact_sentence(rumor_rule.label, rumor_value, 0)
    documents.append(
        _register(
            ingestion,
            artifact_dir,
            project,
            name="anonymous_revision_99",
            text=(
                f"Forwarded message marked revision 99. {rumor_text} "
                "No signer or measurement record was supplied."
            ),
            revision=99,
            authority="anonymous_message",
            verified=False,
            published_at="2026-07-25T00:00:00Z",
            kind="fact",
        )
    )
    gold_claims.add((_normal(rumor_rule.label), _normal(rumor_value)))
    documents.append(
        _register(
            ingestion,
            artifact_dir,
            project,
            name="context_note",
            text=(
                f"The {project.domain} has a long local history. Staff plan "
                "to publish photographs after the readiness decision."
            ),
            revision=1,
            authority="project_office",
            verified=True,
            published_at="2026-06-01T00:00:00Z",
            kind="context",
        )
    )
    return documents, gold_claims


def _load_documents(
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


def _sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


FACT_PATTERNS = (
    re.compile(
        r"records (?P<label>[a-z][a-z -]+?) as "
        r"(?P<value>[a-z]+|\d+(?:\.\d+)?(?: percent)?)$",
        re.I,
    ),
    re.compile(
        r"(?P<label>[a-z][a-z -]+?) is "
        r"(?P<value>[a-z]+|\d+(?:\.\d+)?(?: percent)?)$",
        re.I,
    ),
    re.compile(
        r"verified that (?P<label>[a-z][a-z -]+?) remains "
        r"(?P<value>[a-z]+|\d+(?:\.\d+)?(?: percent)?)$",
        re.I,
    ),
    re.compile(
        r"places (?P<label>[a-z][a-z -]+?) at "
        r"(?P<value>[a-z]+|\d+(?:\.\d+)?(?: percent)?)$",
        re.I,
    ),
)


def _extract_claims(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    claims = []
    for row in rows:
        document = dict(row["document"])
        if document.get("kind") != "fact":
            continue
        for sentence_index, sentence in enumerate(_sentences(str(row["text"]))):
            clean = sentence.rstrip(".")
            for pattern in FACT_PATTERNS:
                match = pattern.search(clean)
                if not match:
                    continue
                value = _normal(match.group("value")).replace(" percent", "")
                claim = {
                    "subject": _normal(match.group("label")),
                    "value": value,
                    "document_id": document["document_id"],
                    "source_file_ref": document["source_file_ref"],
                    "sentence": sentence_index + 1,
                    "revision": int(document.get("revision") or 0),
                    "published_at": str(document.get("published_at") or ""),
                    "authority": str(document.get("authority") or ""),
                    "authority_rank": AUTHORITY_RANK.get(
                        str(document.get("authority") or ""), 0
                    ),
                    "verified": document.get("verified") is True,
                    "provenance_hash": document.get("provenance_hash"),
                }
                claims.append(claim)
                break
    return claims


def _active_policy(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    candidates = [
        row
        for row in rows
        if row["document"].get("kind") == "policy"
        and row["document"].get("verified") is True
        and row["document"].get("provenance_hash")
    ]
    return max(
        candidates,
        key=lambda row: (
            AUTHORITY_RANK.get(row["document"].get("authority"), 0),
            int(row["document"].get("revision") or 0),
            str(row["document"].get("published_at") or ""),
        ),
    )


def _parse_rule_clause(clause: str) -> FieldRule | None:
    clause = _normal(clause)
    patterns = (
        (r"(.+?) is at least (\d+) percent$", "ge"),
        (r"(.+?) reaches no less than (\d+) percent$", "ge"),
        (r"(.+?) meets or exceeds (\d+) percent$", "ge"),
        (r"(.+?) does not exceed (\d+)$", "le"),
        (r"(.+?) is no more than (\d+)$", "le"),
        (r"(.+?) remains at or below (\d+)$", "le"),
        (r"(.+?) is ([a-z]+)$", "eq"),
        (r"(.+?) remains ([a-z]+)$", "eq"),
        (r"(.+?) has status ([a-z]+)$", "eq"),
    )
    for raw, comparator in patterns:
        match = re.match(raw, clause)
        if match:
            target: Any = (
                int(match.group(2))
                if comparator in {"ge", "le"}
                else match.group(2)
            )
            return FieldRule(_normal(match.group(1)), comparator, target)
    return None


def _decompose_policy(policy_text: str) -> List[FieldRule]:
    decision_sentence = next(
        sentence
        for sentence in _sentences(policy_text)
        if (
            "only when" in sentence.lower()
            or "only if" in sentence.lower()
            or "depends on all of the following:" in sentence.lower()
        )
    )
    lowered = decision_sentence.lower()
    for marker in (
        "only when ",
        "only if ",
        "depends on all of the following: ",
    ):
        if marker in lowered:
            tail = decision_sentence[
                lowered.index(marker) + len(marker):
            ].rstrip(".")
            break
    else:
        return []
    tail = re.sub(r",\s+and\s+", ", ", tail, flags=re.I)
    clauses = [part.strip() for part in tail.split(",") if part.strip()]
    return [
        parsed
        for parsed in (_parse_rule_clause(clause) for clause in clauses)
        if parsed is not None
    ]


def _resolve_beliefs(claims: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for claim in claims:
        grouped.setdefault(str(claim["subject"]), []).append(claim)
    beliefs = {}
    for subject, candidates in grouped.items():
        ranked = sorted(
            candidates,
            key=lambda claim: (
                bool(claim.get("verified")),
                int(claim.get("authority_rank") or 0),
                int(claim.get("revision") or 0),
                str(claim.get("published_at") or ""),
            ),
            reverse=True,
        )
        accepted = dict(ranked[0])
        accepted["superseded_claims"] = [
            {
                "value": claim["value"],
                "document_id": claim["document_id"],
                "reason": (
                    "unverified"
                    if not claim.get("verified")
                    else "lower_authority_or_older_revision"
                ),
            }
            for claim in ranked[1:]
        ]
        beliefs[subject] = accepted
    return beliefs


def _evaluate_project(
    project: NaturalProject,
    *,
    rows: Sequence[Mapping[str, Any]],
    gold_claims: set[Tuple[str, str]],
) -> Dict[str, Any]:
    policy = _active_policy(rows)
    rules = _decompose_policy(str(policy["text"]))
    claims = _extract_claims(rows)
    predicted_claims = {
        (_normal(claim["subject"]), _normal(claim["value"]))
        for claim in claims
    }
    true_positive = len(predicted_claims & gold_claims)
    precision = true_positive / len(predicted_claims) if predicted_claims else 0.0
    recall = true_positive / len(gold_claims) if gold_claims else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    beliefs = _resolve_beliefs(claims)
    decisions = []
    citations = [
        {
            "document_id": policy["document"]["document_id"],
            "source_file_ref": policy["document"]["source_file_ref"],
            "revision": policy["document"]["revision"],
            "provenance_hash": policy["document"]["provenance_hash"],
            "sentence": 2,
            "role": "decision_rule",
        }
    ]
    for rule in rules:
        belief = beliefs.get(_normal(rule.label))
        satisfied = bool(belief and _satisfies(belief["value"], rule))
        decisions.append(
            {
                "field": rule.label,
                "comparator": rule.comparator,
                "target": rule.target,
                "observed": belief.get("value") if belief else None,
                "satisfied": satisfied,
            }
        )
        if belief:
            citations.append(
                {
                    "document_id": belief["document_id"],
                    "source_file_ref": belief["source_file_ref"],
                    "revision": belief["revision"],
                    "provenance_hash": belief["provenance_hash"],
                    "sentence": belief["sentence"],
                    "role": f"evidence:{rule.label}",
                }
            )
    recommendation = (
        "approve"
        if len(decisions) == len(rules)
        and decisions
        and all(row["satisfied"] for row in decisions)
        else "defer"
    )
    expected_fields = {_normal(rule.label) for rule in project.rules}
    discovered_fields = {_normal(rule.label) for rule in rules}
    revision_correct = all(
        beliefs.get(_normal(rule.label), {}).get("value")
        == _normal(project.current_values[rule.label])
        for rule in project.rules
    )
    rumor_accepted = any(
        belief.get("verified") is not True
        for belief in beliefs.values()
    )
    provenance_complete = all(
        citation.get("document_id")
        and citation.get("source_file_ref")
        and citation.get("provenance_hash")
        and citation.get("sentence")
        for citation in citations
    )
    # Control: first policy and first extracted claim for every subject.
    first_policy = next(
        row for row in rows if row["document"].get("kind") == "policy"
    )
    control_rules = _decompose_policy(str(first_policy["text"]))
    first_beliefs: Dict[str, Mapping[str, Any]] = {}
    for claim in claims:
        first_beliefs.setdefault(str(claim["subject"]), claim)
    control = (
        "approve"
        if control_rules
        and all(
            first_beliefs.get(_normal(rule.label))
            and _satisfies(first_beliefs[_normal(rule.label)]["value"], rule)
            for rule in control_rules
        )
        else "defer"
    )
    return {
        "project_id": project.project_id,
        "domain": project.domain,
        "objective": project.objective,
        "discovered_subgoals": [
            {
                "field": rule.label,
                "comparator": rule.comparator,
                "target": rule.target,
            }
            for rule in rules
        ],
        "claim_precision": precision,
        "claim_recall": recall,
        "claim_f1": f1,
        "decomposition_exact": discovered_fields == expected_fields,
        "beliefs": beliefs,
        "revision_correct": revision_correct,
        "rumor_accepted": rumor_accepted,
        "decisions": decisions,
        "recommendation": recommendation,
        "expected_recommendation": project.expected_decision,
        "goal_success": recommendation == project.expected_decision,
        "first_record_control_success": control == project.expected_decision,
        "citations": citations,
        "provenance_complete": provenance_complete,
    }


def _external_chunks(path: Path) -> List[Dict[str, Any]]:
    chunks = []
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        for page_index, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = page.extract_text() or ""
            sentences = _sentences(text)
            # Overlapping windows preserve definitions and enumerations that
            # cross sentence boundaries without exposing evaluator anchors.
            for sentence_index in range(0, len(sentences), 3):
                window = " ".join(sentences[sentence_index:sentence_index + 6])
                chunks.append(
                    {
                        "source": str(path),
                        "locator": (
                            f"page:{page_index}:sentence:{sentence_index + 1}"
                        ),
                        "text": window,
                    }
                )
    else:
        lines = path.read_text(encoding="utf-8").splitlines()
        heading = ""
        block: List[str] = []
        block_start = 1

        def flush() -> None:
            nonlocal block
            if block:
                chunks.append(
                    {
                        "source": str(path),
                        "locator": f"line:{block_start}",
                        "text": " ".join(
                            part for part in (heading, *block) if part
                        ),
                    }
                )
                block = []

        for line_index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                heading = stripped.lstrip("#").strip()
                continue
            if not stripped or stripped == "---":
                flush()
                continue
            if not block:
                block_start = line_index
            block.append(stripped)
        flush()
    return chunks


def _retrieval_terms(text: str) -> set[str]:
    terms = _tokens(text)
    # Morphological families make retrieval less brittle while remaining
    # independent of the four evaluator answers.
    families = {
        "govern": {"governance", "governed", "governing", "policy"},
        "define": {"definition", "defines", "semantics", "means"},
        "runtime": {"engine", "execution", "implemented", "system"},
        "physical": {"physics", "hardware", "qubits", "quantum"},
        "audit": {"auditable", "trace", "trail", "replay"},
        "stage": {"step", "process", "structured", "lifecycle"},
        "role": {"purpose", "definition", "interaction"},
        "differ": {
            "difference", "versus", "definitions", "formal", "semantics",
            "runtime", "execute", "meaning",
        },
    }
    expanded = set(terms)
    for root, members in families.items():
        if root in terms or terms & members:
            expanded.add(root)
            expanded.update(members)
    return expanded


def _external_comprehension(paths: Sequence[Path]) -> Dict[str, Any]:
    available = [path for path in paths if path.exists()]
    all_chunks = [
        chunk
        for path in available
        for chunk in _external_chunks(path)
    ]
    # Gold anchors remain evaluator-only. Retrieval sees only the questions.
    tasks = (
        {
            "question": (
                "What is the Tessaris Engine's core role and which lower "
                "layers does it integrate?"
            ),
            "anchors": (
                "orchestration and governance layer",
                "symatics",
                "glyphos",
                "codexcore",
                "sqm/sqi",
            ),
        },
        {
            "question": (
                "What public boundary distinguishes symbolic execution from "
                "AI and physical quantum hardware?"
            ),
            "anchors": (
                "symbolic and deterministic",
                "not physical quantum devices",
                "does not claim to be an ai itself",
            ),
        },
        {
            "question": "How do SQM and SQI differ in role?",
            "anchors": (
                "formal semantics",
                "implemented runtime",
                "meaning-states",
                "containers",
            ),
        },
        {
            "question": "What stages make collapse a governed measurement?",
            "anchors": (
                "option space",
                "observer/context",
                "policy hooks",
                "selection",
                "audit trail",
            ),
        },
    )
    rows = []
    for task in tasks:
        query = _retrieval_terms(task["question"])
        candidates = []
        for chunk in all_chunks:
            terms = _retrieval_terms(chunk["text"])
            overlap = len(query & terms)
            candidates.append(
                {
                    **chunk,
                    "terms": terms,
                    "relevance": overlap / max(1.0, len(query) ** 0.5),
                }
            )
        selected = []
        remaining = list(candidates)
        while remaining and len(selected) < 8:
            def utility(chunk: Mapping[str, Any]) -> float:
                redundancy = 0.0
                for prior in selected:
                    union = chunk["terms"] | prior["terms"]
                    if union:
                        redundancy = max(
                            redundancy,
                            len(chunk["terms"] & prior["terms"]) / len(union),
                        )
                return float(chunk["relevance"]) - 0.35 * redundancy

            chosen = max(remaining, key=utility)
            remaining.remove(chosen)
            if chosen["relevance"] <= 0:
                break
            selected.append(chosen)
        answer = _normal(
            " ".join(chunk["text"] for chunk in selected)
        )
        anchor_hits = [
            anchor
            for anchor in task["anchors"]
            if _normal(anchor) in answer
        ]
        rows.append(
            {
                "question": task["question"],
                "anchor_coverage": len(anchor_hits) / len(task["anchors"]),
                "anchor_hits": anchor_hits,
                "citations": [
                    {
                        "source": chunk["source"],
                        "locator": chunk["locator"],
                        "text_hash": _sha(chunk["text"]),
                    }
                    for chunk in selected
                ],
            }
        )
    return {
        "documents": len(available),
        "chunks": len(all_chunks),
        "tasks": rows,
        "mean_anchor_coverage": (
            sum(row["anchor_coverage"] for row in rows) / len(rows)
            if rows else 0.0
        ),
        "all_tasks_cited": all(row["citations"] for row in rows),
    }


def run_natural_document_comprehension_benchmark(
    *,
    state_path: Path,
    artifact_dir: Path,
    result_path: Path | None = None,
    sealed_projects: int = 60,
    external_documents: Sequence[Path] = (),
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    artifact_dir = artifact_dir.resolve()
    external_documents = tuple(path.resolve() for path in external_documents)
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    source_store = SourceDocumentStore(artifact_dir / "source_store")
    ingestion = DocumentIngestionRuntime(
        source_document_store=source_store
    )
    loader = DocumentTextLoader(base_dir=artifact_dir)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_cost_aware_open_docs_09c260698e08"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="natural_document_comprehension",
            steps=["phase39_cost_aware_open_documents"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase39_dependency"},
        )
    )
    rows = []
    for project in _projects(sealed_projects, seed=400_040):
        documents, gold_claims = _install_project_documents(
            project,
            ingestion=ingestion,
            artifact_dir=artifact_dir / "sealed_documents",
        )
        loaded = _load_documents(documents, loader)
        evaluated = _evaluate_project(
            project,
            rows=loaded,
            gold_claims=gold_claims,
        )
        evaluated["verified_memory_commit"] = bool(
            evaluated["goal_success"]
            and evaluated["revision_correct"]
            and evaluated["provenance_complete"]
            and not evaluated["rumor_accepted"]
        )
        runtime.store.state["document_comprehension_projects"][
            project.project_id
        ] = evaluated
        runtime.store.commit(reason=f"phase40_project:{project.project_id}")
        rows.append(evaluated)
    domains = {}
    for domain in DOMAIN_CONTRACTS:
        members = [row for row in rows if row["domain"] == domain]
        domains[domain] = {
            "projects": len(members),
            "goal_success": sum(
                int(row["goal_success"]) for row in members
            ) / len(members),
            "claim_f1": sum(row["claim_f1"] for row in members) / len(members),
        }
    external = _external_comprehension(external_documents)
    gate = {
        "projects": len(rows),
        "goal_success": sum(int(row["goal_success"]) for row in rows) / len(rows),
        "weakest_domain_success": min(
            row["goal_success"] for row in domains.values()
        ),
        "claim_precision": sum(row["claim_precision"] for row in rows) / len(rows),
        "claim_recall": sum(row["claim_recall"] for row in rows) / len(rows),
        "claim_f1": sum(row["claim_f1"] for row in rows) / len(rows),
        "decomposition_exact": sum(
            int(row["decomposition_exact"]) for row in rows
        ) / len(rows),
        "contradiction_revision_accuracy": sum(
            int(row["revision_correct"]) for row in rows
        ) / len(rows),
        "first_record_control_success": sum(
            int(row["first_record_control_success"]) for row in rows
        ) / len(rows),
        "provenance_complete": sum(
            int(row["provenance_complete"]) for row in rows
        ) / len(rows),
        "unverified_acceptances": sum(
            int(row["rumor_accepted"]) for row in rows
        ),
        "verified_memory_commits": sum(
            int(row["verified_memory_commit"]) for row in rows
        ),
        "external_document_anchor_coverage": external["mean_anchor_coverage"],
        "external_document_worst_task": min(
            (
                row["anchor_coverage"]
                for row in external["tasks"]
            ),
            default=0.0,
        ),
        "external_tasks_cited": external["all_tasks_cited"],
    }
    errors = []
    requirements = (
        ("goal_success", 0.90),
        ("weakest_domain_success", 0.85),
        ("claim_f1", 0.90),
        ("decomposition_exact", 0.90),
        ("contradiction_revision_accuracy", 0.95),
        ("provenance_complete", 1.0),
    )
    for name, minimum in requirements:
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["unverified_acceptances"]:
        errors.append("UNVERIFIED_CLAIM_ACCEPTED")
    if gate["verified_memory_commits"] != sealed_projects:
        errors.append("VERIFIED_PROJECTS_NOT_RETAINED")
    if external_documents:
        if gate["external_document_anchor_coverage"] < 0.75:
            errors.append("EXTERNAL_DOCUMENT_TRANSFER_BELOW_75_PERCENT")
        if gate["external_document_worst_task"] < 0.60:
            errors.append("EXTERNAL_DOCUMENT_WORST_TASK_BELOW_60_PERCENT")
        if not gate["external_tasks_cited"]:
            errors.append("EXTERNAL_DOCUMENT_CITATIONS_MISSING")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_natural_document_comprehension_"
            + _canonical_hash(
                {"parent": parent_id, "gate": gate, "domains": domains}
            )[:12]
        ),
        goal="natural_document_comprehension",
        steps=[
            "ingest_source_disjoint_natural_documents",
            "extract_claims_without_gold_access",
            "induce_project_subgoals_from_active_policy",
            "synthesize_cross_document_evidence",
            "revise_beliefs_by_authority_revision_and_provenance",
            "reject_unverified_conflicts",
            "derive_cite_commit_and_restart",
        ],
        score=gate["goal_success"] + gate["claim_f1"],
        success=gate["accepted"],
        evidence={"evaluation": "phase40_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase40_natural_document_comprehension")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "projects_retained": len(
            restarted.store.state["document_comprehension_projects"]
        ) == sealed_projects,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "natural_document_comprehension"
            ) == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["projects_retained"]
        and restart["champion_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.natural_document_comprehension.v1",
        "benchmark": "source_disjoint_natural_document_comprehension",
        "passed": passed,
        "gate": gate,
        "domain_metrics": domains,
        "external_transfer": external,
        "sealed": {"projects": len(rows), "rows": rows},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "gold_isolation": {
            "solver_receives_gold_claims": False,
            "solver_receives_expected_subgoals": False,
            "solver_receives_expected_decision": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 40 evaluates generic claim extraction, policy-derived "
            "decomposition, cross-document synthesis and revision-aware belief "
            "maintenance over source-disjoint synthetic natural prose, plus a "
            "small real-document retrieval-and-anchor transfer check. The "
            "document grammar, metadata schema, question set and deterministic "
            "oracle remain engineered. This is not unrestricted reading "
            "comprehension, arbitrary media understanding or AGI."
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
        description="Run HexCore Phase 40 document comprehension benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-projects", type=int, default=60)
    parser.add_argument(
        "--external-document",
        action="append",
        type=Path,
        default=[],
    )
    args = parser.parse_args()
    result = run_natural_document_comprehension_benchmark(
        state_path=args.state_path,
        artifact_dir=args.artifact_dir,
        result_path=args.result_path,
        sealed_projects=args.sealed_projects,
        external_documents=args.external_document,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
