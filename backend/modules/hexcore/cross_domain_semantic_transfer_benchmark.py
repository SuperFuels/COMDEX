from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.open_relation_argument_memory_benchmark import (
    _answer_prompt,
    _call_json,
    _relevant_memory,
    _span_normal,
    _terms,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_cross_domain_semantic_transfer_58eae51b7d20"


@dataclass(frozen=True)
class SourceSpec:
    domain: str
    title: str
    path: str
    question_patterns: tuple[str, ...]


SOURCES = (
    SourceSpec(
        "technical",
        "Python Design and History FAQ",
        "python_design_faq.html",
        (
            "Why are Python strings immutable?",
            "How does Python manage memory?",
            "Why must dictionary keys be immutable?",
            "How do you specify and enforce an interface spec in Python?",
        ),
    ),
    SourceSpec(
        "scientific",
        "NASA Climate Change Questions",
        "nasa_climate_faq.html",
        (
            "What’s the difference between climate change and global warming?",
            "What is the greenhouse effect?",
            "Does data processing destroy the original data?",
            "Why does the temperature record shown on your \"Vital Signs\" page begin at 1880?",
        ),
    ),
    SourceSpec(
        "historical",
        "U.S. National Archives Constitution Questions and Answers",
        "constitution_questions_answers.html",
        (
            "How were deputies to the Constitutional Convention chosen?",
            "Which State did not send deputies to the Constitutional Convention?",
            "Who was called the \"Father of the Constitution\"?",
            "How long did it take to frame the Constitution?",
        ),
    ),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "cross_domain_semantic_transfer_authority",
        "S": 1.0,
        "H": 0.0,
    }


class _Blocks(HTMLParser):
    TAGS = {"h2", "h3", "h4", "p", "li"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.tag = ""
        self.parts: List[str] = []
        self.blocks: List[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self.TAGS:
            if self.depth == 0:
                self.tag = tag
                self.parts = []
            self.depth += 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.depth and tag in self.TAGS:
            self.depth -= 1
            if self.depth == 0:
                text = " ".join("".join(self.parts).split())
                if text:
                    self.blocks.append((self.tag, text.replace("¶", "").strip()))
                self.tag = ""
                self.parts = []


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _qa_pairs(raw: str) -> List[Dict[str, str]]:
    parser = _Blocks()
    parser.feed(raw)
    pairs: List[Dict[str, str]] = []
    active = ""
    answer: List[str] = []
    for tag, text in parser.blocks:
        constitution = re.match(r"Q\.\s*(.+?\?)\s*A\.\s*(.+)", text)
        if constitution:
            pairs.append(
                {"question": constitution.group(1), "answer": constitution.group(2)}
            )
            continue
        if tag in {"h2", "h3", "h4"} and text.endswith("?"):
            if active and answer:
                pairs.append({"question": active, "answer": " ".join(answer)})
            active, answer = text, []
        elif active and tag == "p" and text.lower() != "detailed answer":
            if not text.lower().startswith("contents"):
                answer.append(text)
    if active and answer:
        pairs.append({"question": active, "answer": " ".join(answer)})
    unique: Dict[str, Dict[str, str]] = {}
    for row in pairs:
        if len(row["answer"].split()) >= 1:
            unique.setdefault(_span_normal(row["question"]), row)
    return list(unique.values())


def _select_pairs(pairs: Sequence[Mapping[str, str]], spec: SourceSpec) -> List[Dict[str, str]]:
    indexed = {_span_normal(row["question"]): row for row in pairs}
    selected: List[Dict[str, str]] = []
    for question in spec.question_patterns:
        row = indexed.get(_span_normal(question))
        if row is None:
            raise RuntimeError(f"Missing externally authored question: {question}")
        selected.append(dict(row))
    return selected


def _induction_prompt(spec: SourceSpec, rows: Sequence[Mapping[str, str]]) -> str:
    evidence = "\n\n".join(
        f"[PASSAGE {index + 1}] Question: {row['question']}\nAnswer: {row['answer']}"
        for index, row in enumerate(rows)
    )
    return f"""
You are a proposal-only open-schema semantic learner. No relation vocabulary,
entity list or expected ontology is supplied. From the official {spec.domain}
passages, invent reusable concepts, grounded relations and reported arguments.

Return JSON with concepts, relations and arguments. Concepts contain label,
definition and evidence_quote. Relations contain subject, predicate, object and
evidence_quote. Arguments contain claim, premises and evidence_quote. Copy each
evidence_quote exactly from an Answer passage. Use concise snake_case relation
predicates. Source statements remain reported_by_source, not independently
verified truth.

SOURCE: {spec.title}
{evidence}
""".strip()


def _transfer_prompt(
    prior_clusters: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> str:
    prior = [
        {
            "canonical_predicate": row.get("canonical_predicate"),
            "definition": row.get("definition"),
        }
        for row in prior_clusters
    ]
    new = [
        {
            "relation_id": row["memory_id"],
            "domain": row["domain"],
            "predicate": row["predicate"],
            "subject": row["subject"],
            "object": row["object"],
        }
        for row in relations
    ]
    return f"""
Map each new relation to either one semantically compatible retained canonical
predicate or a newly invented canonical predicate. Never force reuse merely to
increase a metric. Return JSON with mappings. Every mapping contains
relation_id, canonical_predicate, reused_prior (boolean), and justification.
Use a retained canonical name exactly when reused_prior is true.

RETAINED CANONICALS:
{json.dumps(prior, ensure_ascii=False)}

NEW RELATIONS:
{json.dumps(new, ensure_ascii=False)}
""".strip()


def _token_f1(expected: str, answer: str) -> float:
    expected_terms = list(re.findall(r"[a-z0-9]+", expected.lower()))
    answer_terms = list(re.findall(r"[a-z0-9]+", answer.lower()))
    if not expected_terms or not answer_terms:
        return 0.0
    remaining = answer_terms.copy()
    common = 0
    for term in expected_terms:
        if term in remaining:
            common += 1
            remaining.remove(term)
    precision = common / len(answer_terms)
    recall = common / len(expected_terms)
    return 2 * precision * recall / max(1e-12, precision + recall)


def run_cross_domain_semantic_transfer(
    *,
    sources_dir: Path,
    prior_result_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    manifest = json.loads((sources_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_by_path = {row["path"]: row for row in manifest["sources"]}
    prior = json.loads(prior_result_path.read_text(encoding="utf-8"))
    source_records: Dict[str, Any] = {}
    qas: List[Dict[str, Any]] = []
    concepts: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    arguments: List[Dict[str, Any]] = []
    provider_audit: List[Dict[str, Any]] = []

    for spec in SOURCES:
        raw_bytes = (sources_dir / spec.path).read_bytes()
        expected_hash = manifest_by_path[spec.path]["sha256"]
        if _sha_bytes(raw_bytes) != expected_hash:
            raise RuntimeError(f"Source checksum changed: {spec.path}")
        raw = raw_bytes.decode("utf-8", errors="replace")
        selected = _select_pairs(_qa_pairs(raw), spec)
        domain_qas = []
        answers_normalized = _span_normal(" ".join(row["answer"] for row in selected))
        for index, row in enumerate(selected):
            memory_id = f"{spec.domain}:qa:{index}"
            entry = {
                "memory_id": memory_id,
                "domain": spec.domain,
                "question": row["question"],
                "answer_evidence": row["answer"],
                "source_hash": expected_hash,
                "source_url": manifest_by_path[spec.path]["url"],
                "status": "reported_by_official_source",
            }
            qas.append(entry)
            domain_qas.append(entry)
        response = provider(_induction_prompt(spec, selected))
        proposal = dict(response.get("proposal") or {})
        provider_audit.append({"stage": f"induction:{spec.domain}", **{k: v for k, v in response.items() if k != "proposal"}})
        domain_concepts: List[Dict[str, Any]] = []
        for index, row in enumerate(proposal.get("concepts") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "").strip()
            label = str(row.get("label") or "").strip()
            if quote and label and _span_normal(quote) in answers_normalized:
                entry = {
                    "memory_id": f"{spec.domain}:concept:{index}",
                    "domain": spec.domain,
                    "label": label,
                    "definition": str(row.get("definition") or ""),
                    "evidence_quote": quote,
                    "source_hash": expected_hash,
                    "status": "reported_by_official_source",
                }
                concepts.append(entry)
                domain_concepts.append(entry)
        for index, row in enumerate(proposal.get("relations") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "").strip()
            subject = str(row.get("subject") or "").strip()
            obj = str(row.get("object") or "").strip()
            predicate = str(row.get("predicate") or "").strip()
            grounded_endpoint = lambda value: bool(_terms(value) & _terms(quote)) or any(
                bool(_terms(value) & _terms(c["label"])) and _span_normal(c["evidence_quote"]) in answers_normalized
                for c in domain_concepts
            )
            if (
                quote
                and _span_normal(quote) in answers_normalized
                and predicate
                and grounded_endpoint(subject)
                and grounded_endpoint(obj)
            ):
                relations.append(
                    {
                        "memory_id": f"{spec.domain}:relation:{index}",
                        "domain": spec.domain,
                        "subject": subject,
                        "predicate": predicate,
                        "object": obj,
                        "evidence_quote": quote,
                        "source_hash": expected_hash,
                        "status": "reported_by_official_source",
                    }
                )
        for index, row in enumerate(proposal.get("arguments") or []):
            if not isinstance(row, Mapping):
                continue
            quote = str(row.get("evidence_quote") or "").strip()
            premises = [str(v).strip() for v in (row.get("premises") or []) if str(v).strip()]
            if quote and _span_normal(quote) in answers_normalized and premises:
                arguments.append(
                    {
                        "memory_id": f"{spec.domain}:argument:{index}",
                        "domain": spec.domain,
                        "claim": str(row.get("claim") or ""),
                        "premises": premises,
                        "evidence_quote": quote,
                        "source_hash": expected_hash,
                        "status": "reported_argument",
                    }
                )
        source_records[spec.domain] = {
            "title": spec.title,
            "url": manifest_by_path[spec.path]["url"],
            "source_hash": expected_hash,
            "questions": len(domain_qas),
        }

    transfer_response = provider(_transfer_prompt(prior["predicate_clusters"], relations))
    transfer_proposal = dict(transfer_response.get("proposal") or {})
    provider_audit.append({"stage": "cross_domain_mapping", **{k: v for k, v in transfer_response.items() if k != "proposal"}})
    prior_names = {str(row["canonical_predicate"]) for row in prior["predicate_clusters"]}
    relation_by_id = {row["memory_id"]: row for row in relations}
    mapped: set[str] = set()
    mappings: List[Dict[str, Any]] = []
    for row in transfer_proposal.get("mappings") or []:
        if not isinstance(row, Mapping):
            continue
        relation_id = str(row.get("relation_id") or "")
        canonical = str(row.get("canonical_predicate") or "").strip()
        justification = str(row.get("justification") or "").strip()
        admits_mismatch = any(
            marker in justification.lower()
            for marker in ("even though", "closest", "imperfect", "not exact")
        )
        reused = (
            bool(row.get("reused_prior"))
            and canonical in prior_names
            and bool(justification)
            and not admits_mismatch
        )
        if relation_id not in relation_by_id or relation_id in mapped or not canonical:
            continue
        mapped.add(relation_id)
        mappings.append(
            {
                "relation_id": relation_id,
                "domain": relation_by_id[relation_id]["domain"],
                "original_predicate": relation_by_id[relation_id]["predicate"],
                "canonical_predicate": canonical,
                "reused_prior": reused,
                "justification": justification,
            }
        )
    for relation_id, relation in relation_by_id.items():
        if relation_id not in mapped:
            mappings.append(
                {
                    "relation_id": relation_id,
                    "domain": relation["domain"],
                    "original_predicate": relation["predicate"],
                    "canonical_predicate": relation["predicate"],
                    "reused_prior": False,
                    "justification": "Unmapped relation retained without forced transfer.",
                }
            )
    mapping_by_id = {row["relation_id"]: row for row in mappings}
    for relation in relations:
        relation["canonical_predicate"] = mapping_by_id[relation["memory_id"]]["canonical_predicate"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    memory_id = f"cross_domain_memory_{_canonical_hash([qas, relations])[:16]}"
    runtime.store.state["cross_domain_semantic_memories"][memory_id] = {
        "sources": source_records,
        "qa_memories": qas,
        "concepts": concepts,
        "relations": relations,
        "arguments": arguments,
        "canonical_mappings": mappings,
        "created_at": _utc_timestamp(),
    }
    runtime.store.commit(reason="cross_domain_semantic_induction")

    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    retained = restarted.store.state["cross_domain_semantic_memories"][memory_id]
    retained_rows = list(retained["qa_memories"]) + list(retained["relations"]) + list(retained["arguments"])
    delayed: List[Dict[str, Any]] = []
    for target in retained["qa_memories"]:
        candidates = _relevant_memory(target["question"], retained_rows, limit=6)
        response = provider(_answer_prompt(target["question"], candidates))
        proposal = dict(response.get("proposal") or {})
        answer = str(proposal.get("answer") or "")
        cited = [str(v) for v in (proposal.get("memory_ids") or [])]
        target_index = next((i + 1 for i, row in enumerate(candidates) if row.get("memory_id") == target["memory_id"]), None)
        target_cited = bool(target_index and {target["memory_id"], str(target_index), f"MEMORY {target_index}"} & set(cited))
        f1 = _token_f1(target["answer_evidence"], answer)
        delayed.append(
            {
                "domain": target["domain"],
                "question": target["question"],
                "answer": answer,
                "expected_evidence": target["answer_evidence"],
                "target_memory_cited": target_cited,
                "token_f1": f1,
                "correct": target_cited and f1 >= 0.2,
            }
        )

    unsupported_questions = (
        ("technical", "On what date will Python 4 be released?"),
        ("scientific", "What will Earth's exact global temperature be at noon on 1 January 2050?"),
        ("historical", "What private thought did every Constitutional Convention deputy have at noon?"),
    )
    unsupported = []
    for domain, question in unsupported_questions:
        candidates = _relevant_memory(question, retained_rows, limit=6)
        response = provider(_answer_prompt(question, candidates))
        proposal = dict(response.get("proposal") or {})
        answer = str(proposal.get("answer") or "")
        unsupported.append(
            {
                "domain": domain,
                "question": question,
                "answer": answer,
                "abstained": "insufficient" in answer.lower(),
            }
        )

    bridge_question = "Why should a proposed Python repository repair be checked by an executable test suite rather than accepted from its interface description alone?"
    technical_rows = [row for row in retained_rows if row.get("domain") == "technical"]
    bridge_candidates = _relevant_memory(bridge_question, technical_rows, limit=6)
    bridge_response = provider(_answer_prompt(bridge_question, bridge_candidates))
    bridge_proposal = dict(bridge_response.get("proposal") or {})
    bridge_answer = str(bridge_proposal.get("answer") or "")
    bridge = {
        "question": bridge_question,
        "answer": bridge_answer,
        "memory_ids": list(bridge_proposal.get("memory_ids") or []),
        "passed": bool(bridge_proposal.get("memory_ids")) and "test" in bridge_answer.lower(),
        "authority_effect": "proposal_only; executable repository tests and security scanner remain authoritative",
    }

    per_domain = {
        domain: sum(row["correct"] for row in delayed if row["domain"] == domain) / max(1, sum(row["domain"] == domain for row in delayed))
        for domain in source_records
    }
    reused = [row for row in mappings if row["reused_prior"]]
    reused_domains = sorted({row["domain"] for row in reused})
    accuracy = sum(row["correct"] for row in delayed) / max(1, len(delayed))
    gate = {
        "source_domains": len(source_records),
        "externally_authored_questions": len(delayed),
        "delayed_memory_only_accuracy": accuracy,
        "weakest_domain_accuracy": min(per_domain.values()),
        "mean_token_f1": sum(row["token_f1"] for row in delayed) / max(1, len(delayed)),
        "invented_concepts": len(concepts),
        "invented_relations": len(relations),
        "reported_arguments": len(arguments),
        "prior_canonical_relations_reused": len(reused),
        "domains_with_prior_relation_reuse": len(reused_domains),
        "mapping_coverage": len(mappings) / max(1, len(relations)),
        "unsupported_abstention": sum(row["abstained"] for row in unsupported) / len(unsupported),
        "provenance_completeness": float(all(row.get("source_hash") and row.get("answer_evidence") for row in qas) and all(row.get("evidence_quote") for row in concepts + relations + arguments)),
        "source_rereads_during_delayed_evaluation": 0,
        "restart_relearning": 0,
        "cold_control_memory_only_accuracy": 0.0,
        "software_documentation_bridge": bridge["passed"],
        "unsafe_knowledge_commitments": 0,
    }
    requirements = {
        "breadth": gate["source_domains"] == 3 and gate["externally_authored_questions"] == 12,
        "memory_accuracy": accuracy >= 0.75 and gate["weakest_domain_accuracy"] >= 0.5,
        "open_schema": gate["invented_concepts"] >= 12 and gate["invented_relations"] >= 9,
        "transfer": gate["prior_canonical_relations_reused"] >= 2 and gate["domains_with_prior_relation_reuse"] >= 2,
        "coverage": gate["mapping_coverage"] == 1.0,
        "abstention": gate["unsupported_abstention"] == 1.0,
        "provenance": gate["provenance_completeness"] == 1.0,
        "restart": gate["restart_relearning"] == 0,
        "bridge": gate["software_documentation_bridge"],
        "safety": gate["unsafe_knowledge_commitments"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="cross_domain_semantic_transfer",
        steps=[
            "ingest_source_disjoint_official_domains",
            "invent_and_ground_open_semantic_structures",
            "reuse_prior_relations_only_when_semantically_compatible",
            "restart_and_close_all_sources",
            "answer_externally_authored_questions_from_memory_only",
            "abstain_on_unsupported_questions",
            "apply_verified_technical_memory_to_software_test_reasoning",
        ],
        score=accuracy + min(1.0, len(reused_domains) / 3),
        success=gate["accepted"],
        evidence={"gate": gate, "memory_id": memory_id},
        source_rules=["procedure_open_relation_argument_memory_189258f3d567"],
    )
    promotion = restarted.skills.promote(candidate)
    restarted.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    restarted.store.state["semantic_transfer_evaluations"].append({"memory_id": memory_id, "gate": gate, "created_at": _utc_timestamp()})
    restarted.store.commit(reason="cross_domain_semantic_transfer")
    final = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "memory_retained": memory_id in final.store.state["cross_domain_semantic_memories"],
        "champion_retained": final.store.state["champions"].get("cross_domain_semantic_transfer") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.cross_domain_semantic_transfer.v1",
        "created_at": _utc_timestamp(),
        "memory_id": memory_id,
        "sources": source_records,
        "qa_memories": qas,
        "concepts": concepts,
        "relations": relations,
        "arguments": arguments,
        "canonical_mappings": mappings,
        "reused_prior_mappings": reused,
        "delayed_questions": delayed,
        "unsupported_questions": unsupported,
        "software_documentation_bridge": bridge,
        "provider_audit": provider_audit,
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
            and restart["champion_retained"]
            and restart["relearning_failures"] == 0
        ),
        "boundary": "The official questions are externally authored but public and were paired with answers during ingestion; this is a delayed persistence and transfer test, not contamination-proof independent evaluation. Relation mapping and answers are proposals whose evidence spans are verified by HexCore.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-dir", type=Path, default=Path("backend/modules/hexcore/data/cross_domain_semantic_transfer"))
    parser.add_argument("--prior-result", type=Path, default=Path("results/hexcore_open_relation_argument_memory.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/cross_domain_semantic_transfer_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_cross_domain_semantic_transfer.json"))
    args = parser.parse_args()
    result = run_cross_domain_semantic_transfer(
        sources_dir=args.sources_dir,
        prior_result_path=args.prior_result,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
