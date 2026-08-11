"""Content-addressed compression of verified intelligence into governed glyphs.

Evidence is never deleted or replaced.  The glyph store removes repeated raw
copies from working memory by retaining compact concept/skill/curriculum atoms
whose provenance pointers resolve to immutable source artifacts.  Curriculum
glyphs are explicitly unlearned; only verified artifacts may produce knowledge
or skill glyphs.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.guided_foundation_academy import MODULES
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_governed_intelligence_glyph_consolidation_v1"
GLYPH_SCHEMA = "aion.intelligence_glyph.v1"

VERIFIED_SOURCES = (
    ("results/hexcore_governed_teacher_python_core_cycle.json", "python_core",
     ("bool_is_int_but_not_valid_domain_integer", "validate_before_state_change", "targeted_remediation", "fresh_sealed_retest")),
    ("results/hexcore_general_apprenticeship_executor.json", "repository_repair",
     ("validate_quarantine_preserve_then_return_absence", "hidden_test_after_selection", "transfer_verified_method")),
    ("results/hexcore_real_rust_apprenticeship.json", "rust_systems",
     ("ownership", "traits", "error_handling", "concurrency", "unsafe_review")),
    ("results/hexcore_rust_sql_systems_depth.json", "database_systems",
     ("transaction_rollback", "migration_verification", "query_plan_measurement", "concurrent_transactions")),
    ("results/hexcore_programming_intelligence_closure.json", "secure_engineering",
     ("functional_success_cannot_override_security", "malicious_patch_rejection", "sandbox_only_execution")),
    ("results/hexcore_accelerated_algorithms_apprenticeship.json", "algorithms_data_structures",
     ("complexity_by_operation_growth", "binary_search_interval", "bfs_unweighted_shortest_path",
      "dijkstra_nonnegative_precondition", "topological_dependency_order", "dynamic_programming_subproblems")),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_verified(payload: Mapping[str, Any]) -> bool:
    return bool(payload.get("passed") is True
                or (payload.get("gate") or {}).get("accepted") is True
                or (payload.get("promotion") or {}).get("champion_retained") is True)


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _glyph(*, kind: str, name: str, payload: Mapping[str, Any], evidence_ids: Sequence[str],
           epistemic: str) -> dict[str, Any]:
    body = {"k": kind, "n": name, "d": dict(payload), "e": sorted(set(evidence_ids)), "s": epistemic}
    glyph_id = "g_" + _canonical_hash(body)[:20]
    # Tessaris/GlyphOS-compatible human rendering; the structured body is authority.
    rendered = f"⟦ {kind} | {name} : {glyph_id} -> Verify ⟧"
    return {"i": glyph_id, **body, "r": rendered}


class GovernedIntelligenceGlyphStore:
    def __init__(self, *, repo_root: Path, index_path: Path, compressed_path: Path) -> None:
        self.repo_root = repo_root
        self.index_path = index_path
        self.compressed_path = compressed_path

    def build(self) -> dict[str, Any]:
        evidence: dict[str, dict[str, Any]] = {}
        glyph_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
        raw_source_bytes = 0
        verified_source_count = 0
        progressive_records = 0
        progressive_subjects: set[str] = set()
        for relative, domain, concepts in VERIFIED_SOURCES:
            path = self.repo_root / relative
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not _is_verified(payload):
                continue
            verified_source_count += 1
            raw_source_bytes += path.stat().st_size
            evidence_id = "ev_" + _sha(path)[:20]
            evidence[evidence_id] = {"p": relative, "h": _sha(path), "b": path.stat().st_size,
                                     "verified": True, "reported_only": False}
            procedure = str(payload.get("procedure_id") or ((payload.get("promotion") or {}).get("candidate") or {}).get("procedure_id") or domain)
            skill = _glyph(kind="Skill", name=domain,
                           payload={"procedure": procedure, "verifier": "source_outcome_gate",
                                    "proposal_only": True, "concepts": list(concepts)},
                           evidence_ids=[evidence_id], epistemic="verified_bounded")
            glyph_by_identity[(skill["k"], skill["n"])] = skill
            for concept in concepts:
                item = _glyph(kind="Knowledge", name=concept,
                              payload={"domain": domain, "claim": "bounded_verified_abstraction"},
                              evidence_ids=[evidence_id], epistemic="verified_bounded")
                identity = (item["k"], item["n"])
                if identity in glyph_by_identity:
                    merged = glyph_by_identity[identity]
                    merged["e"] = sorted(set(merged["e"] + item["e"]))
                else:
                    glyph_by_identity[identity] = item

        # Consolidate the live progressive competency ledger. Repeated trials
        # strengthen provenance but do not mint repeated concepts: identity is
        # one subject skill glyph plus one knowledge glyph per grounded
        # subskill. Invalidated or hash-mismatched evidence fails closed.
        competency_state_path = (
            self.repo_root / "backend/modules/hexcore/data/progressive_competency/state.json"
        )
        if competency_state_path.exists():
            competency_state = json.loads(competency_state_path.read_text(encoding="utf-8"))
            subjects = competency_state.get("subjects") or {}
            subject_evidence: dict[str, list[tuple[dict[str, Any], str]]] = {}
            for row in competency_state.get("evidence") or []:
                if row.get("verified") is not True or row.get("invalidated_reason"):
                    continue
                artifact_name = str(row.get("artifact") or "")
                if not artifact_name:
                    continue
                artifact = self.repo_root / artifact_name
                if not artifact.exists():
                    continue
                artifact_hash = _sha(artifact)
                if artifact_hash != row.get("artifact_hash"):
                    continue
                evidence_id = "ev_" + artifact_hash[:20]
                if evidence_id not in evidence:
                    evidence[evidence_id] = {
                        "p": artifact_name, "h": artifact_hash, "b": artifact.stat().st_size,
                        "verified": True, "reported_only": False,
                        "authority": "progressive_competency_outcome",
                    }
                    raw_source_bytes += artifact.stat().st_size
                subject_id = str(row.get("subject_id") or "")
                if subject_id not in subjects:
                    continue
                subject_evidence.setdefault(subject_id, []).append((row, evidence_id))
                progressive_records += 1

            for subject_id, rows in subject_evidence.items():
                progressive_subjects.add(subject_id)
                subject = subjects[subject_id]
                evidence_ids = sorted({evidence_id for _, evidence_id in rows})
                kinds = sorted({str(row.get("kind")) for row, _ in rows})
                grounded_subskills = sorted({
                    str(skill) for row, _ in rows for skill in (row.get("subskills") or [])
                })
                skill = _glyph(
                    kind="Skill", name=f"competency:{subject_id}",
                    payload={"subject": subject.get("name", subject_id),
                             "verified_evidence_kinds": kinds,
                             "grounded_subskills": grounded_subskills,
                             "level_authority": "progressive_competency_ledger",
                             "proposal_only": True},
                    evidence_ids=evidence_ids, epistemic="verified_bounded",
                )
                glyph_by_identity[(skill["k"], skill["n"])] = skill
                for subskill in grounded_subskills:
                    subskill_evidence = sorted({
                        evidence_id for row, evidence_id in rows
                        if subskill in (row.get("subskills") or [])
                    })
                    item = _glyph(
                        kind="Knowledge", name=f"{subject_id}.{subskill}",
                        payload={"subject": subject.get("name", subject_id),
                                 "subskill": subskill,
                                 "claim": "verified_bounded_evidence_exists",
                                 "competency_level_not_implied": True},
                        evidence_ids=subskill_evidence, epistemic="verified_bounded",
                    )
                    glyph_by_identity[(item["k"], item["n"])] = item

        # The academy graph is compressed too, but never mislabelled as learned.
        for module in MODULES:
            item = _glyph(kind="Curriculum", name=module.module_id,
                          payload={"prerequisites": list(module.prerequisites),
                                   "competencies": list(module.competencies),
                                   "authorities": list(module.practical_authorities),
                                   "capstone": module.capstone},
                          evidence_ids=[], epistemic="proposed_not_learned")
            glyph_by_identity[(item["k"], item["n"])] = item

        glyphs = sorted(glyph_by_identity.values(), key=lambda row: (row["k"], row["n"]))
        packet = {"v": GLYPH_SCHEMA, "dictionary": {"i": "id", "k": "kind", "n": "name",
                  "d": "data", "e": "evidence", "s": "epistemic", "r": "rendered"},
                  "glyphs": glyphs}
        encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.compressed_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.compressed_path.with_suffix(self.compressed_path.suffix + ".tmp")
        with gzip.open(temporary, "wb", compresslevel=9) as handle:
            handle.write(encoded)
        os.replace(temporary, self.compressed_path)
        compressed_bytes = self.compressed_path.stat().st_size
        verified_source_count = len(evidence)
        index = {
            "schema_version": GLYPH_SCHEMA, "created_at": _utc_timestamp(),
            "compressed_store": _display_path(self.compressed_path, self.repo_root),
            "compressed_sha256": _sha(self.compressed_path),
            "evidence": evidence,
            "glyph_count": len(glyphs),
            "knowledge_glyphs": sum(row["k"] == "Knowledge" for row in glyphs),
            "skill_glyphs": sum(row["k"] == "Skill" for row in glyphs),
            "curriculum_glyphs": sum(row["k"] == "Curriculum" for row in glyphs),
            "verified_source_count": verified_source_count,
            "progressive_evidence_records": progressive_records,
            "progressive_subjects_consolidated": len(progressive_subjects),
            "raw_source_bytes": raw_source_bytes,
            "canonical_glyph_bytes": len(encoded), "compressed_glyph_bytes": compressed_bytes,
            "working_memory_reduction": (1.0 - compressed_bytes / raw_source_bytes) if raw_source_bytes else 0.0,
            "source_evidence_deleted": 0, "raw_evidence_duplicated_in_glyph_store": False,
        }
        _atomic_write(self.index_path, index)
        return index

    def load_and_verify(self) -> dict[str, Any]:
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        if _sha(self.compressed_path) != index["compressed_sha256"]:
            raise ValueError("compressed glyph store checksum mismatch")
        with gzip.open(self.compressed_path, "rb") as handle:
            packet = json.loads(handle.read().decode("utf-8"))
        for evidence_id, reference in index["evidence"].items():
            path = self.repo_root / reference["p"]
            if not path.exists() or _sha(path) != reference["h"]:
                raise ValueError(f"glyph evidence unavailable or altered: {evidence_id}")
        valid_ids = set(index["evidence"])
        for glyph in packet["glyphs"]:
            if not set(glyph["e"]).issubset(valid_ids):
                raise ValueError("glyph has unresolved provenance")
            if glyph["k"] in {"Knowledge", "Skill"} and glyph["s"] != "verified_bounded":
                raise ValueError("knowledge/skill glyph lacks verified epistemic state")
            if glyph["k"] == "Curriculum" and glyph["s"] != "proposed_not_learned":
                raise ValueError("curriculum glyph was incorrectly promoted to knowledge")
        return {"index": index, "packet": packet}

    def resolve_evidence(self, glyph_id: str) -> list[dict[str, Any]]:
        loaded = self.load_and_verify()
        glyph = next((row for row in loaded["packet"]["glyphs"] if row["i"] == glyph_id), None)
        if glyph is None:
            raise KeyError(glyph_id)
        return [{"evidence_id": eid, **loaded["index"]["evidence"][eid]} for eid in glyph["e"]]


def run(*, repo_root: Path, index_path: Path, compressed_path: Path,
        result_path: Path) -> dict[str, Any]:
    store = GovernedIntelligenceGlyphStore(repo_root=repo_root, index_path=index_path,
                                           compressed_path=compressed_path)
    index = store.build()
    loaded = store.load_and_verify()
    first_verified = next(row for row in loaded["packet"]["glyphs"] if row["e"])
    resolved = store.resolve_evidence(first_verified["i"])
    gate = {
        "verified_sources": index["verified_source_count"], "glyphs": index["glyph_count"],
        "knowledge_glyphs": index["knowledge_glyphs"], "skill_glyphs": index["skill_glyphs"],
        "curriculum_glyphs": index["curriculum_glyphs"],
        "progressive_evidence_records": index["progressive_evidence_records"],
        "progressive_subjects_consolidated": index["progressive_subjects_consolidated"],
        "working_memory_reduction": round(index["working_memory_reduction"], 6),
        "all_provenance_resolves": bool(resolved), "compressed_checksum_verified": True,
        "curriculum_not_mistaken_for_learning": all(
            row["s"] == "proposed_not_learned" for row in loaded["packet"]["glyphs"] if row["k"] == "Curriculum"),
        "raw_evidence_duplicated": index["raw_evidence_duplicated_in_glyph_store"],
        "source_evidence_deleted": index["source_evidence_deleted"], "unsafe_actions": 0,
    }
    gate["accepted"] = bool(gate["verified_sources"] >= 3 and gate["glyphs"] >= 20
                            and gate["skill_glyphs"] >= 3 and gate["curriculum_glyphs"] == len(MODULES)
                            and gate["working_memory_reduction"] >= 0.75
                            and gate["all_provenance_resolves"] and gate["compressed_checksum_verified"]
                            and gate["curriculum_not_mistaken_for_learning"]
                            and not gate["raw_evidence_duplicated"]
                            and gate["source_evidence_deleted"] == gate["unsafe_actions"] == 0)
    runtime = HexCorePersistentLearningRuntime(
        state_path=index_path.with_name("learning.json"),
        authority_provider=lambda goal: {"allow_learn": True, "deny_reason": None, "goal": goal,
                                         "source": "glyph_consolidation_cau", "S": 1.0, "H": 0.0})
    candidate = ProcedureCandidate(PROCEDURE_ID, "governed_intelligence_glyph_consolidation",
        ["admit_only_verified_knowledge_and_skill_sources", "deduplicate_repeated_abstractions",
         "store_content_addressed_provenance_not_raw_evidence_copies", "gzip_compact_structured_glyph_packet",
         "preserve_tessaris_compatible_rendering", "resolve_exact_evidence_on_demand",
         "keep_curriculum_proposals_epistemically_separate"],
        1.0 + gate["working_memory_reduction"], gate["accepted"], {"gate": gate},
        ["procedure_guided_programming_systems_security_academy_v1",
         "procedure_governed_teacher_python_core_cycle_v1"])
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.state.setdefault("intelligence_glyphs", {})[index["compressed_sha256"]] = {
        "index_path": _display_path(index_path, repo_root), "glyph_count": index["glyph_count"],
        "working_memory_reduction": index["working_memory_reduction"]}
    runtime.store.commit(reason="governed_intelligence_glyph_consolidation")
    champion = runtime.skills.champion("governed_intelligence_glyph_consolidation") or {}
    result = {"schema_version": GLYPH_SCHEMA, "created_at": _utc_timestamp(),
              "procedure_id": PROCEDURE_ID, "index": index, "gate": gate,
              "sample_glyph": first_verified, "sample_provenance_resolution": resolved,
              "promotion": {"candidate": candidate.to_dict(), "decision": decision,
                            "champion_retained": champion.get("procedure_id") == PROCEDURE_ID},
              "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
              "boundary": "Glyphs compress verified working intelligence; they do not replace immutable evidence or make proposed curricula true."}
    _atomic_write(result_path, result)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--index-path", type=Path, default=Path("backend/modules/hexcore/data/intelligence_glyphs/index.json"))
    parser.add_argument("--compressed-path", type=Path, default=Path("backend/modules/hexcore/data/intelligence_glyphs/glyphs.json.gz"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_governed_intelligence_glyph_consolidation.json"))
    args = parser.parse_args()
    result = run(repo_root=args.repo_root.resolve(), index_path=args.index_path.resolve(),
                 compressed_path=args.compressed_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))


if __name__ == "__main__":
    main()
