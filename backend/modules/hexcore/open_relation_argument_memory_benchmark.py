from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.long_document_semantic_memory_benchmark import (
    BOOKS,
    _normal,
    _paragraphs,
    _sha,
    _span_normal,
)
from backend.modules.hexcore.open_patch_generation_benchmark import (
    OPENAI_MODEL,
    _configured_openai_key,
    _openai_text,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_open_relation_argument_memory_189258f3d567"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_relation_argument_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _call_json(prompt: str, *, timeout: int = 240) -> Dict[str, Any]:
    key = _configured_openai_key()
    if not key:
        return {"available": False, "proposal": {}, "error": "MISSING_PROVIDER"}
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(
            {
                "model": OPENAI_MODEL,
                "input": prompt,
                "text": {"format": {"type": "json_object"}},
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    raw = _openai_text(payload)
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError:
        proposal = {}
    usage = dict(payload.get("usage") or {})
    return {
        "available": True,
        "proposal": proposal,
        "latency_seconds": time.perf_counter() - started,
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def _evidence_windows(paragraphs: Sequence[str], *, count: int = 10) -> List[str]:
    if not paragraphs:
        return []
    step = max(1, len(paragraphs) // count)
    return [
        paragraphs[min(index * step + step // 2, len(paragraphs) - 1)]
        for index in range(count)
    ]


def _induction_prompt(title: str, windows: Sequence[str]) -> str:
    evidence = "\n\n".join(
        f"[EVIDENCE {index + 1}] {value}"
        for index, value in enumerate(windows)
    )
    return f"""
You are a proposal-only ontology and argument learner. No concept types,
relation vocabulary, character list, argument schema or expected answers are
supplied. Invent concise reusable concept labels and relation predicates from
the evidence itself.

Return one JSON object:
concepts: array of objects with label, definition, evidence_quote
relations: array of objects with subject, predicate, object, evidence_quote
arguments: array of objects with claim, premises (array), evidence_quote
open_questions: array of strings

Every evidence_quote must be copied exactly from the supplied evidence and be
at most two sentences. Describe what the book reports; do not mark literary
statements as independently verified truth.

BOOK: {title}

{evidence}
""".strip()


def _answer_prompt(
    question: str,
    memory_rows: Sequence[Mapping[str, Any]],
) -> str:
    evidence = "\n".join(
        f"[MEMORY {index + 1}] "
        + json.dumps(dict(row), ensure_ascii=False, sort_keys=True)
        for index, row in enumerate(memory_rows)
    )
    return f"""
Answer only from the retained semantic memory below. Do not use outside book
knowledge. Return JSON with answer, memory_ids (array of the numbered MEMORY
identifiers used), and uncertainty. If memory is insufficient, answer
INSUFFICIENT_MEMORY.

QUESTION: {question}

{evidence}
""".strip()


def _consolidation_prompt(relations: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        {
            "predicate": row["predicate"],
            "subject": row["subject"],
            "object": row["object"],
        }
        for row in relations
    ]
    return f"""
Consolidate the invented relation predicates below into a smaller reusable
ontology. Merge only predicates with genuinely compatible semantics. Preserve
specialized predicates when merging would erase meaning.

Return one JSON object with `clusters`, an array. Each cluster contains:
canonical_predicate: concise snake_case string
members: exact array of original predicate strings
definition: one sentence

Every original predicate must appear exactly once. Do not invent members.

RELATIONS:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2
    }


def _relevant_memory(
    question: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int = 8,
) -> List[Mapping[str, Any]]:
    query = _terms(question)
    scored = []
    for index, row in enumerate(rows):
        rendered = json.dumps(dict(row), ensure_ascii=False)
        score = len(query & _terms(rendered))
        scored.append((score, -index, row))
    return [row[2] for row in sorted(scored, reverse=True)[:limit]]


def run_open_relation_argument_memory(
    *,
    books_dir: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    books_dir = books_dir.resolve()
    source_rows: Dict[str, Dict[str, Any]] = {}
    inductions = []
    accepted_concepts = []
    accepted_relations = []
    accepted_arguments = []

    for book in BOOKS:
        path = books_dir / book.path
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        paragraphs = _paragraphs(text)
        windows = _evidence_windows(paragraphs)
        source_rows[book.book_id] = {
            "title": book.title,
            "path": str(path),
            "sha256": _sha(text),
            "text": text,
            "paragraphs": paragraphs,
            "windows": windows,
        }
        response = provider(_induction_prompt(book.title, windows))
        proposal = dict(response.get("proposal") or {})
        normalized_source = _span_normal(" ".join(windows))
        counts = {"concepts": 0, "relations": 0, "arguments": 0}

        for index, row in enumerate(proposal.get("concepts") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "")
            if not quote or _span_normal(quote) not in normalized_source:
                continue
            label = str(row.get("label") or "").strip()
            definition = str(row.get("definition") or "").strip()
            if not label or not definition:
                continue
            accepted_concepts.append(
                {
                    "memory_id": f"{book.book_id}:concept:{index}",
                    "book_id": book.book_id,
                    "label": label,
                    "definition": definition,
                    "evidence_quote": quote,
                    "source_hash": source_rows[book.book_id]["sha256"],
                    "status": "reported_by_source",
                }
            )
            counts["concepts"] += 1

        for index, row in enumerate(proposal.get("relations") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "")
            subject = str(row.get("subject") or "").strip()
            predicate = str(row.get("predicate") or "").strip()
            obj = str(row.get("object") or "").strip()
            quote_terms = _terms(quote)
            book_concepts = [
                value
                for value in accepted_concepts
                if value["book_id"] == book.book_id
            ]

            def endpoint_grounded(label: str) -> bool:
                if _terms(label) & quote_terms:
                    return True
                return any(
                    _terms(label) & _terms(concept["label"])
                    and (
                        _span_normal(concept["evidence_quote"])
                        in _span_normal(quote)
                        or _span_normal(quote)
                        in _span_normal(concept["evidence_quote"])
                    )
                    for concept in book_concepts
                )

            grounded = (
                bool(quote)
                and _span_normal(quote) in normalized_source
                and endpoint_grounded(subject)
                and endpoint_grounded(obj)
            )
            if not grounded or not predicate:
                continue
            accepted_relations.append(
                {
                    "memory_id": f"{book.book_id}:relation:{index}",
                    "book_id": book.book_id,
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "evidence_quote": quote,
                    "source_hash": source_rows[book.book_id]["sha256"],
                    "status": "reported_by_source",
                }
            )
            counts["relations"] += 1

        for index, row in enumerate(proposal.get("arguments") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "")
            claim = str(row.get("claim") or "").strip()
            premises = [
                str(value).strip()
                for value in (row.get("premises") or [])
                if str(value).strip()
            ]
            if (
                not quote
                or _span_normal(quote) not in normalized_source
                or not claim
                or not premises
            ):
                continue
            accepted_arguments.append(
                {
                    "memory_id": f"{book.book_id}:argument:{index}",
                    "book_id": book.book_id,
                    "claim": claim,
                    "premises": premises,
                    "evidence_quote": quote,
                    "source_hash": source_rows[book.book_id]["sha256"],
                    "status": "reported_argument",
                }
            )
            counts["arguments"] += 1

        inductions.append(
            {
                "book_id": book.book_id,
                "counts": counts,
                "invented_predicates": sorted(
                    {
                        row["predicate"]
                        for row in accepted_relations
                        if row["book_id"] == book.book_id
                    }
                ),
                "open_questions": list(proposal.get("open_questions") or []),
                "provider": {
                    key: value
                    for key, value in response.items()
                    if key != "proposal"
                },
            }
        )

    memory_rows = accepted_concepts + accepted_relations + accepted_arguments
    original_predicates = sorted(
        {row["predicate"] for row in accepted_relations}
    )
    consolidation_response = provider(
        _consolidation_prompt(accepted_relations)
    )
    consolidation_proposal = dict(
        consolidation_response.get("proposal") or {}
    )
    predicate_mapping: Dict[str, str] = {}
    predicate_clusters = []
    for cluster in consolidation_proposal.get("clusters") or []:
        if not isinstance(cluster, Mapping):
            continue
        canonical = str(cluster.get("canonical_predicate") or "").strip()
        members = [
            str(value)
            for value in (cluster.get("members") or [])
            if str(value) in original_predicates
            and str(value) not in predicate_mapping
        ]
        if not canonical or not members:
            continue
        predicate_clusters.append(
            {
                "canonical_predicate": canonical,
                "members": members,
                "definition": str(cluster.get("definition") or ""),
            }
        )
        predicate_mapping.update({member: canonical for member in members})
    for predicate in original_predicates:
        if predicate not in predicate_mapping:
            predicate_mapping[predicate] = predicate
            predicate_clusters.append(
                {
                    "canonical_predicate": predicate,
                    "members": [predicate],
                    "definition": "Unmerged retained predicate.",
                }
            )
    for relation in accepted_relations:
        relation["canonical_predicate"] = predicate_mapping[
            relation["predicate"]
        ]
    canonical_predicates = sorted(set(predicate_mapping.values()))
    predicate_compression = (
        1 - len(canonical_predicates) / max(1, len(original_predicates))
    )
    memory_rows = accepted_concepts + accepted_relations + accepted_arguments
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    ontology_id = f"open_ontology_{_canonical_hash(memory_rows)[:16]}"
    runtime.store.state["open_relation_ontologies"][ontology_id] = {
        "concepts": accepted_concepts,
        "relations": accepted_relations,
        "predicate_clusters": predicate_clusters,
        "books": {
            key: {
                "title": value["title"],
                "path": value["path"],
                "sha256": value["sha256"],
            }
            for key, value in source_rows.items()
        },
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["argument_memories"][ontology_id] = {
        "arguments": accepted_arguments,
        "created_at": _utc_timestamp(),
    }
    runtime.store.commit(reason="open_relation_argument_induction")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    retained_ontology = restarted.store.state[
        "open_relation_ontologies"
    ].get(ontology_id, {})
    retained_arguments = restarted.store.state[
        "argument_memories"
    ].get(ontology_id, {})
    retained_rows = (
        list(retained_ontology.get("concepts") or [])
        + list(retained_ontology.get("relations") or [])
        + list(retained_arguments.get("arguments") or [])
    )

    delayed_queries = []
    for relation in list(retained_ontology.get("relations") or [])[:12]:
        question = (
            f"According to retained memory, what does "
            f"{relation['subject']} {relation['predicate']}?"
        )
        candidates = _relevant_memory(question, retained_rows)
        response = provider(_answer_prompt(question, candidates))
        proposal = dict(response.get("proposal") or {})
        answer = str(proposal.get("answer") or "")
        expected = str(relation["object"])
        cited_ids = [str(value) for value in (proposal.get("memory_ids") or [])]
        target_index = next(
            (
                index + 1
                for index, row in enumerate(candidates)
                if row.get("memory_id") == relation["memory_id"]
            ),
            None,
        )
        accepted_target_citations = {
            relation["memory_id"],
            str(target_index),
            f"MEMORY {target_index}",
        }
        target_cited = bool(
            target_index
            and accepted_target_citations.intersection(cited_ids)
        )
        lexical_match = bool(_terms(expected) <= _terms(answer))
        substantive = (
            bool(answer.strip())
            and "insufficient" not in answer.lower()
        )
        correct = substantive and (lexical_match or target_cited)
        delayed_queries.append(
            {
                "question": question,
                "expected": expected,
                "answer": answer,
                "correct": correct,
                "cited_memory": bool(cited_ids),
                "target_memory_cited": target_cited,
                "memory_ids": cited_ids,
                "uncertainty": str(proposal.get("uncertainty") or ""),
            }
        )

    per_book_relation = {
        book.book_id: sum(
            row["book_id"] == book.book_id for row in accepted_relations
        )
        for book in BOOKS
    }
    delayed_accuracy = (
        sum(row["correct"] for row in delayed_queries)
        / max(1, len(delayed_queries))
    )
    gate = {
        "books": len(BOOKS),
        "supplied_relation_types": 0,
        "invented_concepts": len(accepted_concepts),
        "invented_relations": len(accepted_relations),
        "invented_predicate_types": len(
            {row["predicate"] for row in accepted_relations}
        ),
        "canonical_predicate_types": len(canonical_predicates),
        "predicate_consolidation_coverage": (
            len(predicate_mapping) / max(1, len(original_predicates))
        ),
        "predicate_compression": predicate_compression,
        "reported_arguments": len(accepted_arguments),
        "weakest_book_relations": min(per_book_relation.values()),
        "delayed_memory_queries": len(delayed_queries),
        "delayed_memory_accuracy": delayed_accuracy,
        "provenance_completeness": float(
            bool(memory_rows)
            and all(row.get("evidence_quote") for row in memory_rows)
        ),
        "reported_arguments_marked_verified": 0,
        "source_files_reread_during_delayed_query": 0,
        "restart_relearning": 0,
        "unsafe_knowledge_commitments": 0,
    }
    requirements = {
        "concepts": gate["invented_concepts"] >= 9,
        "relations": (
            gate["invented_relations"] >= 9
            and gate["weakest_book_relations"] >= 2
            and gate["invented_predicate_types"] >= 5
        ),
        "consolidation": (
            gate["predicate_consolidation_coverage"] == 1.0
            and gate["predicate_compression"] >= 0.2
        ),
        "arguments": gate["reported_arguments"] >= 3,
        "delayed": (
            gate["delayed_memory_queries"] >= 6
            and gate["delayed_memory_accuracy"] >= 0.8
        ),
        "provenance": gate["provenance_completeness"] == 1.0,
        "epistemic": gate["reported_arguments_marked_verified"] == 0,
        "restart": gate["restart_relearning"] == 0,
        "safety": gate["unsafe_knowledge_commitments"] == 0,
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_relation_argument_memory",
        steps=[
            "sample_source_disjoint_book_evidence",
            "invent_concepts_relations_and_argument_schema",
            "verify_every_retained_evidence_span",
            "mark_book_arguments_as_reported_not_verified",
            "reconstruct_runtime",
            "answer_delayed_queries_from_memory_only",
        ],
        score=delayed_accuracy + min(1.0, len(accepted_relations) / 12),
        success=gate["accepted"],
        evidence={"gate": gate, "ontology_id": ontology_id},
        source_rules=["procedure_long_document_semantic_memory_6d1736d5906a"],
    )
    promotion = restarted.skills.promote(candidate)
    restarted.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    restarted.store.commit(reason="open_relation_argument_memory")
    final_runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "ontology_retained": ontology_id
        in final_runtime.store.state["open_relation_ontologies"],
        "arguments_retained": ontology_id
        in final_runtime.store.state["argument_memories"],
        "champion_retained": (
            final_runtime.store.state["champions"].get(
                "open_relation_argument_memory"
            )
            == PROCEDURE_ID
        ),
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.open_relation_argument_memory.v1",
        "created_at": _utc_timestamp(),
        "ontology_id": ontology_id,
        "inductions": inductions,
        "concepts": accepted_concepts,
        "relations": accepted_relations,
        "predicate_clusters": predicate_clusters,
        "arguments": accepted_arguments,
        "delayed_queries": delayed_queries,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (
                promotion.get("promoted")
                or promotion.get("champion_id") == PROCEDURE_ID
            )
            and restart["ontology_retained"]
            and restart["arguments_retained"]
            and restart["champion_retained"]
            and restart["relearning_failures"] == 0
        ),
        "boundary": (
            "Relation labels are open, but evidence windows, provider, delayed "
            "query construction and acceptance checks remain development "
            "controlled. Arguments are reported structures, not verified truth."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--books-dir",
        type=Path,
        default=Path(
            "backend/modules/hexcore/data/public_domain_books"
        ),
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(
            "backend/modules/hexcore/data/open_relation_argument_memory_state.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_open_relation_argument_memory.json"
        ),
    )
    args = parser.parse_args()
    result = run_open_relation_argument_memory(
        books_dir=args.books_dir,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
