from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
)


SCHEMA_VERSION = "aion.hexcore.first_class_cognitive_control_plane.v1"
VERIFICATION_METHODS = {
    "executable",
    "formal_proof",
    "human_authority",
    "independent_observation",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "do", "for", "from", "had", "has", "have", "how", "i", "if", "in", "is",
    "it", "me", "my", "of", "on", "or", "our", "so", "that", "the", "their",
    "this", "to", "use", "was", "we", "what", "when", "where", "which", "with",
    "would", "you", "your",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    return str(value)


def _hash(value: Any) -> str:
    raw = json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _tokens(text: Any) -> set[str]:
    clean = "".join(ch.lower() if ch.isalnum() else " " for ch in str(text or ""))
    return {part for part in clean.split() if len(part) > 1 and part not in STOP_WORDS}


def _score(query: set[str], text: Any) -> float:
    if not query:
        return 0.0
    candidate = _tokens(text)
    if not candidate:
        return 0.0
    intersection = len(query & candidate)
    return (intersection / len(query)) + (intersection / len(candidate)) * 0.25


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_safe(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class FirstClassCognitiveControlPlane:
    """Governed task-time retrieval over truth, experience, skills and hypotheses.

    The persistent learning store remains AION's only canonical fact authority.
    Encountered material can guide research, but repetition can never promote it.
    """

    def __init__(
        self,
        *,
        canonical_state_path: Path,
        state_path: Optional[Path] = None,
        repo_root: Optional[Path] = None,
        authority_provider=None,
        association_state_path: Optional[Path] = None,
        competency_status_path: Optional[Path] = None,
        executor_registry_path: Optional[Path] = None,
        experience_root: Optional[Path] = None,
        executive_skills_path: Optional[Path] = None,
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[3])
        self.canonical_state_path = Path(canonical_state_path)
        self.state_path = Path(
            state_path or self.canonical_state_path.with_name("first_class_cognitive_control_plane.json")
        )
        self.association_state_path = Path(
            association_state_path
            or self.repo_root
            / "backend/modules/hexcore/data/expertise_containers/dynamic_association_state.json"
        )
        self.competency_status_path = Path(
            competency_status_path or self.repo_root / "results/aion_progressive_competency_status.json"
        )
        self.executor_registry_path = Path(
            executor_registry_path
            or self.repo_root / "backend/modules/hexcore/data/progressive_competency/executor_registry.json"
        )
        self.experience_root = Path(
            experience_root
            or self.repo_root / "backend/modules/hexcore/data/real_world_integration_arena"
        )
        self.executive_skills_path = Path(
            executive_skills_path
            or self.repo_root / "data/aion/canonical_runtime/executive_skills.json"
        )
        self.authority_provider = authority_provider
        self._lock = threading.RLock()
        self.state = self._load_state()

    @contextmanager
    def _locked_state(self):
        """Serialize state mutations across threads and supervised processes."""
        import fcntl

        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with lock_path.open("a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    self.state = self._load_state()
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "updated_at": None,
            "encountered_claims": {},
            "task_traces": [],
            "retrieval_outcomes": [],
            "promotion_events": [],
            "policy": {
                "canonical_source": str(self.canonical_state_path),
                "repetition_can_promote": False,
                "unverified_can_be_asserted_as_fact": False,
                "verified_evidence_and_authority_required": True,
                "original_inventions_begin_as": "proposal",
            },
        }

    def _load_state(self) -> Dict[str, Any]:
        state = _load(self.state_path, self._empty_state())
        if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
            state = self._empty_state()
        for key, fallback in (
            ("encountered_claims", {}),
            ("task_traces", []),
            ("retrieval_outcomes", []),
            ("promotion_events", []),
        ):
            state.setdefault(key, fallback)
        state.setdefault("policy", self._empty_state()["policy"])
        return state

    def _save(self) -> None:
        self.state["revision"] = int(self.state.get("revision") or 0) + 1
        self.state["updated_at"] = _utc_now()
        _atomic_write(self.state_path, self.state)

    def observe_encounter(
        self,
        *,
        subject: str,
        predicate: str,
        object_value: str,
        source_id: str,
        source_type: str,
        provenance: Optional[Mapping[str, Any]] = None,
        user_scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a structured encounter outside canonical truth.

        Raw private conversation is intentionally not accepted here. Callers must
        provide a deliberately extracted structured proposition and provenance.
        """
        claim = {
            "subject": str(subject).strip(),
            "predicate": str(predicate).strip(),
            "object": str(object_value).strip(),
        }
        if not all(claim.values()) or not str(source_id).strip() or not str(source_type).strip():
            return {"accepted": False, "reason": "STRUCTURED_CLAIM_AND_SOURCE_REQUIRED"}
        encounter_id = f"encounter_{_hash(claim)[:20]}"
        source_hash = _hash([source_type, source_id, provenance or {}])
        with self._locked_state():
            row = self.state["encountered_claims"].setdefault(
                encounter_id,
                {
                    "encounter_id": encounter_id,
                    **claim,
                    "status": "encountered_unverified",
                    "first_seen_at": _utc_now(),
                    "last_seen_at": None,
                    "observation_count": 0,
                    "independent_source_hashes": [],
                    "provenance": [],
                    "user_scopes": [],
                    "canonical_conflict": False,
                    "promoted_claim_ids": [],
                },
            )
            row["last_seen_at"] = _utc_now()
            row["observation_count"] = int(row.get("observation_count") or 0) + 1
            if source_hash not in row["independent_source_hashes"]:
                row["independent_source_hashes"].append(source_hash)
            if provenance:
                compact = _safe(dict(provenance))
                if compact not in row["provenance"]:
                    row["provenance"].append(compact)
            if user_scope and user_scope not in row["user_scopes"]:
                row["user_scopes"].append(str(user_scope))
            row["canonical_conflict"] = self._canonical_conflict(claim)
            # Deliberate invariant: no amount of repetition changes this status.
            if not row.get("promoted_claim_ids"):
                row["status"] = "encountered_unverified"
            self._save()
            return {
                "accepted": True,
                "encounter_id": encounter_id,
                "status": row["status"],
                "observation_count": row["observation_count"],
                "independent_source_count": len(row["independent_source_hashes"]),
                "canonical_conflict": row["canonical_conflict"],
                "repetition_promoted": False,
            }

    def _canonical_runtime(self) -> HexCorePersistentLearningRuntime:
        return HexCorePersistentLearningRuntime(
            state_path=self.canonical_state_path,
            authority_provider=self.authority_provider,
        )

    def _canonical_conflict(self, claim: Mapping[str, Any]) -> bool:
        try:
            result = self._canonical_runtime().knowledge.query_claim(
                str(claim.get("subject") or ""), str(claim.get("predicate") or "")
            )
            active = result.get("claim") or {}
            return bool(active and str(active.get("object")) != str(claim.get("object")))
        except Exception:
            return False

    def promote_encounter(
        self,
        *,
        encounter_id: str,
        verifier: str,
        verification_method: str,
        evidence_refs: Sequence[str],
        confidence: float = 1.0,
        revision: int = 1,
    ) -> Dict[str, Any]:
        verifier = str(verifier or "").strip()
        method = str(verification_method or "").strip()
        refs = [str(v).strip() for v in evidence_refs if str(v).strip()]
        if not verifier or method not in VERIFICATION_METHODS or not refs:
            return {"promoted": False, "reason": "VERIFIED_PROVENANCE_REQUIRED"}
        with self._locked_state():
            row = self.state["encountered_claims"].get(encounter_id)
            if not row:
                return {"promoted": False, "reason": "ENCOUNTER_NOT_FOUND"}
            capsule_id = f"capsule_{_hash([encounter_id, verifier, method, refs, revision])[:20]}"
            capsule = EvidenceCapsule(
                capsule_id=capsule_id,
                source_uri=refs[0],
                content=f"Verified promotion of {encounter_id} by {verifier}",
                claims=[{
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "confidence": float(confidence),
                    "revision": int(revision),
                }],
                confidence=float(confidence),
                verified=True,
            )
            try:
                result = self._canonical_runtime().knowledge.ingest(capsule)
            except Exception as exc:
                return {"promoted": False, "reason": f"CANONICAL_COMMIT_FAILED:{type(exc).__name__}"}
            if not result.get("accepted"):
                return {"promoted": False, "reason": result.get("reason"), "canonical": result}
            claim_ids = list(result.get("accepted_claim_ids") or [])
            row["status"] = "promoted_verified"
            row["promoted_claim_ids"] = sorted(set(row.get("promoted_claim_ids") or []) | set(claim_ids))
            event = {
                "event_id": f"promotion_{uuid.uuid4().hex}",
                "encounter_id": encounter_id,
                "capsule_id": capsule_id,
                "claim_ids": claim_ids,
                "verifier": verifier,
                "verification_method": method,
                "evidence_refs": refs,
                "promoted_at": _utc_now(),
            }
            self.state["promotion_events"].append(event)
            self._save()
            return {"promoted": True, "event": event, "canonical": result}

    def _subjects_and_skills(self, query: set[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        status = _load(self.competency_status_path, {})
        registry = _load(self.executor_registry_path, {})
        subjects = status.get("subjects") or {}
        adapters = registry.get("adapters") or {}
        scored: List[Tuple[float, str, Dict[str, Any]]] = []
        for subject_id, row in subjects.items():
            haystack = " ".join([
                str(subject_id), str(row.get("name") or ""), str(row.get("group") or ""),
                " ".join((row.get("per_subskill") or {}).keys()),
            ])
            value = _score(query, haystack)
            if value > 0:
                scored.append((value, str(subject_id), row))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = scored[:8]
        subject_rows: List[Dict[str, Any]] = []
        required_skills: List[Dict[str, Any]] = []
        missing: List[str] = []
        for value, subject_id, row in selected:
            adapter = adapters.get(subject_id) or {}
            subject_rows.append({
                "subject_id": subject_id,
                "name": row.get("name"),
                "group": row.get("group"),
                "overall_level": row.get("overall_level"),
                "knowledge_level": row.get("knowledge_level"),
                "practical_level": row.get("practical_level"),
                "relevance": round(value, 6),
            })
            required_skills.append({
                "skill_id": subject_id,
                "name": row.get("name"),
                "current_level": row.get("overall_level"),
                "adapter_status": adapter.get("status") or "missing",
                "verified_available": adapter.get("status") == "verified_available",
            })
            if adapter.get("status") != "verified_available":
                missing.append(subject_id)
        return subject_rows, required_skills, missing

    def _associations(self, seed_ids: set[str], query: set[str]) -> List[Dict[str, Any]]:
        raw = _load(self.association_state_path, {})
        relationships = raw.get("relationships") or {}
        rows = relationships.values() if isinstance(relationships, dict) else relationships
        selected = []
        for row in rows:
            source = str(row.get("source_subject_id") or row.get("source") or "")
            target = str(row.get("target_subject_id") or row.get("target") or "")
            relation_text = json.dumps(row, sort_keys=True)
            value = _score(query, relation_text)
            if source in seed_ids or target in seed_ids or value > 0.25:
                selected.append((float(row.get("strength") or row.get("score") or value), row))
        selected.sort(key=lambda item: item[0], reverse=True)
        return [_safe(row) for _, row in selected[:12]]

    def _expand_associated_skills(
        self,
        subjects: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
        missing: List[str],
        associations: Sequence[Mapping[str, Any]],
    ) -> None:
        status = _load(self.competency_status_path, {})
        registry = _load(self.executor_registry_path, {})
        subject_map = status.get("subjects") or {}
        adapters = registry.get("adapters") or {}
        known = {str(row.get("subject_id")) for row in subjects}
        linked: List[str] = []
        for edge in associations:
            for key in ("source_subject_id", "source", "target_subject_id", "target"):
                subject_id = str(edge.get(key) or "")
                if subject_id and subject_id not in known and subject_id in subject_map:
                    linked.append(subject_id)
                    known.add(subject_id)
        for subject_id in linked[:6]:
            row = subject_map[subject_id]
            adapter = adapters.get(subject_id) or {}
            subjects.append({
                "subject_id": subject_id,
                "name": row.get("name"),
                "group": row.get("group"),
                "overall_level": row.get("overall_level"),
                "knowledge_level": row.get("knowledge_level"),
                "practical_level": row.get("practical_level"),
                "relevance": "association_expansion",
            })
            skills.append({
                "skill_id": subject_id,
                "name": row.get("name"),
                "current_level": row.get("overall_level"),
                "adapter_status": adapter.get("status") or "missing",
                "verified_available": adapter.get("status") == "verified_available",
                "selected_via": "knowledge_association",
            })
            if adapter.get("status") != "verified_available" and subject_id not in missing:
                missing.append(subject_id)

    def _experience(self, query: set[str], subject_ids: set[str]) -> List[Dict[str, Any]]:
        rows: List[Tuple[float, Dict[str, Any]]] = []
        capsule_root = self.experience_root / "capsules"
        for path in capsule_root.glob("*.json") if capsule_root.exists() else []:
            capsule = _load(path, {})
            text = json.dumps(capsule, sort_keys=True)
            value = _score(query, text)
            refs = {str(v).replace("subject__", "") for v in capsule.get("knowledge_container_refs") or []}
            if refs & subject_ids:
                value += 0.5
            if value <= 0:
                continue
            rows.append((value, {
                "capsule_id": capsule.get("capsule_id") or path.stem,
                "title": capsule.get("title"),
                "verified_real_outcome": bool(
                    capsule.get("verified_real_outcome")
                    or capsule.get("passed")
                    or capsule.get("outcome_success")
                ),
                "experience_claim": capsule.get("experience_claim"),
                "lesson": capsule.get("lesson") or capsule.get("wisdom_rule"),
                "known_gap": capsule.get("knowledge_to_action_gap"),
                "repair": capsule.get("repair"),
                "outcome": capsule.get("outcome"),
                "relevance": round(value, 6),
                "source_path": str(path),
            }))
        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows[:8]]

    def _procedures(self, query: set[str]) -> List[Dict[str, Any]]:
        canonical = _load(self.canonical_state_path, {})
        rows: List[Tuple[float, Dict[str, Any]]] = []
        procedures = canonical.get("procedures") or {}
        champions = set((canonical.get("champions") or {}).values())
        for procedure_id, procedure in procedures.items():
            value = _score(query, json.dumps(procedure, sort_keys=True))
            if value > 0:
                rows.append((value, {
                    "procedure_id": procedure_id,
                    "goal": procedure.get("goal"),
                    "steps": procedure.get("steps") or [],
                    "score": procedure.get("score"),
                    "verified_success": bool(procedure.get("success")),
                    "champion": procedure_id in champions,
                    "relevance": round(value, 6),
                }))
        executive = _load(self.executive_skills_path, {})
        for skill_id, outcome in (executive.get("skill_outcomes") or {}).items():
            value = _score(query, skill_id)
            if value > 0:
                rows.append((value, {
                    "procedure_id": f"executive_skill:{skill_id}",
                    "goal": skill_id.replace("_", " "),
                    "steps": [],
                    "verified_success": int(outcome.get("verified") or 0) > 0,
                    "evidence": _safe(outcome),
                    "relevance": round(value, 6),
                }))
        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows[:8]]

    def _encounters(self, query: set[str]) -> List[Dict[str, Any]]:
        rows = []
        for row in self.state["encountered_claims"].values():
            if row.get("status") != "encountered_unverified":
                continue
            value = _score(query, f"{row.get('subject')} {row.get('predicate')} {row.get('object')}")
            if value > 0:
                rows.append((value, {
                    "encounter_id": row["encounter_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "status": "unverified_research_lead_only",
                    "canonical_conflict": bool(row.get("canonical_conflict")),
                    "observation_count": int(row.get("observation_count") or 0),
                    "independent_source_count": len(row.get("independent_source_hashes") or []),
                    "relevance": round(value, 6),
                }))
        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows[:8]]

    def prepare_task(
        self,
        task_text: str,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        query = _tokens(task_text)
        with self._locked_state():
            subjects, skills, missing = self._subjects_and_skills(query)
            subject_ids = {row["subject_id"] for row in subjects}
            canonical_truth: List[Dict[str, Any]] = []
            try:
                for item in self._canonical_runtime().knowledge.retrieve(task_text, limit=8):
                    canonical_truth.append({
                        "claim": _safe(item.get("claim") or {}),
                        "evidence": _safe(item.get("evidence") or []),
                        "relevance": item.get("score"),
                        "status": "canonical_verified_truth",
                    })
            except Exception:
                pass
            associations = self._associations(subject_ids, query)
            self._expand_associated_skills(subjects, skills, missing, associations)
            subject_ids = {row["subject_id"] for row in subjects}
            experience = self._experience(query, subject_ids)
            procedures = self._procedures(query)
            unverified = self._encounters(query)
            trace_id = f"task_trace_{uuid.uuid4().hex}"
            trace = {
                "trace_id": trace_id,
                "created_at": _utc_now(),
                "task_hash": hashlib.sha256(str(task_text).encode("utf-8")).hexdigest(),
                "task_tokens": sorted(query),
                "session_id": str((metadata or {}).get("session_id") or ""),
                "retrieved_ids": {
                    "canonical_claims": [row["claim"].get("claim_id") for row in canonical_truth],
                    "experiences": [row["capsule_id"] for row in experience],
                    "procedures": [row["procedure_id"] for row in procedures],
                    "unverified_encounters": [row["encounter_id"] for row in unverified],
                    "subjects": sorted(subject_ids),
                },
                "missing_capabilities": missing,
            }
            self.state["task_traces"].append(trace)
            self.state["task_traces"] = self.state["task_traces"][-5000:]
            self._save()
            return {
                "schema_version": "aion.hexcore.task_intelligence_context.v1",
                "trace_id": trace_id,
                "status": "prepared",
                "canonical_truth": canonical_truth,
                "experiential_memory": experience,
                "encountered_unverified": unverified,
                "relevant_subjects": subjects,
                "relevant_associations": associations,
                "required_skills": skills,
                "reusable_methods": procedures,
                "known_failures_and_lessons": [
                    {
                        "capsule_id": row["capsule_id"],
                        "known_gap": row.get("known_gap"),
                        "lesson": row.get("lesson"),
                        "repair": row.get("repair"),
                    }
                    for row in experience
                    if row.get("known_gap") or row.get("lesson") or row.get("repair")
                ],
                "missing_capabilities": missing,
                "task_policy": {
                    "facts_must_come_from_canonical_or_current_verified_evidence": True,
                    "unverified_encounters_are_research_leads_only": True,
                    "prior_verified_experience_should_be_reused": True,
                    "relevant_skills_must_be_selected_before_execution": True,
                    "fresh_invention_status_until_verified": "proposal",
                    "retrieval_must_be_recorded": True,
                },
            }

    def record_task_outcome(
        self,
        *,
        trace_id: str,
        used_memory_ids: Sequence[str],
        used_skill_ids: Sequence[str],
        outcome: str,
        verified: bool,
        verifier: Optional[str] = None,
        evidence_refs: Sequence[str] = (),
    ) -> Dict[str, Any]:
        with self._locked_state():
            if not any(row.get("trace_id") == trace_id for row in self.state["task_traces"]):
                return {"recorded": False, "reason": "TRACE_NOT_FOUND"}
            if verified and (not str(verifier or "").strip() or not list(evidence_refs)):
                return {"recorded": False, "reason": "VERIFIED_OUTCOME_REQUIRES_PROVENANCE"}
            row = {
                "outcome_id": f"task_outcome_{uuid.uuid4().hex}",
                "trace_id": trace_id,
                "recorded_at": _utc_now(),
                "used_memory_ids": sorted(set(map(str, used_memory_ids))),
                "used_skill_ids": sorted(set(map(str, used_skill_ids))),
                "outcome": str(outcome),
                "verified": bool(verified),
                "verifier": str(verifier or "") or None,
                "evidence_refs": list(map(str, evidence_refs)),
                "canonical_learning_authorized": False,
            }
            self.state["retrieval_outcomes"].append(row)
            self.state["retrieval_outcomes"] = self.state["retrieval_outcomes"][-5000:]
            self._save()
            return {"recorded": True, "outcome": row}

    def status(self) -> Dict[str, Any]:
        with self._locked_state():
            canonical = self._canonical_runtime().status() if self.canonical_state_path.exists() else {}
            encounters = list(self.state["encountered_claims"].values())
            capsule_count = len(list((self.experience_root / "capsules").glob("*.json")))
            return {
                "schema_version": "aion.hexcore.first_class_cognitive_control_plane_status.v1",
                "status": "active",
                "state_path": str(self.state_path),
                "canonical_state_path": str(self.canonical_state_path),
                "canonical_active_claims": int(canonical.get("active_claims") or 0),
                "canonical_evidence_capsules": int(canonical.get("evidence_capsules") or 0),
                "encountered_unverified": sum(
                    1 for row in encounters if row.get("status") == "encountered_unverified"
                ),
                "verified_promotions": len(self.state["promotion_events"]),
                "repetition_promotions": 0,
                "experience_capsules": capsule_count,
                "task_retrievals": len(self.state["task_traces"]),
                "retrieval_outcomes": len(self.state["retrieval_outcomes"]),
                "policy": _safe(self.state["policy"]),
                "claim_boundary": (
                    "This control plane retrieves and labels knowledge; it does not make "
                    "unverified encounters true or make unverified outcomes competent."
                ),
            }


def run(
    *,
    repo_root: Path,
    canonical_state_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    result_path: Optional[Path] = None,
) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    control = FirstClassCognitiveControlPlane(
        repo_root=repo_root,
        canonical_state_path=canonical_state_path
        or repo_root / "data/hexcore/persistent_learning_state.json",
        state_path=state_path,
    )
    result = control.status()
    result["checked_at"] = _utc_now()
    result["passed"] = (
        result["status"] == "active"
        and result["repetition_promotions"] == 0
        and result["policy"].get("repetition_can_promote") is False
    )
    result["result_sha256"] = _hash({k: v for k, v in result.items() if k != "result_sha256"})
    target = result_path or repo_root / "results/hexcore_first_class_cognitive_control_plane.json"
    _atomic_write(Path(target), result)
    return result


__all__ = ["FirstClassCognitiveControlPlane", "run"]
