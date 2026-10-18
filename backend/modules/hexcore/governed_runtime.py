from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional


AuthorityProvider = Callable[[str], Mapping[str, Any]]
RecallProvider = Callable[[str], Mapping[str, Any]]
MemoryWriter = Callable[[str, str, Mapping[str, float], Mapping[str, Any]], bool]


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


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


@dataclass(frozen=True)
class GovernedTurnContext:
    schema_version: str = "aion.hexcore.governed_turn_context.v1"
    governance_id: str = ""
    turn_id: str = ""
    session_id: str = ""
    user_text: str = ""
    created_at: str = ""
    authority: Dict[str, Any] = field(default_factory=dict)
    recalled_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    pattern_results: List[Dict[str, Any]] = field(default_factory=list)
    tessaris_rules: List[Dict[str, Any]] = field(default_factory=list)
    goals: List[Dict[str, Any]] = field(default_factory=list)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_providers: List[str] = field(default_factory=list)
    cognitive_foundation: Dict[str, Any] = field(default_factory=dict)
    learning_layers: Dict[str, Any] = field(default_factory=dict)
    task_intelligence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))


class AppendOnlyOutcomeLedger:
    """Small append-only audit ledger for governed turns and learning decisions."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else _data_root() / "hexcore" / "governed_turns.jsonl"
        self._lock = threading.Lock()

    def append(self, record: Mapping[str, Any]) -> str:
        payload = _json_safe(dict(record))
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            previous_record_hash = None
            if self.path.exists():
                try:
                    lines = self.path.read_text(encoding="utf-8").splitlines()
                    if lines:
                        previous_record_hash = json.loads(lines[-1]).get("record_hash")
                except Exception:
                    previous_record_hash = None
            payload["previous_record_hash"] = previous_record_hash
            canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            envelope = {**payload, "record_hash": record_hash}
            line = json.dumps(envelope, ensure_ascii=False, sort_keys=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return record_hash


class HexCoreGovernedRuntime:
    """
    Canonical authority shell around AION cognition.

    Language/reasoning providers may propose responses. They cannot authorize
    long-term learning. Only an explicit verified outcome plus a positive CAU
    decision can mutate long-term memory.
    """

    def __init__(
        self,
        *,
        authority_provider: Optional[AuthorityProvider] = None,
        recall_provider: Optional[RecallProvider] = None,
        memory_writer: Optional[MemoryWriter] = None,
        outcome_ledger: Optional[AppendOnlyOutcomeLedger] = None,
        soul_laws_path: Optional[Path] = None,
        foundation_root: Optional[Path] = None,
        learning_state_path: Optional[Path] = None,
        cognitive_control_plane: Optional[Any] = None,
    ) -> None:
        self._authority_provider = authority_provider or self._default_authority_provider
        self._recall_provider = recall_provider or self._default_recall_provider
        self._memory_writer = memory_writer or self._default_memory_writer
        self.outcome_ledger = outcome_ledger or AppendOnlyOutcomeLedger()
        self.soul_laws_path = soul_laws_path or Path(__file__).with_name("soul_laws.yaml")
        self.foundation_root = foundation_root or Path(
            os.getenv("AION_TPU_ROOT", "/Users/kevinrobinson/Documents/Tessaris/TPU")
        )
        self.learning_state_path = learning_state_path or Path(
            os.getenv(
                "HEXCORE_LEARNING_STATE_PATH",
                str(_data_root() / "hexcore" / "persistent_learning_state.json"),
            )
        )
        self._cognitive_control_plane = cognitive_control_plane

    @staticmethod
    def _default_authority_provider(goal: str) -> Mapping[str, Any]:
        from backend.modules.aion_cognition.cau_authority import get_authority_state

        return get_authority_state(goal=goal)

    @staticmethod
    def _default_recall_provider(prompt: str) -> Mapping[str, Any]:
        from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory

        return recall_from_memory(prompt)

    @staticmethod
    def _default_memory_writer(
        prompt: str,
        answer: str,
        resonance: Mapping[str, float],
        metadata: Mapping[str, Any],
    ) -> bool:
        # CAU is intentionally enforced by this runtime before this method.
        # require_cau=False avoids the legacy LexMemory soft-fail compatibility path.
        from backend.modules.aion_cognition.cee_lex_memory import get_lex

        lex = get_lex()
        entry = lex.update(
            prompt=prompt,
            answer=answer,
            rho=float(resonance.get("rho", resonance.get("ρ", 0.8))),
            Ibar=float(resonance.get("Ibar", resonance.get("I", 0.8))),
            sqi=float(resonance.get("sqi", resonance.get("SQI", 0.8))),
            meta=dict(metadata),
            require_cau=False,
        )
        if entry is None:
            return False
        lex.save()
        return True

    def _authority_snapshot(self, goal: str) -> Dict[str, Any]:
        try:
            state = dict(self._authority_provider(goal) or {})
            if "allow_learn" not in state:
                raise ValueError("CAU response missing allow_learn")
            state["allow_learn"] = bool(state["allow_learn"])
            state.setdefault("deny_reason", None if state["allow_learn"] else "CAU_DENIED")
            state.setdefault("source", "cau_authority")
            return _json_safe(state)
        except Exception as exc:
            return {
                "allow_learn": False,
                "deny_reason": "CAU_UNAVAILABLE",
                "source": "hexcore_fail_closed",
                "error": type(exc).__name__,
                "goal": goal,
            }

    def _recall(self, prompt: str) -> List[Dict[str, Any]]:
        recalled: List[Dict[str, Any]] = []
        try:
            hit = dict(self._recall_provider(prompt) or {})
        except Exception:
            hit = {}
        if hit and str(hit.get("answer") or "").strip():
            confidence = float(hit.get("confidence") or 0.0)
            if confidence >= float(os.getenv("HEXCORE_RECALL_MIN_CONFIDENCE", "0.72")):
                recalled.append(
                    {
                        "source": "cee_lex_memory",
                        "prompt": str(hit.get("prompt") or prompt),
                        "answer": str(hit["answer"]),
                        "confidence": confidence,
                        "resonance": _json_safe(hit.get("resonance") or {}),
                    }
                )

        if self.learning_state_path.exists():
            try:
                from backend.modules.hexcore.persistent_learning import (
                    HexCorePersistentLearningRuntime,
                )

                learning = HexCorePersistentLearningRuntime(state_path=self.learning_state_path)
                for item in learning.knowledge.retrieve(prompt, limit=3):
                    claim = dict(item.get("claim") or {})
                    if not claim:
                        continue
                    recalled.append(
                        {
                            "source": "hexcore_persistent_knowledge",
                            "prompt": prompt,
                            "answer": (
                                f"{claim.get('subject')} "
                                f"{claim.get('predicate')} "
                                f"{claim.get('object')}"
                            ),
                            "confidence": float(claim.get("confidence") or 0.0),
                            "claim": claim,
                            "evidence": list(item.get("evidence") or []),
                            "retrieval_score": float(item.get("score") or 0.0),
                        }
                    )
            except Exception:
                pass
        return recalled

    def _foundation_descriptor(self) -> Dict[str, Any]:
        selection = self.foundation_root / "results" / "aion_foundation_v3" / "checkpoint_selection.json"
        descriptor: Dict[str, Any] = {
            "role": "replaceable_representation_provider",
            "root": str(self.foundation_root),
            "available": self.foundation_root.exists(),
            "loaded_for_turn": False,
        }
        try:
            if selection.exists():
                raw = json.loads(selection.read_text(encoding="utf-8"))
                descriptor["selection_manifest"] = str(selection)
                descriptor["selection"] = _json_safe(raw)
        except Exception as exc:
            descriptor["manifest_error"] = type(exc).__name__
        return descriptor

    def _persistent_learning_descriptor(self) -> Dict[str, Any]:
        path = self.learning_state_path
        descriptor: Dict[str, Any] = {
            "schema_version": "aion.hexcore.persistent_learning_descriptor.v1",
            "state_path": str(path),
            "available": path.exists(),
            "knowledge_learning": True,
            "world_learning": True,
            "skill_learning": True,
        }
        if not path.exists():
            descriptor["status"] = None
        else:
            try:
                from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime

                runtime = HexCorePersistentLearningRuntime(state_path=path)
                descriptor["status"] = runtime.status()
            except Exception as exc:
                descriptor["status_error"] = type(exc).__name__

        research_states = {}
        for name in ("multi_domain_learning_state.json", "active_causal_learning_state.json"):
            candidate = path.parent / name
            if not candidate.exists():
                continue
            try:
                from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime

                research_states[name] = HexCorePersistentLearningRuntime(
                    state_path=candidate
                ).status()
            except Exception as exc:
                research_states[name] = {"status_error": type(exc).__name__}
        descriptor["research_states"] = research_states
        return descriptor

    def _task_intelligence(
        self,
        task_text: str,
        *,
        session_id: str,
        request_metadata: Mapping[str, Any],
    ) -> Dict[str, Any]:
        try:
            if self._cognitive_control_plane is None:
                from backend.modules.hexcore.first_class_cognitive_control_plane import (
                    FirstClassCognitiveControlPlane,
                )

                self._cognitive_control_plane = FirstClassCognitiveControlPlane(
                    canonical_state_path=self.learning_state_path,
                    state_path=self.learning_state_path.with_name(
                        "first_class_cognitive_control_plane.json"
                    ),
                )
            return self._cognitive_control_plane.prepare_task(
                task_text,
                metadata={**dict(request_metadata), "session_id": session_id},
            )
        except Exception as exc:
            return {
                "schema_version": "aion.hexcore.task_intelligence_context.v1",
                "status": "unavailable_fail_closed",
                "error": type(exc).__name__,
                "canonical_truth": [],
                "experiential_memory": [],
                "encountered_unverified": [],
                "required_skills": [],
                "missing_capabilities": [],
                "task_policy": {
                    "facts_must_come_from_canonical_or_current_verified_evidence": True,
                    "unverified_encounters_are_research_leads_only": True,
                },
            }

    def begin_turn(
        self,
        *,
        turn_id: str,
        session_id: str,
        user_text: str,
        request_metadata: Optional[Mapping[str, Any]] = None,
    ) -> GovernedTurnContext:
        meta = dict(request_metadata or {})
        goal = str(meta.get("authority_goal") or "maintain_coherence")
        providers = meta.get("reasoning_providers") or ["aion_composer", "local_gemma", "openai", "gemini"]
        task_intelligence = self._task_intelligence(
            user_text,
            session_id=session_id,
            request_metadata=meta,
        )
        return GovernedTurnContext(
            governance_id=str(uuid.uuid4()),
            turn_id=turn_id,
            session_id=session_id,
            user_text=user_text,
            created_at=_utc_timestamp(),
            authority=self._authority_snapshot(goal),
            recalled_knowledge=self._recall(user_text),
            pattern_results=[
                dict(v) for v in (meta.get("pattern_results") or []) if isinstance(v, Mapping)
            ],
            tessaris_rules=[
                dict(v) for v in (meta.get("tessaris_rules") or []) if isinstance(v, Mapping)
            ],
            goals=[dict(v) for v in (meta.get("goals") or []) if isinstance(v, Mapping)],
            memories=[dict(v) for v in (meta.get("memories") or []) if isinstance(v, Mapping)],
            reasoning_providers=[str(v) for v in providers],
            cognitive_foundation=self._foundation_descriptor(),
            learning_layers=self._persistent_learning_descriptor(),
            task_intelligence=task_intelligence,
        )

    def status(self) -> Dict[str, Any]:
        control_plane_status: Dict[str, Any]
        try:
            if self._cognitive_control_plane is None:
                from backend.modules.hexcore.first_class_cognitive_control_plane import (
                    FirstClassCognitiveControlPlane,
                )

                self._cognitive_control_plane = FirstClassCognitiveControlPlane(
                    canonical_state_path=self.learning_state_path,
                    state_path=self.learning_state_path.with_name(
                        "first_class_cognitive_control_plane.json"
                    ),
                )
            control_plane_status = self._cognitive_control_plane.status()
        except Exception as exc:
            control_plane_status = {"status": "unavailable_fail_closed", "error": type(exc).__name__}
        return {
            "schema_version": "aion.hexcore.governed_runtime_status.v1",
            "authority": self._authority_snapshot("maintain_coherence"),
            "outcome_ledger": str(self.outcome_ledger.path),
            "cognitive_foundation": self._foundation_descriptor(),
            "learning_layers": self._persistent_learning_descriptor(),
            "first_class_cognitive_control_plane": control_plane_status,
            "learning_policy": {
                "provider_output_is_knowledge": False,
                "explicit_verified_outcome_required": True,
                "cau_permission_required": True,
                "authority_failure_mode": "deny_learning",
            },
            "action_policy": {
                "soul_laws_path": str(self.soul_laws_path),
                "authority_failure_mode": "deny_action",
            },
        }

    def evaluate_action(
        self,
        action: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        import yaml

        ctx = dict(context or {})
        lowered = f"{action}\n{json.dumps(_json_safe(ctx), sort_keys=True)}".lower()
        violations: List[Dict[str, Any]] = []
        try:
            laws = (yaml.safe_load(self.soul_laws_path.read_text(encoding="utf-8")) or {}).get(
                "soul_laws", []
            )
        except Exception as exc:
            return {
                "allowed": False,
                "decision": "deny",
                "reason": "SOUL_LAWS_UNAVAILABLE",
                "error": type(exc).__name__,
                "violations": [],
            }

        for law in laws:
            triggers = [str(v).lower() for v in (law.get("triggers") or [])]
            matched = [trigger for trigger in triggers if trigger and trigger in lowered]
            if matched:
                violations.append(
                    {
                        "id": law.get("id"),
                        "title": law.get("title"),
                        "severity": law.get("severity", "warn"),
                        "matched_triggers": matched,
                    }
                )

        if ctx.get("requires_consent") and not ctx.get("consent_granted"):
            violations.append(
                {
                    "id": "consent",
                    "title": "Consent required",
                    "severity": "block",
                    "matched_triggers": ["requires_consent"],
                }
            )

        blocked = any(str(v.get("severity")).lower() == "block" for v in violations)
        return {
            "allowed": not blocked,
            "decision": "deny" if blocked else "allow",
            "reason": "SOUL_LAW_VETO" if blocked else "SOUL_LAWS_CLEARED",
            "violations": violations,
        }

    @staticmethod
    def _verified_learning_candidate(
        *,
        user_text: str,
        response_text: str,
        apply_teaching: bool,
        request_metadata: Mapping[str, Any],
    ) -> Dict[str, Any]:
        outcome = request_metadata.get("learning_outcome")
        if not apply_teaching:
            return {"eligible": False, "reason": "TEACHING_NOT_REQUESTED"}
        if not isinstance(outcome, Mapping):
            return {"eligible": False, "reason": "NO_VERIFIED_OUTCOME"}
        verifier = str(outcome.get("verifier") or "").strip()
        answer = str(outcome.get("correction") or outcome.get("answer") or "").strip()
        evidence_refs = [str(v) for v in (outcome.get("evidence_refs") or []) if str(v).strip()]
        verified = outcome.get("verified") is True
        if not verified or not verifier or not answer:
            return {"eligible": False, "reason": "OUTCOME_NOT_VERIFIED"}
        if not evidence_refs and str(outcome.get("verification_method") or "") not in {
            "executable",
            "human_authority",
            "formal_proof",
        }:
            return {"eligible": False, "reason": "VERIFICATION_PROVENANCE_MISSING"}
        return {
            "eligible": True,
            "reason": "VERIFIED_OUTCOME",
            "prompt": str(outcome.get("prompt") or user_text),
            "answer": answer,
            "verifier": verifier,
            "evidence_refs": evidence_refs,
            "verification_method": str(outcome.get("verification_method") or "evidence"),
            "provider_response_hash": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def _candidate_audit_view(candidate: Mapping[str, Any]) -> Dict[str, Any]:
        audit = {
            str(k): _json_safe(v)
            for k, v in candidate.items()
            if k not in {"prompt", "answer"}
        }
        if candidate.get("prompt") is not None:
            audit["prompt_hash"] = hashlib.sha256(
                str(candidate.get("prompt") or "").encode("utf-8")
            ).hexdigest()
        if candidate.get("answer") is not None:
            audit["answer_hash"] = hashlib.sha256(
                str(candidate.get("answer") or "").encode("utf-8")
            ).hexdigest()
        return audit

    def complete_turn(
        self,
        *,
        context: GovernedTurnContext,
        response_text: str,
        confidence: float,
        mode: str,
        apply_teaching: bool,
        request_metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = dict(request_metadata or {})
        candidate = self._verified_learning_candidate(
            user_text=context.user_text,
            response_text=response_text,
            apply_teaching=apply_teaching,
            request_metadata=meta,
        )
        authority_allows = bool(context.authority.get("allow_learn", False))
        learned = False
        learning_reason = str(candidate.get("reason") or "NOT_ELIGIBLE")
        authorization_record_hash = None
        candidate_audit = self._candidate_audit_view(candidate)

        if candidate.get("eligible") and authority_allows:
            authorization_record_hash = self.outcome_ledger.append(
                {
                    "schema_version": "aion.hexcore.learning_authorization.v1",
                    "governance_id": context.governance_id,
                    "turn_id": context.turn_id,
                    "session_id": context.session_id,
                    "timestamp": _utc_timestamp(),
                    "authority": context.authority,
                    "candidate": candidate_audit,
                    "decision": "AUTHORIZED_FOR_VERIFIED_COMMIT",
                }
            )
            resonance = dict((meta.get("learning_outcome") or {}).get("resonance") or {})
            try:
                learned = bool(
                    self._memory_writer(
                        str(candidate["prompt"]),
                        str(candidate["answer"]),
                        resonance,
                        {
                            "source": "hexcore_governed_runtime",
                            "governance_id": context.governance_id,
                            "turn_id": context.turn_id,
                            "verified": True,
                            "verifier": candidate["verifier"],
                            "evidence_refs": candidate["evidence_refs"],
                            "verification_method": candidate["verification_method"],
                        },
                    )
                )
                learning_reason = "VERIFIED_MEMORY_COMMITTED" if learned else "MEMORY_WRITER_REJECTED"
            except Exception as exc:
                learned = False
                learning_reason = f"MEMORY_WRITE_FAILED:{type(exc).__name__}"
        elif candidate.get("eligible") and not authority_allows:
            learning_reason = str(context.authority.get("deny_reason") or "CAU_DENIED")

        record = {
            "schema_version": "aion.hexcore.governed_turn_outcome.v1",
            "governance_id": context.governance_id,
            "turn_id": context.turn_id,
            "session_id": context.session_id,
            "timestamp": _utc_timestamp(),
            "input_hash": hashlib.sha256(context.user_text.encode("utf-8")).hexdigest(),
            "response_hash": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
            "confidence": float(confidence),
            "mode": mode,
            "authority": context.authority,
            "recall_count": len(context.recalled_knowledge),
            "task_intelligence": {
                "trace_id": context.task_intelligence.get("trace_id"),
                "status": context.task_intelligence.get("status"),
                "canonical_count": len(context.task_intelligence.get("canonical_truth") or []),
                "experience_count": len(context.task_intelligence.get("experiential_memory") or []),
                "unverified_count": len(context.task_intelligence.get("encountered_unverified") or []),
                "required_skill_count": len(context.task_intelligence.get("required_skills") or []),
                "missing_capabilities": list(context.task_intelligence.get("missing_capabilities") or []),
            },
            "learning": {
                "candidate": candidate_audit,
                "committed": learned,
                "reason": learning_reason,
                "authorization_record_hash": authorization_record_hash,
            },
        }
        record_hash = self.outcome_ledger.append(record)
        try:
            trace_id = str(context.task_intelligence.get("trace_id") or "")
            if trace_id and self._cognitive_control_plane is not None:
                self._cognitive_control_plane.record_task_outcome(
                    trace_id=trace_id,
                    used_memory_ids=list(meta.get("used_memory_ids") or []),
                    used_skill_ids=list(meta.get("used_skill_ids") or []),
                    outcome=learning_reason,
                    verified=bool(learned),
                    verifier=str(candidate.get("verifier") or "") or None,
                    evidence_refs=list(candidate.get("evidence_refs") or []),
                )
        except Exception:
            pass
        return {
            "schema_version": "aion.hexcore.governance_result.v1",
            "governance_id": context.governance_id,
            "authority": context.authority,
            "recall_count": len(context.recalled_knowledge),
            "pattern_result_count": len(context.pattern_results),
            "tessaris_rule_count": len(context.tessaris_rules),
            "reasoning_providers": list(context.reasoning_providers),
            "cognitive_foundation": context.cognitive_foundation,
            "learning_layers": context.learning_layers,
            "task_intelligence": context.task_intelligence,
            "learning_committed": learned,
            "learning_reason": learning_reason,
            "learning_authorization_record_hash": authorization_record_hash,
            "outcome_record_hash": record_hash,
        }


_RUNTIME: Optional[HexCoreGovernedRuntime] = None
_RUNTIME_LOCK = threading.Lock()


def get_hexcore_governed_runtime() -> HexCoreGovernedRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = HexCoreGovernedRuntime()
        return _RUNTIME
