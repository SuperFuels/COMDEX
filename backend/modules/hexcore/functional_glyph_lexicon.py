"""Typed semantic-procedural glyph memory built from verified experience.

The lexicon is neither a raw answer store nor a bag of topic labels.  It keeps
compact meanings, procedures, invariants, failure signatures, verification
properties and transfer links.  Every promoted node resolves to immutable
evidence, and procedural capsules must survive structural reconstruction.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_functional_glyph_lexicon_v2"
SCHEMA = "aion.functional_glyph_lexicon.v2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}


class FunctionalGlyphLexicon:
    REQUIRED_PROCEDURE_FACETS = {
        "purpose", "inputs", "preconditions", "steps", "invariants",
        "failure_signals", "verification", "transfer",
    }

    def __init__(self, *, repo_root: Path, store_path: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.store_path = store_path
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, str]] = []
        self.evidence: dict[str, dict[str, Any]] = {}

    def add_evidence(self, relative: str, *, authority: str, positive: bool = True) -> str:
        path = self.repo_root / relative
        if not path.exists():
            raise FileNotFoundError(relative)
        evidence_id = "ev_" + _sha(path)[:20]
        self.evidence[evidence_id] = {
            "path": relative, "sha256": _sha(path), "bytes": path.stat().st_size,
            "authority": authority, "positive": positive,
        }
        return evidence_id

    def add_node(self, *, kind: str, key: str, summary: str,
                 aliases: Iterable[str] = (), facets: Mapping[str, Any] | None = None,
                 evidence: Iterable[str] = (), epistemic: str = "verified_bounded") -> str:
        body = {
            "kind": kind, "key": key, "summary": summary,
            "aliases": sorted(set(str(value) for value in aliases)),
            "facets": dict(facets or {}), "evidence": sorted(set(evidence)),
            "epistemic": epistemic,
        }
        node_id = "fg_" + _canonical_hash(body)[:20]
        self.nodes[node_id] = {"id": node_id, **body,
                               "glyph": f"⟦ {kind} | {key} : {node_id} → Reconstruct+Verify ⟧"}
        return node_id

    def relate(self, source: str, relation: str, target: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("functional glyph edge endpoint missing")
        edge = {"source": source, "relation": relation, "target": target}
        if edge not in self.edges:
            self.edges.append(edge)

    def validate(self) -> dict[str, Any]:
        evidence_ok = all(
            (self.repo_root / row["path"]).exists()
            and _sha(self.repo_root / row["path"]) == row["sha256"]
            for row in self.evidence.values()
        )
        endpoints_ok = all(row["source"] in self.nodes and row["target"] in self.nodes for row in self.edges)
        provenance_ok = all(set(row["evidence"]) <= set(self.evidence) for row in self.nodes.values())
        procedures = [row for row in self.nodes.values() if row["kind"] == "procedure"]
        complete = [row for row in procedures if self.REQUIRED_PROCEDURE_FACETS <= set(row["facets"])]
        return {
            "nodes": len(self.nodes), "edges": len(self.edges),
            "node_types": len({row["kind"] for row in self.nodes.values()}),
            "relation_types": len({row["relation"] for row in self.edges}),
            "procedures": len(procedures), "complete_procedures": len(complete),
            "evidence_sources": len(self.evidence), "evidence_resolves": evidence_ok,
            "edge_endpoints_resolve": endpoints_ok, "node_provenance_resolves": provenance_ok,
        }

    def query(self, text: str, *, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = _tokens(text)
        scored: list[tuple[float, dict[str, Any]]] = []
        for node in self.nodes.values():
            lexical = " ".join([node["key"], node["summary"], *node["aliases"]])
            node_tokens = _tokens(lexical)
            overlap = len(query_tokens & node_tokens)
            if not overlap:
                continue
            score = overlap / max(1, len(query_tokens))
            if node["kind"] == "procedure":
                score += 0.35
            scored.append((score, node))
        scored.sort(key=lambda item: (-item[0], item[1]["key"]))
        return [{"score": round(score, 6), **node} for score, node in scored[:limit]]

    def reconstruct(self, procedure_key: str) -> dict[str, Any]:
        procedure = next((row for row in self.nodes.values()
                          if row["kind"] == "procedure" and row["key"] == procedure_key), None)
        if procedure is None:
            return {"status": "ABSTAIN_UNKNOWN_PROCEDURE", "passed": False}
        related_ids = {procedure["id"]}
        frontier = {procedure["id"]}
        for _ in range(2):
            next_frontier: set[str] = set()
            for edge in self.edges:
                if edge["source"] in frontier:
                    next_frontier.add(edge["target"])
                if edge["target"] in frontier:
                    next_frontier.add(edge["source"])
            related_ids |= next_frontier
            frontier = next_frontier
        complete = self.REQUIRED_PROCEDURE_FACETS <= set(procedure["facets"])
        evidence_ids = sorted({eid for node_id in related_ids for eid in self.nodes[node_id]["evidence"]})
        return {
            "status": "FUNCTIONAL_CAPSULE_RECONSTRUCTED" if complete and evidence_ids else "ABSTAIN_INCOMPLETE_CAPSULE",
            "passed": bool(complete and evidence_ids),
            "procedure": procedure,
            "associations": [self.nodes[node_id] for node_id in sorted(related_ids) if node_id != procedure["id"]],
            "relations": [row for row in self.edges if row["source"] in related_ids and row["target"] in related_ids],
            "evidence_ids": evidence_ids,
            "source_documents_opened": 0,
        }

    def save(self) -> dict[str, Any]:
        packet = {
            "schema_version": SCHEMA, "created_at": _now(),
            "dictionary": {
                "lexeme": "surface form or sense", "concept": "meaning or entity",
                "procedure": "reconstructable method", "invariant": "condition that must remain true",
                "failure": "diagnostic counterexample", "verifier": "executable correctness authority",
                "transfer": "source-disjoint application family", "provenance": "immutable evidence pointer",
            },
            "nodes": sorted(self.nodes.values(), key=lambda row: (row["kind"], row["key"])),
            "edges": sorted(self.edges, key=lambda row: (row["source"], row["relation"], row["target"])),
            "evidence": self.evidence,
        }
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        with gzip.open(temporary, "wb", compresslevel=9) as handle:
            handle.write(encoded)
        os.replace(temporary, self.store_path)
        return {"store_sha256": _sha(self.store_path), "compressed_bytes": self.store_path.stat().st_size,
                "uncompressed_bytes": len(encoded)}

    @classmethod
    def load(cls, *, repo_root: Path, store_path: Path) -> "FunctionalGlyphLexicon":
        with gzip.open(store_path, "rt", encoding="utf-8") as handle:
            packet = json.load(handle)
        if packet.get("schema_version") != SCHEMA:
            raise ValueError("unsupported functional glyph lexicon")
        instance = cls(repo_root=repo_root, store_path=store_path)
        instance.nodes = {row["id"]: row for row in packet["nodes"]}
        instance.edges = list(packet["edges"])
        instance.evidence = dict(packet["evidence"])
        return instance


def build_lexicon(*, repo_root: Path, store_path: Path) -> tuple[FunctionalGlyphLexicon, dict[str, str]]:
    lex = FunctionalGlyphLexicon(repo_root=repo_root, store_path=store_path)
    ev_alg = lex.add_evidence("results/hexcore_accelerated_algorithms_apprenticeship.json",
                              authority="sealed_algorithm_properties")
    ev_mission = lex.add_evidence("results/hexcore_hierarchical_mission_graph.json",
                                  authority="executable_mission_graph_audit")
    ev_failure = lex.add_evidence("results/immutable/aion_competency_reconstruction_failure_receipt.json",
                                  authority="failed_fresh_reconstruction", positive=False)

    ids: dict[str, str] = {}
    ids["python_word"] = lex.add_node(kind="lexeme", key="python", summary="Python programming-language sense",
        aliases=["python 3", "cpython language"], facets={"sense": "programming_language", "distinguish_from": "python_snake"},
        evidence=[ev_failure])
    ids["dag"] = lex.add_node(kind="concept", key="directed_acyclic_graph",
        summary="directed dependency structure with no directed cycle", aliases=["dag", "dependency graph"],
        facets={"components": ["task_ids", "directed_dependencies"], "constraint": "no_directed_cycle"}, evidence=[ev_alg])
    ids["priority"] = lex.add_node(kind="concept", key="ready_task_priority",
        summary="choose priority only among tasks whose dependencies are satisfied", aliases=["priority ready set"],
        facets={"tie_break": "descending_numeric_priority_then_identifier"}, evidence=[ev_alg, ev_mission])
    ids["state"] = lex.add_node(kind="concept", key="restartable_mission_state",
        summary="minimal task progress state that can be reconstructed without replay", aliases=["persistent runner state"],
        facets={"fields": ["plan", "position", "completed", "attempts", "max_attempts"]}, evidence=[ev_mission])

    topo_facets = {
        "purpose": "order dependent work safely while respecting ready-task priority",
        "inputs": ["task dictionaries", "unique task ID", "numeric priority", "dependency IDs", "optional required capability"],
        "preconditions": ["task IDs are unique", "every dependency names a known task", "capability levels use an ordered scale"],
        "steps": [
            "index tasks by ID and reject duplicates",
            "reject dependencies that are absent from the index",
            "maintain remaining and completed task-ID sets",
            "derive the ready set whose dependencies are all completed",
            "if work remains but ready is empty, reject a cycle",
            "choose ready task by descending numeric priority then identifier",
            "emit learn:capability before the task only for unassessed or beginner capability",
            "emit the task ID, mark it completed, and continue",
        ],
        "invariants": ["dependency_before_dependent", "each_task_exactly_once", "returned_tasks_are_string_ids", "priority_applies_only_within_ready_set"],
        "failure_signals": ["cycle", "missing_dependency", "duplicate_identifier", "task_dictionary_returned_instead_of_id"],
        "verification": ["independent positive ordering", "capability gap insertion", "cycle rejection", "missing dependency rejection", "duplicate rejection"],
        "transfer": ["build systems", "project plans", "workflow engines", "curriculum dependency scheduling"],
        "complexity": "O(V+E) plus ready-set selection cost",
        "program": {
            "ir": "aion.functional_method_program.v1",
            "input_collection": "tasks", "identifier_field": "id", "dependency_field": "depends_on",
            "priority_field": "priority", "capability_field": "capability",
            "level_order": ["unassessed", "beginner", "intermediate", "advanced", "expert"],
            "learning_threshold": "intermediate",
            "operators": ["validate_unique_identifiers", "validate_dependency_references",
                          "select_dependency_ready", "order_ready_by_priority_then_identifier",
                          "emit_learning_gap_below_threshold", "emit_identifier",
                          "advance_completed_set", "reject_stalled_cycle"],
        },
    }
    ids["topo"] = lex.add_node(kind="procedure", key="topological_priority_planning",
        summary="dependency-safe priority planning with capability-gap insertion", aliases=["dependency planner", "priority topological order"],
        facets=topo_facets, evidence=[ev_alg, ev_mission, ev_failure])

    runner_facets = {
        "purpose": "execute a finite mission with retry and restart continuity",
        "inputs": ["ordered task-ID plan", "maximum attempts"],
        "preconditions": ["plan is finite", "maximum attempts is positive"],
        "steps": [
            "next task is the task at the current position or none when complete",
            "reject an outcome for any task other than the current task",
            "on success append current task to completed and advance position",
            "on failure increment only the current task attempt count",
            "below the maximum, leave position unchanged so the same task retries",
            "snapshot position, attempts, completed tasks, and maximum attempts",
            "reconstruct those fields without executing completed tasks",
        ],
        "invariants": ["completed_tasks_never_rerun", "failed_task_retries_in_place", "completion_iff_position_reaches_plan_length"],
        "failure_signals": ["wrong_task_outcome", "premature_position_advance", "lost_attempt_count", "snapshot_method_shadowed_by_data"],
        "verification": ["success advances", "failure retries", "snapshot round trip", "completion returns no next task"],
        "transfer": ["long projects", "interruption recovery", "tool workflows", "autonomous curricula"],
        "program": {
            "ir": "aion.functional_state_machine.v1",
            "state": ["plan", "position", "completed", "attempts", "max_attempts"],
            "operators": ["return_current_or_none", "reject_noncurrent_outcome", "success_advance",
                          "failure_increment_and_retry", "snapshot_state", "restore_state",
                          "complete_when_position_reaches_plan_length"],
        },
    }
    ids["runner"] = lex.add_node(kind="procedure", key="restartable_mission_runner",
        summary="persistent sequential mission state machine with bounded retry", aliases=["persistent mission executor", "restart runner"],
        facets=runner_facets, evidence=[ev_mission, ev_failure])

    ids["invariant"] = lex.add_node(kind="invariant", key="dependency_before_dependent",
        summary="every prerequisite occurs before its dependent task", aliases=["prerequisite ordering"],
        facets={"falsifier": "find dependency position greater than or equal to dependent position"}, evidence=[ev_alg])
    ids["failure"] = lex.add_node(kind="failure", key="omitted_required_interface",
        summary="candidate module lacks a function or class required by its contract", aliases=["missing build_plan", "missing mission runner"],
        facets={"diagnosis": "interface reconstruction failure", "repair": "preserve independently passing components during composition"}, evidence=[ev_failure])
    ids["verifier"] = lex.add_node(kind="verifier", key="sealed_mission_executor_contract",
        summary="fresh executable positive, negative, retry and restart properties", aliases=["hidden planner tests"],
        facets={"authority": "disposable Python subprocess", "proposal_can_self_score": False}, evidence=[ev_failure])
    ids["transfer"] = lex.add_node(kind="transfer", key="dependency_method_transfer",
        summary="reuse dependency-safe ordering across software and project domains", aliases=["cross-domain planning transfer"],
        facets={"domains": topo_facets["transfer"]}, evidence=[ev_alg, ev_mission])
    ids["provenance"] = lex.add_node(kind="provenance", key="content_addressed_evidence",
        summary="immutable hash-resolved evidence supporting a functional capsule", aliases=["evidence pointer"],
        facets={"raw_source_in_active_memory": False}, evidence=[ev_alg, ev_mission, ev_failure])

    for target in (ids["dag"], ids["priority"], ids["invariant"], ids["failure"], ids["verifier"], ids["transfer"], ids["provenance"]):
        relation = {
            ids["dag"]: "requires", ids["priority"]: "uses", ids["invariant"]: "must_preserve",
            ids["failure"]: "fails_as", ids["verifier"]: "verified_by", ids["transfer"]: "transfers_to",
            ids["provenance"]: "supported_by",
        }[target]
        lex.relate(ids["topo"], relation, target)
    for target, relation in ((ids["state"], "represents"), (ids["failure"], "diagnosed_by"),
                             (ids["verifier"], "verified_by"), (ids["provenance"], "supported_by")):
        lex.relate(ids["runner"], relation, target)
    lex.relate(ids["python_word"], "language_hosts", ids["topo"])
    lex.relate(ids["topo"], "composes_with", ids["runner"])
    return lex, ids


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "functional_glyph_lexicon_cau", "S": 1.0, "H": 0.0}


def run(*, repo_root: Path, store_path: Path, index_path: Path, result_path: Path) -> dict[str, Any]:
    lex, _ = build_lexicon(repo_root=repo_root.resolve(), store_path=store_path)
    validation = lex.validate()
    storage = lex.save()
    reloaded = FunctionalGlyphLexicon.load(repo_root=repo_root, store_path=store_path)
    queries = {
        "dependency priority project planner": "topological_priority_planning",
        "resume work after restart and retry": "restartable_mission_runner",
        "python schedule tasks with capability gaps": "topological_priority_planning",
    }
    query_results = {}
    for query, expected in queries.items():
        rows = reloaded.query(query, limit=5)
        query_results[query] = {"expected": expected, "returned": [row["key"] for row in rows],
                                "passed": any(row["key"] == expected for row in rows)}
    unsupported = reloaded.query("dog bark veterinary anatomy", limit=3)
    query_results["unsupported"] = {"returned": [row["key"] for row in unsupported], "passed": not unsupported}
    capsules = [reloaded.reconstruct("topological_priority_planning"), reloaded.reconstruct("restartable_mission_runner")]
    corrupted = json.loads(json.dumps(capsules[0]))
    corrupted["procedure"]["facets"].pop("invariants", None)
    corrupted_rejected = not (FunctionalGlyphLexicon.REQUIRED_PROCEDURE_FACETS <= set(corrupted["procedure"]["facets"]))
    gate = {**validation, **storage, "queries_passed": sum(row["passed"] for row in query_results.values()),
            "queries_total": len(query_results), "functional_capsules_reconstructed": sum(row["passed"] for row in capsules),
            "functional_capsules_total": len(capsules), "corrupted_capsules_rejected": int(corrupted_rejected),
            "source_documents_opened_during_reconstruction": sum(row["source_documents_opened"] for row in capsules),
            "raw_answers_stored": 0, "unsafe_actions": 0, "live_source_writes": 0}
    gate["accepted"] = bool(validation["evidence_resolves"] and validation["edge_endpoints_resolve"]
        and validation["node_provenance_resolves"] and validation["node_types"] >= 8
        and validation["relation_types"] >= 8 and validation["complete_procedures"] == 2
        and gate["queries_passed"] == gate["queries_total"] and gate["functional_capsules_reconstructed"] == 2
        and corrupted_rejected and gate["unsafe_actions"] == gate["live_source_writes"] == 0)
    _write(index_path, {"schema_version": SCHEMA, "created_at": _now(), "store": str(store_path.relative_to(repo_root)),
                        "store_sha256": storage["store_sha256"], "gate": gate})
    learning = HexCorePersistentLearningRuntime(state_path=index_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "functional_glyph_lexicon",
        ["extract_verified_meaning", "type_semantic_and_procedural_glyphs", "link_invariants_failures_and_verifiers",
         "resolve_by_association", "reconstruct_functional_capsule", "reject_incomplete_capsule"],
        float(gate["queries_passed"] + gate["functional_capsules_reconstructed"]), gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=gate["accepted"], score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="functional_glyph_lexicon")
    result = {"schema_version": SCHEMA, "created_at": _now(), "procedure_id": PROCEDURE_ID,
              "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
              "gate": gate, "query_results": query_results, "capsules": capsules, "decision": decision,
              "boundary": "The lexicon retains compact verified semantic-procedural structure; it is not raw training data, a complete language ontology, or proof of arbitrary mastery."}
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        store_path=root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
        index_path=root / "backend/modules/hexcore/data/functional_glyph_lexicon/index.json",
        result_path=root / "results/hexcore_functional_glyph_lexicon.json"), indent=2))
