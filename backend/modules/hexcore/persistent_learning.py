from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


AuthorityProvider = Callable[[str], Mapping[str, Any]]
ProcedureRunner = Callable[[Sequence[str]], Mapping[str, Any]]


def _utc_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _tokens(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in str(text or ""))
    return {part for part in cleaned.split() if part}


@dataclass(frozen=True)
class EvidenceCapsule:
    capsule_id: str
    source_uri: str
    content: str
    claims: List[Dict[str, Any]]
    observed_at: str = field(default_factory=_utc_timestamp)
    confidence: float = 1.0
    verified: bool = True
    checksum: str = ""
    schema_version: str = "aion.hexcore.evidence_capsule.v1"

    def __post_init__(self) -> None:
        if not self.capsule_id.strip():
            raise ValueError("capsule_id is required")
        if not self.source_uri.strip():
            raise ValueError("source_uri is required")
        if not self.checksum:
            object.__setattr__(
                self,
                "checksum",
                _canonical_hash(
                    {
                        "source_uri": self.source_uri,
                        "content": self.content,
                        "claims": self.claims,
                    }
                ),
            )

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class TransitionObservation:
    observation_id: str
    world_id: str
    state: Dict[str, Any]
    action: str
    next_state: Dict[str, Any]
    evidence_id: str
    observed_at: str = field(default_factory=_utc_timestamp)
    schema_version: str = "aion.hexcore.transition_observation.v1"

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ProcedureCandidate:
    procedure_id: str
    goal: str
    steps: List[str]
    score: float
    success: bool
    evidence: Dict[str, Any]
    source_rules: List[str] = field(default_factory=list)
    schema_version: str = "aion.hexcore.procedure_candidate.v1"

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


class LearningAuthorityError(PermissionError):
    pass


class HexCorePersistentLearningStore:
    """Atomic persistent state shared by knowledge, world and skill learning."""

    SCHEMA_VERSION = "aion.hexcore.persistent_learning_store.v1"

    def __init__(
        self,
        *,
        path: Path,
        authority_provider: Optional[AuthorityProvider] = None,
    ) -> None:
        self.path = Path(path)
        self.authority_provider = authority_provider or self._default_authority
        self.state = self._load()

    @staticmethod
    def _default_authority(goal: str) -> Mapping[str, Any]:
        from backend.modules.aion_cognition.cau_authority import get_authority_state

        return get_authority_state(goal=goal)

    @classmethod
    def _empty_state(cls) -> Dict[str, Any]:
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "revision": 0,
            "updated_at": None,
            "evidence": {},
            "claims": {},
            "contradictions": [],
            "observations": [],
            "world_rules": {},
            "causal_beliefs": {},
            "causal_graphs": {},
            "latent_variables": {},
            "model_criticisms": [],
            "hypothesis_expansions": [],
            "discovery_sessions": [],
            "change_events": [],
            "procedures": {},
            "champions": {},
            "promotion_history": [],
            "outcomes": [],
            "failure_queues": {},
            "procedure_mutation_cycles": [],
            "invented_concepts": {},
            "skill_contracts": {},
            "invention_history": [],
            "theory_revisions": [],
            "experiment_policies": {},
            "structural_analogies": {},
            "cognitive_programs": {},
            "program_evolution": {},
            "executable_knowledge": {},
            "tool_skills": {},
            "tool_outcomes": [],
            "workspace_sessions": {},
            "workspace_outcomes": [],
            "neural_consolidation": {},
            "continual_improvement": {},
            "open_world_projects": {},
            "goal_graph_projects": {},
            "relation_models": {},
            "clarification_sessions": {},
            "information_policies": {},
            "open_document_projects": {},
            "document_comprehension_projects": {},
            "invented_document_schemas": {},
            "schema_learning_projects": {},
            "adaptive_schema_theories": {},
            "schema_revision_sessions": [],
            "compositional_theory_programs": {},
            "program_induction_sessions": [],
            "typed_dsl_programs": {},
            "verified_subprogram_library": {},
            "dsl_synthesis_sessions": [],
            "invented_primitives": {},
            "primitive_invention_sessions": [],
            "algebraic_law_models": {},
            "continuous_operator_models": {},
            "invented_photon_tools": {},
            "tool_invention_sessions": [],
            "long_horizon_projects": {},
            "project_revision_events": [],
            "autonomous_goal_decompositions": {},
            "multimodal_evidence_projects": {},
            "glyphchain_evidence_commitments": {},
            "continual_arena_generations": {},
            "continual_arena_outcomes": [],
            "foundation_substrate_evaluations": {},
            "provider_substrate_registry": {},
            "external_benchmark_evaluations": {},
            "open_document_knowledge": {},
            "autonomous_knowledge_projects": {},
            "general_invented_tools": {},
            "general_experiment_inventions": {},
            "multi_track_challengers": {},
            "self_improvement_generations": {},
            "neural_proposal_models": {},
            "blind_evaluation_protocols": {},
            "open_world_sources": {},
            "open_world_claims": {},
            "real_file_projects": {},
            "relational_world_models": {},
            "world_model_sessions": {},
            "open_multimodal_projects": {},
            "multimodal_schema_models": {},
            "multimodal_project_outcomes": [],
            "project_outcome_ledger": [],
            "project_failure_models": {},
            "project_learning_challengers": {},
            "project_learning_generations": {},
            "invented_project_repairs": {},
            "project_repair_invention_sessions": [],
            "project_repair_counterexamples": [],
            "compound_repair_contracts": {},
            "compound_repair_generations": {},
            "compound_repair_sessions": [],
            "learned_repair_contracts": {},
            "contract_discovery_sessions": [],
            "contract_counterfactual_experiments": [],
            "repair_interference_models": {},
            "repair_interference_experiments": [],
            "repair_interference_generations": {},
            "raw_event_streams": {},
            "invented_state_vocabularies": {},
            "invented_relation_vocabularies": {},
            "representation_models": {},
            "representation_learning_sessions": [],
            "real_outcome_authorities": {},
            "real_outcome_observations": [],
            "outcome_grounded_skills": {},
            "outcome_grounding_sessions": [],
            "capability_maps": {},
            "autonomous_curricula": {},
            "curriculum_generations": [],
            "natural_event_streams": {},
            "open_topology_models": {},
            "latent_event_modes": {},
            "topology_induction_sessions": [],
            "continuous_event_streams": {},
            "continuous_world_models": {},
            "model_criticism_records": [],
            "representation_revision_generations": [],
            "continual_world_arenas": {},
            "invented_continuous_operators": {},
            "operator_synthesis_sessions": [],
            "operator_counterexamples": [],
            "external_continuous_traces": {},
            "operator_transfer_evaluations": {},
            "compositional_operator_library": {},
            "multivariate_synthesis_sessions": [],
            "active_measurement_records": [],
            "external_multivariate_traces": {},
            "compositional_transfer_evaluations": {},
            "open_causal_theories": {},
            "causal_intervention_records": [],
            "continuous_theory_revisions": [],
            "scientific_curriculum_generations": [],
            "external_software_maintenance": {},
            "repository_experiment_sessions": [],
            "sandbox_patch_library": {},
            "causal_repair_isomorphisms": {},
            "evi_curriculum_decisions": [],
            "repository_project_checkpoints": {},
            "historical_repository_repair_sessions": [],
            "invented_repository_falsification_tests": {},
            "synthesized_historical_patches": {},
            "historical_repair_transfer_models": {},
            "open_outcome_project_sessions": {},
            "invented_failure_ontologies": {},
            "delayed_repository_outcomes": [],
            "project_scientist_curricula": [],
            "open_project_checkpoints": {},
            "natural_repair_substrate_evaluations": {},
            "cross_language_repair_sessions": [],
            "cross_language_patch_library": {},
            "source_disjoint_repair_sessions": [],
            "source_disjoint_patch_library": {},
            "source_disjoint_repair_curricula": [],
            "open_patch_generation_sessions": [],
            "open_patch_library": {},
            "long_document_semantic_memories": {},
            "concept_composition_models": {},
            "delayed_memory_evaluations": [],
            "open_relation_ontologies": {},
            "argument_memories": {},
            "cross_domain_semantic_memories": {},
            "semantic_transfer_evaluations": [],
            "repository_semantic_ontologies": {},
            "documentation_guided_repair_sessions": [],
            "semantic_memory_router_trials": [],
            "executable_falsification_programs": {},
            "verified_execution_adapters": {},
            "execution_adapter_learning_sessions": [],
            "verified_property_programs": {},
            "property_invention_sessions": [],
            "adversarial_patch_tournaments": [],
            "reproducibility_audits": [],
            "polyglot_execution_contracts": {},
            "language_acquisition_sessions": [],
            "constructed_language_skills": {},
            "technology_selection_policies": {},
            "technology_selection_sessions": [],
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._empty_state()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self._empty_state()
        if not isinstance(raw, dict) or raw.get("schema_version") != self.SCHEMA_VERSION:
            return self._empty_state()
        state = self._empty_state()
        state.update(raw)
        return state

    def _authority(self, goal: str) -> Dict[str, Any]:
        try:
            state = dict(self.authority_provider(goal) or {})
        except Exception as exc:
            raise LearningAuthorityError(f"CAU_UNAVAILABLE:{type(exc).__name__}") from exc
        if state.get("allow_learn") is not True:
            raise LearningAuthorityError(str(state.get("deny_reason") or "CAU_DENIED"))
        return _json_safe(state)

    def commit(self, *, reason: str, authority_goal: str = "maintain_coherence") -> Dict[str, Any]:
        authority = self._authority(authority_goal)
        self.state["revision"] = int(self.state.get("revision") or 0) + 1
        self.state["updated_at"] = _utc_timestamp()
        self.state["last_commit"] = {
            "reason": reason,
            "authority": authority,
            "state_hash": _canonical_hash(self.state),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=self.path.parent,
            suffix=".tmp",
            encoding="utf-8",
        )
        try:
            json.dump(_json_safe(self.state), tmp, indent=2, ensure_ascii=False, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            json.loads(Path(tmp.name).read_text(encoding="utf-8"))
            os.replace(tmp.name, self.path)
        except Exception:
            try:
                tmp.close()
            except Exception:
                pass
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise
        return dict(self.state["last_commit"])

    def snapshot(self) -> Dict[str, Any]:
        return json.loads(json.dumps(_json_safe(self.state)))

    def prepare_mutation(self, authority_goal: str = "maintain_coherence") -> Dict[str, Any]:
        self._authority(authority_goal)
        return self.snapshot()

    def rollback(self, snapshot: Mapping[str, Any]) -> None:
        self.state = json.loads(json.dumps(_json_safe(snapshot)))


class GovernedKnowledgeLearner:
    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    @staticmethod
    def _claim_key(subject: str, predicate: str) -> str:
        return f"{subject.strip().lower()}::{predicate.strip().lower()}"

    def ingest(self, capsule: EvidenceCapsule) -> Dict[str, Any]:
        if not capsule.verified:
            return {"accepted": False, "reason": "UNVERIFIED_CAPSULE", "capsule_id": capsule.capsule_id}

        before = self.store.prepare_mutation()
        evidence = self.store.state["evidence"]
        existing = evidence.get(capsule.capsule_id)
        if existing and existing.get("checksum") != capsule.checksum:
            return {"accepted": False, "reason": "CAPSULE_ID_CHECKSUM_CONFLICT", "capsule_id": capsule.capsule_id}
        evidence[capsule.capsule_id] = capsule.to_dict()

        accepted_claims: List[str] = []
        superseded_claims: List[str] = []
        contradictions: List[str] = []

        for raw in capsule.claims:
            subject = str(raw.get("subject") or "").strip()
            predicate = str(raw.get("predicate") or "").strip()
            obj = str(raw.get("object") or "").strip()
            if not subject or not predicate or not obj:
                continue
            revision = int(raw.get("revision") or 1)
            confidence = float(raw.get("confidence", capsule.confidence))
            key = self._claim_key(subject, predicate)
            claim_id = str(raw.get("claim_id") or f"claim_{_canonical_hash([key, obj, revision])[:16]}")
            record = {
                "schema_version": "aion.hexcore.knowledge_claim.v1",
                "claim_id": claim_id,
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "revision": revision,
                "confidence": confidence,
                "status": "active",
                "evidence_ids": [capsule.capsule_id],
                "source_uri": capsule.source_uri,
                "observed_at": capsule.observed_at,
            }

            prior = [
                claim
                for claim in self.store.state["claims"].values()
                if self._claim_key(claim["subject"], claim["predicate"]) == key
                and claim.get("status") == "active"
            ]
            for old in prior:
                if old["object"] == obj:
                    if capsule.capsule_id not in old["evidence_ids"]:
                        old["evidence_ids"].append(capsule.capsule_id)
                    old["confidence"] = max(float(old.get("confidence", 0.0)), confidence)
                    record = old
                    claim_id = old["claim_id"]
                    break
                contradiction_id = f"contradiction_{_canonical_hash([old['claim_id'], claim_id])[:16]}"
                contradiction = {
                    "schema_version": "aion.hexcore.knowledge_contradiction.v1",
                    "contradiction_id": contradiction_id,
                    "claim_ids": [old["claim_id"], claim_id],
                    "key": key,
                    "objects": [old["object"], obj],
                    "resolved": False,
                    "resolution": None,
                }
                if revision > int(old.get("revision") or 1):
                    old["status"] = "superseded"
                    old["superseded_by"] = claim_id
                    contradiction["resolved"] = True
                    contradiction["resolution"] = "higher_revision"
                    superseded_claims.append(old["claim_id"])
                elif revision < int(old.get("revision") or 1):
                    record["status"] = "superseded"
                    record["superseded_by"] = old["claim_id"]
                    contradiction["resolved"] = True
                    contradiction["resolution"] = "existing_higher_revision"
                else:
                    old["status"] = "contested"
                    record["status"] = "contested"
                if not any(c["contradiction_id"] == contradiction_id for c in self.store.state["contradictions"]):
                    self.store.state["contradictions"].append(contradiction)
                contradictions.append(contradiction_id)

            self.store.state["claims"][claim_id] = record
            accepted_claims.append(claim_id)

        try:
            commit = self.store.commit(reason=f"knowledge_ingest:{capsule.capsule_id}")
        except Exception:
            self.store.rollback(before)
            raise
        return {
            "accepted": True,
            "capsule_id": capsule.capsule_id,
            "accepted_claim_ids": accepted_claims,
            "superseded_claim_ids": superseded_claims,
            "contradiction_ids": contradictions,
            "commit": commit,
        }

    def query_claim(self, subject: str, predicate: str) -> Dict[str, Any]:
        key = self._claim_key(subject, predicate)
        rows = [
            dict(claim)
            for claim in self.store.state["claims"].values()
            if self._claim_key(claim["subject"], claim["predicate"]) == key
        ]
        active = [row for row in rows if row.get("status") == "active"]
        active.sort(key=lambda row: (int(row.get("revision") or 0), float(row.get("confidence") or 0.0)), reverse=True)
        return {
            "found": bool(active),
            "claim": active[0] if active else None,
            "alternatives": rows,
            "provenance_complete": bool(active and active[0].get("evidence_ids")),
        }

    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_tokens = _tokens(query)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for claim in self.store.state["claims"].values():
            if claim.get("status") != "active":
                continue
            text = f"{claim['subject']} {claim['predicate']} {claim['object']}"
            claim_tokens = _tokens(text)
            overlap = len(query_tokens & claim_tokens) / max(1, len(query_tokens))
            score = overlap * float(claim.get("confidence") or 0.0)
            if score > 0:
                scored.append(
                    (
                        score,
                        {
                            "claim": dict(claim),
                            "score": round(score, 6),
                            "evidence": [
                                self.store.state["evidence"].get(eid)
                                for eid in claim.get("evidence_ids") or []
                                if eid in self.store.state["evidence"]
                            ],
                        },
                    )
                )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]


class GovernedWorldLearner:
    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    def observe(self, observation: TransitionObservation) -> Dict[str, Any]:
        rows = self.store.state["observations"]
        if any(row.get("observation_id") == observation.observation_id for row in rows):
            return {"accepted": False, "reason": "DUPLICATE_OBSERVATION"}
        before = self.store.prepare_mutation()
        rows.append(observation.to_dict())
        try:
            commit = self.store.commit(reason=f"world_observation:{observation.observation_id}")
        except Exception:
            self.store.rollback(before)
            raise
        return {"accepted": True, "observation_id": observation.observation_id, "commit": commit}

    @staticmethod
    def _effect(before: Any, after: Any) -> Optional[Dict[str, Any]]:
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            return {"kind": "delta", "value": round(float(after) - float(before), 8)}
        if before != after:
            return {"kind": "set", "value": after}
        return None

    def infer_effect_rules(self, *, world_id: str, minimum_support: int = 2) -> List[Dict[str, Any]]:
        before = self.store.prepare_mutation()
        observations = [
            row for row in self.store.state["observations"] if row.get("world_id") == world_id
        ]
        grouped: Dict[Tuple[str, str], List[str]] = {}
        effect_values: Dict[str, Dict[str, Any]] = {}
        for row in observations:
            for key in sorted(set(row["state"]) | set(row["next_state"])):
                effect = self._effect(row["state"].get(key), row["next_state"].get(key))
                if effect is None:
                    continue
                signature = json.dumps(effect, sort_keys=True)
                grouped.setdefault((row["action"], key), []).append(signature)
                effect_values[signature] = effect

        learned: List[Dict[str, Any]] = []
        for (action, field_name), signatures in grouped.items():
            counts = {signature: signatures.count(signature) for signature in set(signatures)}
            winner, support = max(counts.items(), key=lambda item: item[1])
            total = len(signatures)
            contradictions = total - support
            confidence = support / max(total, 1)
            rule_id = f"rule_{_canonical_hash([world_id, action, field_name, winner])[:16]}"
            rule = {
                "schema_version": "aion.hexcore.world_rule.v1",
                "rule_id": rule_id,
                "world_id": world_id,
                "rule_type": "action_effect",
                "action": action,
                "field": field_name,
                "effect": effect_values[winner],
                "support_count": support,
                "contradiction_count": contradictions,
                "confidence": round(confidence, 6),
                "status": "active" if support >= minimum_support and confidence >= 0.75 else "hypothesis",
                "observation_ids": [
                    row["observation_id"]
                    for row in observations
                    if row["action"] == action
                ],
            }
            self.store.state["world_rules"][rule_id] = rule
            learned.append(rule)
        try:
            self.store.commit(reason=f"infer_effect_rules:{world_id}")
        except Exception:
            self.store.rollback(before)
            raise
        return learned

    def infer_threshold_rule(
        self,
        *,
        world_id: str,
        action: str,
        condition_field: str,
        outcome_field: str,
        success_value: Any,
    ) -> Optional[Dict[str, Any]]:
        rows = [
            row
            for row in self.store.state["observations"]
            if row.get("world_id") == world_id
            and row.get("action") == action
            and isinstance(row.get("state", {}).get(condition_field), (int, float))
            and outcome_field in row.get("next_state", {})
        ]
        positives = [
            float(row["state"][condition_field])
            for row in rows
            if row["next_state"].get(outcome_field) == success_value
        ]
        negatives = [
            float(row["state"][condition_field])
            for row in rows
            if row["next_state"].get(outcome_field) != success_value
        ]
        if len(positives) < 2 or not negatives:
            return None
        threshold = min(positives)
        if max(negatives) >= threshold:
            return None
        before = self.store.prepare_mutation()
        rule_id = f"rule_{_canonical_hash([world_id, action, condition_field, threshold])[:16]}"
        rule = {
            "schema_version": "aion.hexcore.world_rule.v1",
            "rule_id": rule_id,
            "world_id": world_id,
            "rule_type": "threshold",
            "action": action,
            "condition": {"field": condition_field, "operator": ">=", "value": threshold},
            "outcome": {"field": outcome_field, "value": success_value},
            "support_count": len(positives),
            "negative_support_count": len(negatives),
            "contradiction_count": 0,
            "confidence": 1.0,
            "status": "active",
            "observation_ids": [row["observation_id"] for row in rows],
        }
        self.store.state["world_rules"][rule_id] = rule
        try:
            self.store.commit(reason=f"infer_threshold_rule:{world_id}:{action}")
        except Exception:
            self.store.rollback(before)
            raise
        return rule

    def active_rules(self, world_id: str) -> List[Dict[str, Any]]:
        return [
            dict(rule)
            for rule in self.store.state["world_rules"].values()
            if rule.get("world_id") == world_id and rule.get("status") == "active"
        ]


class GovernedSkillLearner:
    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    def plan_threshold_goal(
        self,
        *,
        world_id: str,
        start_state: Mapping[str, Any],
        terminal_action: str,
    ) -> Optional[ProcedureCandidate]:
        rules = [
            rule
            for rule in self.store.state["world_rules"].values()
            if rule.get("world_id") == world_id and rule.get("status") == "active"
        ]
        threshold_rules = [
            rule
            for rule in rules
            if rule.get("rule_type") == "threshold" and rule.get("action") == terminal_action
        ]
        if not threshold_rules:
            return None
        threshold_rule = threshold_rules[0]
        condition = threshold_rule["condition"]
        field_name = condition["field"]
        target = float(condition["value"])
        current = float(start_state.get(field_name) or 0.0)
        effect_rules = [
            rule
            for rule in rules
            if rule.get("rule_type") == "action_effect"
            and rule.get("field") == field_name
            and rule.get("effect", {}).get("kind") == "delta"
            and float(rule.get("effect", {}).get("value") or 0.0) > 0
        ]
        if not effect_rules:
            return None
        best = max(effect_rules, key=lambda rule: float(rule["effect"]["value"]))
        delta = float(best["effect"]["value"])
        repetitions = max(0, int(math.ceil((target - current) / delta)))
        steps = [str(best["action"])] * repetitions + [terminal_action]
        return ProcedureCandidate(
            procedure_id=f"procedure_{_canonical_hash([world_id, steps])[:16]}",
            goal=f"{threshold_rule['outcome']['field']}={threshold_rule['outcome']['value']}",
            steps=steps,
            score=0.0,
            success=False,
            evidence={"planning_method": "learned_threshold_and_effect_rules"},
            source_rules=[threshold_rule["rule_id"], best["rule_id"]],
        )

    def evaluate(
        self,
        candidate: ProcedureCandidate,
        *,
        runner: ProcedureRunner,
    ) -> ProcedureCandidate:
        result = dict(runner(candidate.steps) or {})
        return ProcedureCandidate(
            procedure_id=candidate.procedure_id,
            goal=candidate.goal,
            steps=list(candidate.steps),
            score=float(result.get("score") or 0.0),
            success=bool(result.get("success")),
            evidence={
                **dict(candidate.evidence),
                "runner_result": _json_safe(result),
                "evaluated_at": _utc_timestamp(),
            },
            source_rules=list(candidate.source_rules),
        )

    def promote(self, candidate: ProcedureCandidate) -> Dict[str, Any]:
        if not candidate.success:
            return {"promoted": False, "reason": "CANDIDATE_FAILED"}
        existing_id = self.store.state["champions"].get(candidate.goal)
        existing = self.store.state["procedures"].get(existing_id) if existing_id else None
        if existing and float(existing.get("score") or 0.0) >= candidate.score:
            return {
                "promoted": False,
                "reason": "NO_CHAMPION_IMPROVEMENT",
                "champion_id": existing_id,
            }

        before = self.store.prepare_mutation()
        record = candidate.to_dict()
        record["status"] = "champion"
        record["promoted_at"] = _utc_timestamp()
        if existing:
            existing["status"] = "retired"
            existing["retired_by"] = candidate.procedure_id
        self.store.state["procedures"][candidate.procedure_id] = record
        self.store.state["champions"][candidate.goal] = candidate.procedure_id
        self.store.state["promotion_history"].append(
            {
                "schema_version": "aion.hexcore.procedure_promotion.v1",
                "goal": candidate.goal,
                "previous_champion_id": existing_id,
                "new_champion_id": candidate.procedure_id,
                "score": candidate.score,
                "evidence_hash": _canonical_hash(candidate.evidence),
                "timestamp": _utc_timestamp(),
            }
        )
        try:
            commit = self.store.commit(reason=f"procedure_promotion:{candidate.procedure_id}")
        except Exception:
            self.store.rollback(before)
            raise
        return {
            "promoted": True,
            "reason": "VERIFIED_CHALLENGER_IMPROVEMENT",
            "champion_id": candidate.procedure_id,
            "commit": commit,
        }

    def champion(self, goal: str) -> Optional[Dict[str, Any]]:
        procedure_id = self.store.state["champions"].get(goal)
        if not procedure_id:
            return None
        procedure = self.store.state["procedures"].get(procedure_id)
        return dict(procedure) if procedure else None

    def record_outcome(
        self,
        *,
        procedure_id: str,
        success: bool,
        score: float,
        evidence: Mapping[str, Any],
    ) -> Dict[str, Any]:
        before = self.store.prepare_mutation()
        outcome = {
            "schema_version": "aion.hexcore.procedure_outcome.v1",
            "outcome_id": f"outcome_{uuid.uuid4().hex[:16]}",
            "procedure_id": procedure_id,
            "success": bool(success),
            "score": float(score),
            "evidence": _json_safe(evidence),
            "timestamp": _utc_timestamp(),
        }
        self.store.state["outcomes"].append(outcome)
        try:
            self.store.commit(reason=f"procedure_outcome:{outcome['outcome_id']}")
        except Exception:
            self.store.rollback(before)
            raise
        return outcome


class HexCorePersistentLearningRuntime:
    """Facade exposing the three learning layers through one persistent state."""

    def __init__(
        self,
        *,
        state_path: Path,
        authority_provider: Optional[AuthorityProvider] = None,
    ) -> None:
        self.store = HexCorePersistentLearningStore(
            path=state_path,
            authority_provider=authority_provider,
        )
        self.knowledge = GovernedKnowledgeLearner(self.store)
        self.world = GovernedWorldLearner(self.store)
        self.skills = GovernedSkillLearner(self.store)

    def status(self) -> Dict[str, Any]:
        state = self.store.state
        active_claims = sum(1 for row in state["claims"].values() if row.get("status") == "active")
        active_rules = sum(1 for row in state["world_rules"].values() if row.get("status") == "active")
        return {
            "schema_version": "aion.hexcore.persistent_learning_status.v1",
            "state_path": str(self.store.path),
            "revision": int(state.get("revision") or 0),
            "evidence_capsules": len(state["evidence"]),
            "active_claims": active_claims,
            "contradictions": len(state["contradictions"]),
            "observations": len(state["observations"]),
            "active_world_rules": active_rules,
            "causal_beliefs": len(state["causal_beliefs"]),
            "causal_graphs": len(state["causal_graphs"]),
            "latent_variables": len(state["latent_variables"]),
            "model_criticisms": len(state["model_criticisms"]),
            "hypothesis_expansions": len(state["hypothesis_expansions"]),
            "discovery_sessions": len(state["discovery_sessions"]),
            "change_events": len(state["change_events"]),
            "procedures": len(state["procedures"]),
            "champions": len(state["champions"]),
            "outcomes": len(state["outcomes"]),
            "failure_queues": sum(
                len(rows) for rows in state["failure_queues"].values()
            ),
            "procedure_mutation_cycles": len(
                state["procedure_mutation_cycles"]
            ),
            "state_hash": _canonical_hash(state),
        }
