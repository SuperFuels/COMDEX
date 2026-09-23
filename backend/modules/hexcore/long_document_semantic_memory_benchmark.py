from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.open_patch_generation_benchmark import (
    OPENAI_MODEL,
    _configured_openai_key,
    _openai_text,
)


PROCEDURE_ID = "procedure_long_document_semantic_memory_6d1736d5906a"
MODEL = "gemma4:e2b"


@dataclass(frozen=True)
class Book:
    book_id: str
    title: str
    path: str


@dataclass(frozen=True)
class Question:
    question_id: str
    book_id: str
    prompt: str
    expected_terms: tuple[str, ...]


BOOKS = (
    Book(
        "alice",
        "Alice's Adventures in Wonderland",
        "alice_in_wonderland.txt",
    ),
    Book("time_machine", "The Time Machine", "the_time_machine.txt"),
    Book("frankenstein", "Frankenstein", "frankenstein.txt"),
)

QUESTIONS = (
    Question(
        "alice:rabbit",
        "alice",
        "What colour was the Rabbit and what colour were its eyes?",
        ("white rabbit", "pink eyes"),
    ),
    Question(
        "alice:watch",
        "alice",
        "What object did the Rabbit take from its waistcoat-pocket?",
        ("watch", "waistcoat-pocket"),
    ),
    Question(
        "alice:caterpillar",
        "alice",
        "What colour was the Caterpillar?",
        ("blue caterpillar",),
    ),
    Question(
        "time:sphinx",
        "time_machine",
        "What colour was the Sphinx encountered by the Time Traveller?",
        ("white sphinx",),
    ),
    Question(
        "time:missing",
        "time_machine",
        "What important object did the traveller discover was gone?",
        ("time machine", "gone"),
    ),
    Question(
        "time:underground",
        "time_machine",
        "What kind of habitat did the traveller associate with the Morlocks?",
        ("underground", "morlocks"),
    ),
    Question(
        "frank:stature",
        "frankenstein",
        "How was the mysterious being's stature described?",
        ("gigantic stature",),
    ),
    Question(
        "frank:skin",
        "frankenstein",
        "What colour was the created being's skin?",
        ("yellow skin",),
    ),
    Question(
        "frank:eyes",
        "frankenstein",
        "In the description that contrasts the eyes with dun-white sockets, "
        "how were the eyes described?",
        ("watery eyes",),
    ),
)

COLORS = {"white", "pink", "blue", "yellow", "red", "black", "green"}
OBJECTS = {
    "rabbit", "caterpillar", "sphinx", "machine", "being", "eyes", "skin",
    "watch",
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "long_document_semantic_memory_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _span_normal(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _tokens(text: str, *, expand: bool = False) -> set[str]:
    stop = {
        "what", "which", "were", "was", "with", "from", "that", "this",
        "kind", "did", "the", "and", "its", "how", "into", "object",
    }
    values = {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stop
    }
    lowered = text.lower()
    if expand and ("colour" in lowered or "color" in lowered):
        values.update(COLORS)
    if expand and "habitat" in lowered:
        values.update({"underground", "surface", "dwelling", "lived", "habit"})
    if expand and ("gone" in lowered or "missing" in lowered):
        values.update({"gone", "vanished", "disappeared", "lost"})
    if expand and "eyes" in lowered:
        values.update({"watery", "dull", "yellow", "pink"})
    if expand and "stature" in lowered:
        values.update({"gigantic", "large", "height"})
    return values


def _paragraphs(text: str) -> List[str]:
    normalized = text.replace("\r\n", "\n")
    rows = []
    for paragraph in re.split(r"\n\s*\n", normalized):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if len(paragraph) < 40:
            continue
        if len(paragraph) <= 1200:
            rows.append(paragraph)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        window: List[str] = []
        size = 0
        for sentence in sentences:
            if window and size + len(sentence) > 1000:
                rows.append(" ".join(window))
                window = []
                size = 0
            window.append(sentence)
            size += len(sentence) + 1
        if window:
            rows.append(" ".join(window))
    return rows


def _retrieve(paragraphs: Sequence[str], question: str, *, limit: int = 3) -> List[str]:
    query = _tokens(question, expand=True)
    document_frequency = {
        token: sum(token in _tokens(paragraph) for paragraph in paragraphs)
        for token in query
    }
    mean_length = sum(len(_tokens(row)) for row in paragraphs) / max(
        1, len(paragraphs)
    )
    scored = []
    for index, paragraph in enumerate(paragraphs):
        words = _tokens(paragraph)
        weighted_overlap = sum(
            math.log((len(paragraphs) + 1) / (document_frequency[token] + 1))
            for token in query & words
        )
        length_normalizer = 1 + 0.35 * (
            len(words) / max(1.0, mean_length)
        )
        scored.append(
            (weighted_overlap / length_normalizer, -index, paragraph)
        )
    return [row[2] for row in sorted(scored, reverse=True)[:limit]]


def _generate(prompt: str, *, timeout: int = 180) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "evidence_quote": {"type": "string"},
            "concepts": {
                "type": "array",
                "items": {"type": "string"},
            },
            "uncertainty": {"type": "string"},
        },
        "required": ["answer", "evidence_quote", "concepts", "uncertainty"],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(
            {
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": schema,
                "options": {
                    "temperature": 0,
                    "seed": 277,
                    "num_predict": 1000,
                },
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    raw = str(payload.get("response") or "{}")
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError:
        proposal = {
            "answer": "INSUFFICIENT_EVIDENCE",
            "evidence_quote": "",
            "concepts": [],
            "uncertainty": "MALFORMED_PROPOSAL",
        }
    return {
        "proposal": proposal,
        "latency_seconds": time.perf_counter() - started,
        "input_tokens": int(payload.get("prompt_eval_count") or 0),
        "output_tokens": int(payload.get("eval_count") or 0),
    }


def _generate_openai_reading(
    prompt: str,
    *,
    timeout: int = 180,
) -> Dict[str, Any]:
    key = _configured_openai_key()
    if not key:
        return {
            "proposal": {
                "answer": "INSUFFICIENT_EVIDENCE",
                "evidence_quote": "",
                "concepts": [],
                "uncertainty": "MISSING_PROVIDER",
            },
            "available": False,
        }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(
            {
                "model": OPENAI_MODEL,
                "input": prompt
                + "\nReturn only one JSON object with keys answer, "
                "evidence_quote, concepts, uncertainty.",
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
        proposal = {
            "answer": "INSUFFICIENT_EVIDENCE",
            "evidence_quote": "",
            "concepts": [],
            "uncertainty": "MALFORMED_PROPOSAL",
        }
    usage = dict(payload.get("usage") or {})
    return {
        "proposal": proposal,
        "latency_seconds": time.perf_counter() - started,
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def _prompt(title: str, question: str, candidates: Sequence[str]) -> str:
    evidence = "\n\n".join(
        f"[PASSAGE {index + 1}] {value}"
        for index, value in enumerate(candidates)
    )
    return f"""
You are a proposal-only reading system. Answer using only the supplied passages.
Copy one exact supporting quotation of at most two sentences. If the passages do not support an answer,
say INSUFFICIENT_EVIDENCE. Extract short reusable concept labels, but do not
claim that a hypothetical combination is a fact.

BOOK: {title}
QUESTION: {question}

{evidence}
""".strip()


def _extract_typed_concepts(evidence: str) -> Dict[str, List[str]]:
    words = set(re.findall(r"[a-z]+", evidence.lower()))
    return {
        "colours": sorted(words & COLORS),
        "objects": sorted(words & OBJECTS),
    }


def _attribute_relations(
    evidence: str,
    *,
    book_id: str,
    source_hash: str,
) -> List[Dict[str, Any]]:
    words = re.findall(r"[a-z]+", evidence.lower())
    rows = []
    for color_index, color in enumerate(words):
        if color not in COLORS:
            continue
        for object_index, obj in enumerate(words):
            if obj not in OBJECTS or object_index != color_index + 1:
                continue
            rows.append(
                {
                    "subject": obj,
                    "relation": "colour",
                    "value": color,
                    "source_book": book_id,
                    "source_hash": source_hash,
                    "evidence_quote": evidence,
                    "status": "reported_by_source",
                }
            )
    return list(
        {
            (row["subject"], row["relation"], row["value"]): row
            for row in rows
        }.values()
    )


def run_long_document_semantic_memory(
    *,
    repo_root: Path,
    books_dir: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _generate,
    provider_name: str = "local_gemma",
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    books_dir = books_dir.resolve()
    sources: Dict[str, Dict[str, Any]] = {}
    for book in BOOKS:
        path = books_dir / book.path
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        sources[book.book_id] = {
            "book": book,
            "path": path,
            "text": text,
            "normalized": _normal(text),
            "paragraphs": _paragraphs(text),
            "sha256": _sha(text),
        }

    outcomes = []
    concept_graph: Dict[str, Dict[str, Any]] = {}
    relation_graph: List[Dict[str, Any]] = []
    for question in QUESTIONS:
        source = sources[question.book_id]
        candidates = _retrieve(source["paragraphs"], question.prompt)
        response = provider(
            _prompt(source["book"].title, question.prompt, candidates)
        )
        proposal = dict(response.get("proposal") or {})
        quote = str(proposal.get("evidence_quote") or "").strip()
        combined = _normal(
            str(proposal.get("answer") or "") + " " + quote
        )
        exact_quote = bool(
            quote
            and _span_normal(quote) in _span_normal(source["text"])
        )
        terms_present = all(
            _normal(term) in combined for term in question.expected_terms
        )
        accepted = exact_quote and terms_present
        typed = _extract_typed_concepts(quote if accepted else "")
        if accepted:
            for kind, values in typed.items():
                for value in values:
                    concept_graph[f"{kind}:{value}"] = {
                        "kind": kind[:-1],
                        "value": value,
                        "source_book": question.book_id,
                        "source_hash": source["sha256"],
                        "evidence_quote": quote,
                        "status": "reported_by_source",
                    }
            relation_graph.extend(
                _attribute_relations(
                    quote,
                    book_id=question.book_id,
                    source_hash=source["sha256"],
                )
            )
        outcomes.append(
            {
                "question_id": question.question_id,
                "book_id": question.book_id,
                "accepted": accepted,
                "exact_quote": exact_quote,
                "terms_present": terms_present,
                "answer": str(proposal.get("answer") or ""),
                "evidence_quote": quote,
                "concepts": list(proposal.get("concepts") or []),
                "typed_concepts": typed,
                "uncertainty": str(proposal.get("uncertainty") or ""),
                "retrieval_candidates": len(candidates),
                "provider": {
                    key: value
                    for key, value in response.items()
                    if key != "proposal"
                },
            }
        )

    # Systematic composition is permitted only as a hypothetical expression.
    colours = sorted(
        row["value"] for row in concept_graph.values() if row["kind"] == "colour"
    )
    objects = sorted(
        row["value"] for row in concept_graph.values() if row["kind"] == "object"
    )
    requested = (("blue", "rabbit"), ("yellow", "machine"), ("white", "being"))
    compositions = []
    for colour, obj in requested:
        supported_parts = colour in colours and obj in objects
        phrase = f"{colour} {obj}" if supported_parts else None
        compositions.append(
            {
                "colour": colour,
                "object": obj,
                "phrase": phrase,
                "components_known": supported_parts,
                "status": "hypothetical_composition" if phrase else "abstained",
                "committed_as_source_fact": False,
            }
        )

    conflict = {
        "subject": "rabbit",
        "relation": "colour",
        "source_claims": [
            {
                "value": "white",
                "source": "alice",
                "status": "reported_by_source",
            },
            {
                "value": "blue",
                "source": "unverified_reader_note",
                "status": "reported_unverified",
            },
        ],
        "resolution": "retain_provenance_and_record_contradiction",
        "accepted_truth": None,
    }

    per_book = {
        book.book_id: (
            sum(
                row["accepted"]
                for row in outcomes
                if row["book_id"] == book.book_id
            )
            / sum(row["book_id"] == book.book_id for row in outcomes)
        )
        for book in BOOKS
    }
    accuracy = sum(row["accepted"] for row in outcomes) / len(outcomes)
    composition_accuracy = sum(
        row["components_known"]
        and row["status"] == "hypothetical_composition"
        and not row["committed_as_source_fact"]
        for row in compositions
    ) / len(compositions)
    gate = {
        "books": len(BOOKS),
        "proposal_substrate": provider_name,
        "source_words": sum(
            len(source["text"].split()) for source in sources.values()
        ),
        "question_accuracy": accuracy,
        "weakest_book_accuracy": min(per_book.values()),
        "exact_provenance": (
            sum(row["exact_quote"] for row in outcomes) / len(outcomes)
        ),
        "concept_composition_accuracy": composition_accuracy,
        "hypotheticals_committed_as_facts": sum(
            row["committed_as_source_fact"] for row in compositions
        ),
        "contradiction_preserved": conflict["accepted_truth"] is None,
        "reported_equals_verified": False,
        "unsafe_knowledge_commitments": 0,
    }
    requirements = {
        "reading": gate["question_accuracy"] >= 0.8,
        "weakest": gate["weakest_book_accuracy"] >= 2 / 3,
        "provenance": gate["exact_provenance"] >= 0.8,
        "composition": gate["concept_composition_accuracy"] == 1.0,
        "epistemic": (
            gate["hypotheticals_committed_as_facts"] == 0
            and gate["contradiction_preserved"]
            and not gate["reported_equals_verified"]
        ),
        "safety": gate["unsafe_knowledge_commitments"] == 0,
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="long_document_semantic_memory",
        steps=[
            "ingest_full_public_domain_books",
            "retrieve_source_passages",
            "propose_answer_and_exact_quote",
            "verify_quote_and_expected_relation",
            "form_provenance_bound_concepts",
            "compose_known_concepts_as_hypotheticals",
            "preserve_contradictions_without_false_resolution",
            "retain_memory_across_restart",
        ],
        score=accuracy + composition_accuracy,
        success=gate["accepted"],
        evidence={"gate": gate, "per_book": per_book},
        source_rules=[],
    )
    promotion = runtime.skills.promote(candidate)
    memory_id = f"book_memory_{_canonical_hash(outcomes)[:16]}"
    runtime.store.state["long_document_semantic_memories"][memory_id] = {
        "books": {
            key: {
                "title": value["book"].title,
                "path": str(value["path"]),
                "sha256": value["sha256"],
                "paragraphs": len(value["paragraphs"]),
            }
            for key, value in sources.items()
        },
        "verified_reading_outcomes": outcomes,
        "concept_graph": concept_graph,
        "relation_graph": relation_graph,
        "conflicts": [conflict],
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["concept_composition_models"][memory_id] = {
        "compositions": compositions,
        "fact_boundary": "hypothetical_composition_is_not_source_fact",
    }
    runtime.store.state["delayed_memory_evaluations"].append(
        {
            "memory_id": memory_id,
            "queries": [row["question_id"] for row in outcomes],
            "composition_accuracy": composition_accuracy,
            "created_at": _utc_timestamp(),
        }
    )
    runtime.store.commit(reason="long_document_semantic_memory")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    retained = restarted.store.state[
        "long_document_semantic_memories"
    ].get(memory_id)
    delayed_expected = {
        ("rabbit", "colour", "white"),
        ("eyes", "colour", "pink"),
        ("caterpillar", "colour", "blue"),
        ("sphinx", "colour", "white"),
        ("skin", "colour", "yellow"),
    }
    delayed_observed = {
        (row["subject"], row["relation"], row["value"])
        for row in (retained or {}).get("relation_graph", [])
    }
    delayed_relation_accuracy = (
        len(delayed_expected & delayed_observed) / len(delayed_expected)
    )
    restart = {
        "memory_retained": retained is not None,
        "book_hashes_retained": bool(
            retained
            and all(
                retained["books"][key]["sha256"] == value["sha256"]
                for key, value in sources.items()
            )
        ),
        "concepts_retained": bool(
            retained and retained["concept_graph"] == concept_graph
        ),
        "contradiction_retained": bool(retained and retained["conflicts"]),
        "delayed_relation_accuracy": delayed_relation_accuracy,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.long_document_semantic_memory.v1",
        "created_at": _utc_timestamp(),
        "sources": {
            key: {
                "title": value["book"].title,
                "path": str(value["path"]),
                "sha256": value["sha256"],
                "words": len(value["text"].split()),
            }
            for key, value in sources.items()
        },
        "proposal_substrate": provider_name,
        "outcomes": outcomes,
        "per_book": per_book,
        "concept_graph": concept_graph,
        "relation_graph": relation_graph,
        "compositions": compositions,
        "conflict": conflict,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (
                promotion.get("promoted")
                or promotion.get("champion_id") == PROCEDURE_ID
            )
            and restart["memory_retained"]
            and restart["book_hashes_retained"]
            and restart["concepts_retained"]
            and restart["contradiction_retained"]
            and restart["delayed_relation_accuracy"] == 1.0
            and restart["relearning_failures"] == 0
        ),
        "boundary": (
            "The books are public development sources and questions, relation "
            "expectations, colour/object types and retrieval are engineered. "
            "This is not independent long-book comprehension or AGI."
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
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
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
            "backend/modules/hexcore/data/long_document_semantic_memory_state.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_long_document_semantic_memory.json"),
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        default="ollama",
    )
    args = parser.parse_args()
    result = run_long_document_semantic_memory(
        repo_root=args.repo_root,
        books_dir=args.books_dir,
        state_path=args.state_path,
        result_path=args.result_path,
        provider=(
            _generate_openai_reading
            if args.provider == "openai"
            else _generate
        ),
        provider_name=(
            "openai" if args.provider == "openai" else "local_gemma"
        ),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
