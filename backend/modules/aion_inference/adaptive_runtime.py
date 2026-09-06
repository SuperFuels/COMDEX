"""Adaptive routing, replay, context selection, and execution receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Iterable, Mapping, Optional

from .semantic_gateway import SemanticGateway
from .verified_calculations import VerifiedCalculationRouter
from .learned_atomsheets import LearnedAtomSheetStore
from .sqi_beams import (
    ModelRoutePredictor,
    SQICandidateBeam,
    WorkflowCatalog,
    collapse_beams_cost_aware,
)
from backend.modules.codex.beam_event_bus import BeamEvent, beam_event_bus


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.casefold()) if len(token) > 2}


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_trace_chain(path: Path) -> bool:
    """Verify a new-format SHA-256 ancestry chain; this is not signature authentication."""
    parent = "0" * 64
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        digest = event.pop("trace_receipt_sha256", None)
        if event.get("parent_trace_receipt_sha256") != parent or digest != _canonical_sha256(event):
            return False
        parent = digest
    return True


def verify_proof_receipt(receipt: Mapping[str, Any]) -> bool:
    payload = dict(receipt)
    digest = payload.pop("proof_receipt_sha256", None)
    return digest == _canonical_sha256(payload)


@dataclass(frozen=True)
class ContextSelection:
    selected: tuple[str, ...]
    original_utf8_bytes: int
    selected_utf8_bytes: int
    compression_percent: float
    policy_passages_preserved: int


class ContextSelector:
    POLICY_PATTERN = re.compile(
        r"\b(must|mustn't|must not|required|prohibited|authorised|authorized|do not|don't|never|policy|approval|consent)\b",
        re.I,
    )

    def select(self, query: str, passages: Iterable[str], max_bytes: int = 2048) -> ContextSelection:
        unique: dict[str, str] = {}
        for passage in passages:
            clean = " ".join(str(passage).split())
            if clean:
                unique.setdefault(clean.casefold(), clean)
        originals = tuple(unique.values())
        query_tokens = _tokens(query)
        ranked = []
        for index, passage in enumerate(originals):
            policy = bool(self.POLICY_PATTERN.search(passage))
            overlap = len(query_tokens & _tokens(passage))
            ranked.append((policy, overlap, -index, passage))
        ranked.sort(reverse=True)

        selected: list[str] = []
        used = 0
        for policy, _, _, passage in ranked:
            size = len(passage.encode("utf-8"))
            if used + size > max_bytes and not policy:
                continue
            selected.append(passage)
            used += size
        original_bytes = sum(len(item.encode("utf-8")) for item in originals)
        return ContextSelection(
            selected=tuple(selected),
            original_utf8_bytes=original_bytes,
            selected_utf8_bytes=used,
            compression_percent=(1.0 - used / original_bytes) * 100.0 if original_bytes else 0.0,
            policy_passages_preserved=sum(bool(self.POLICY_PATTERN.search(item)) for item in selected),
        )


class ReplayStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS verified_replay (
                    glyph_address TEXT PRIMARY KEY,
                    contract_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL
                )"""
            )

    def get(self, glyph_address: str, contract_sha256: str) -> Optional[Mapping[str, Any]]:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload_json FROM verified_replay WHERE glyph_address=? AND contract_sha256=?",
                (glyph_address, contract_sha256),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE verified_replay SET hit_count=hit_count+1,last_used_at=? WHERE glyph_address=?",
                (_utc_now(), glyph_address),
            )
        return json.loads(row[0])

    def put(self, glyph_address: str, contract_sha256: str, payload: Mapping[str, Any]) -> None:
        now = _utc_now()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT INTO verified_replay
                   (glyph_address,contract_sha256,payload_json,hit_count,created_at,last_used_at)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(glyph_address) DO UPDATE SET
                     contract_sha256=excluded.contract_sha256,
                     payload_json=excluded.payload_json,
                     last_used_at=excluded.last_used_at""",
                (glyph_address, contract_sha256, json.dumps(dict(payload), sort_keys=True), 0, now, now),
            )


@dataclass(frozen=True)
class AdaptiveRuntimeResult:
    schema_version: str
    route: str
    model_call_required: bool
    answer: Optional[str]
    glyph_address: str
    structured_result: Optional[Mapping[str, str]]
    proof_receipt: Mapping[str, Any]
    fallback_prompt: Optional[str]
    context_selection: Optional[ContextSelection]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AdaptiveInferenceRuntime:
    def __init__(self, *, replay_path: Path, trace_path: Path, learned_store: Optional[LearnedAtomSheetStore] = None) -> None:
        self.semantic = SemanticGateway()
        self.calculations = VerifiedCalculationRouter()
        self.context_selector = ContextSelector()
        self.workflows = WorkflowCatalog()
        self.model_route_predictor = ModelRoutePredictor()
        self.replay = ReplayStore(replay_path)
        self.trace_path = trace_path
        self.learned_store = learned_store
        self._trace_lock = threading.Lock()
        self._trace_parent = "0" * 64
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        if trace_path.exists() and trace_path.stat().st_size:
            last_line = trace_path.read_text(encoding="utf-8").splitlines()[-1]
            last_event = json.loads(last_line)
            self._trace_parent = str(
                last_event.get("trace_receipt_sha256")
                or hashlib.sha256(last_line.encode("utf-8")).hexdigest()
            )

    @staticmethod
    def _seal_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
        sealed = dict(receipt)
        sealed.pop("proof_receipt_sha256", None)
        sealed["proof_receipt_integrity"] = "sha256_canonical_binding_not_authentication"
        sealed["proof_receipt_sha256"] = _canonical_sha256(sealed)
        return sealed

    def _trace(self, result: AdaptiveRuntimeResult) -> None:
        with self._trace_lock:
            event = {
                "timestamp": _utc_now(),
                "schema_version": result.schema_version,
                "route": result.route,
                "model_call_required": result.model_call_required,
                "glyph_address": result.glyph_address,
                "proof_receipt": result.proof_receipt,
                "parent_trace_receipt_sha256": self._trace_parent,
                "trace_chain_integrity": "sha256_ancestry_not_authentication",
            }
            digest = _canonical_sha256(event)
            event["trace_receipt_sha256"] = digest
            with self.trace_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
            self._trace_parent = digest

    def _verified_result(
        self,
        *,
        glyph_address: str,
        answer: str,
        structured_result: Mapping[str, str],
        receipt: Mapping[str, Any],
        contract_hash: str,
    ) -> AdaptiveRuntimeResult:
        cached = self.replay.get(glyph_address, contract_hash)
        if cached is not None:
            result = AdaptiveRuntimeResult(
                schema_version="aion.adaptive_runtime.result.v1",
                route="verified_replay",
                model_call_required=False,
                answer=str(cached["answer"]),
                glyph_address=glyph_address,
                structured_result=dict(cached["structured_result"]),
                proof_receipt=self._seal_receipt({**dict(receipt), "replay_hit": True, "model_calls": 0}),
                fallback_prompt=None,
                context_selection=None,
            )
        else:
            self.replay.put(glyph_address, contract_hash, {
                "answer": answer, "structured_result": dict(structured_result)
            })
            result = AdaptiveRuntimeResult(
                schema_version="aion.adaptive_runtime.result.v1",
                route="verified_atomsheet",
                model_call_required=False,
                answer=answer,
                glyph_address=glyph_address,
                structured_result=dict(structured_result),
                proof_receipt=self._seal_receipt({**dict(receipt), "replay_hit": False, "model_calls": 0}),
                fallback_prompt=None,
                context_selection=None,
            )
        self._trace(result)
        return result

    def route(
        self,
        text: str,
        *,
        context: Iterable[str] = (),
        context_max_bytes: int = 2048,
    ) -> AdaptiveRuntimeResult:
        tasks = {
            "profit": self.semantic.route,
            "calculation": self.calculations.route,
            "workflow": self.workflows.lookup,
        }
        if self.learned_store is not None:
            tasks["learned"] = self.learned_store.route_text
        with ThreadPoolExecutor(max_workers=len(tasks), thread_name_prefix="aion-sqi") as executor:
            futures = {name: executor.submit(task, text) for name, task in tasks.items()}
            evaluated = {name: future.result() for name, future in futures.items()}

        profit = evaluated["profit"]
        calculation = evaluated["calculation"]
        learned = evaluated.get("learned")
        workflow = evaluated["workflow"]
        model_prediction = self.model_route_predictor.predict(text, profit.meaning_capsule.constraints)
        beams = [
            SQICandidateBeam(
                "profit_atomsheet", "verified_atomsheet", 1.0 if not profit.model_call_required else 0.0,
                not profit.model_call_required, str(profit.proof_receipt["gate_reason"]),
                {
                    "intent": profit.meaning_capsule.intent,
                    "gate_passed": not profit.model_call_required,
                    "execution_signature": f"atomsheet:{profit.proof_receipt['atomsheet_sha256']}",
                    "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 1.0},
                },
            ),
            SQICandidateBeam(
                "calculation_atomsheet", "verified_atomsheet", 0.99 if not calculation.model_call_required else 0.0,
                not calculation.model_call_required, str(calculation.proof_receipt["gate_reason"]),
                {
                    "intent": calculation.intent,
                    "gate_passed": not calculation.model_call_required,
                    "execution_signature": f"calculation:{calculation.intent}",
                    "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 1.0},
                },
            ),
        ]
        if learned is not None:
            beams.append(SQICandidateBeam(
                "learned_atomsheet", "verified_atomsheet", 0.98 if not learned.model_call_required else 0.0,
                not learned.model_call_required, str(learned.proof_receipt["gate_reason"]),
                {
                    "intent": learned.intent,
                    "gate_passed": not learned.model_call_required,
                    "execution_signature": f"learned:{learned.proof_receipt.get('contract_sha256')}",
                    "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 1.0},
                },
            ))
        beams.append(SQICandidateBeam(
            "workflow_lookup", "governed_workflow", workflow.score if workflow else 0.0,
            bool(workflow and workflow.executor_bound),
            "workflow_executor_bound" if workflow and workflow.executor_bound
            else "workflow_not_found" if workflow is None else "workflow_discovered_executor_not_bound",
            {
                **(asdict(workflow) if workflow else {"match": None}),
                "execution_signature": f"workflow:{workflow.workflow_id}" if workflow else "workflow:none",
                "execution_cost": {"model_calls": 0, "estimated_storage_bytes": 0, "estimated_ttft_ms": 2.0},
            },
        ))
        beams.append(SQICandidateBeam(
            "model_fallback", "full_model", 0.45 + 0.1 * model_prediction.confidence, True,
            model_prediction.reason, {
                **asdict(model_prediction),
                "execution_signature": (
                    f"model:{model_prediction.model_role}:{model_prediction.expert_prefetch_profile}"
                ),
                "execution_cost": {
                    "model_calls": 1,
                    "estimated_storage_bytes": None,
                    "estimated_ttft_ms": None,
                    "estimate_status": "model_runtime_measurement_required",
                },
            },
        ))
        collapse, fusion_receipts = collapse_beams_cost_aware(beams)

        beam_events = []
        for beam in beams:
            event_id = "be_" + hashlib.sha256(
                f"{profit.meaning_capsule.glyph_address}|{beam.beam_id}".encode("utf-8")
            ).hexdigest()[:10]
            event = BeamEvent(
                "semantic_route_candidate",
                source=profit.meaning_capsule.glyph_address,
                target=beam.route,
                drift=1.0 - beam.score,
                qscore=beam.score,
                metadata={
                    "beam_id": beam.beam_id,
                    "eligible": beam.eligible,
                    "reason": beam.reason,
                    "metric_basis": "deterministic_route_evidence_not_photonic_measurement",
                },
                event_id=event_id,
                timestamp=0.0,
            )
            beam_event_bus.publish(event)
            beam_events.append(event.to_dict())
        collapse_event = BeamEvent(
            "semantic_route_collapse",
            source=profit.meaning_capsule.glyph_address,
            target=collapse.selected_route,
            drift=1.0 - next(beam.score for beam in beams if beam.beam_id == collapse.selected_beam_id),
            qscore=next(beam.score for beam in beams if beam.beam_id == collapse.selected_beam_id),
            metadata={
                "selected_beam_id": collapse.selected_beam_id,
                "rejected_beam_ids": collapse.rejected_beam_ids,
                "metric_basis": "deterministic_route_evidence_not_photonic_measurement",
            },
            event_id="be_" + hashlib.sha256(
                f"{profit.meaning_capsule.glyph_address}|collapse|{collapse.selected_beam_id}".encode("utf-8")
            ).hexdigest()[:10],
            timestamp=0.0,
        )
        beam_event_bus.publish(collapse_event)
        beam_events.append(collapse_event.to_dict())
        gateway_evidence = {
            "semantic_gateway_pipeline": [
                "canonical_intent_extraction", "entity_and_unit_extraction", "constraint_preservation",
                "ambiguity_scoring", "atomsheet_lookup", "workflow_lookup", "context_selection",
                "model_route_prediction", "minimal_prompt_construction", "trace_and_proof_receipt",
            ],
            "sqi_beam_mode": "bounded_deterministic_parallel_candidates",
            "sqi_candidate_beams": [beam.to_dict() for beam in beams],
            "route_collapse": collapse.to_dict(),
            "route_collapse_policy": "highest_assurance_then_lowest_estimated_cost",
            "beam_fusion": fusion_receipts,
            "workflow_lookup": asdict(workflow) if workflow else None,
            "workflow_catalog_sha256": self.workflows.sha256,
            "model_route_prediction": asdict(model_prediction),
            "beam_events": beam_events,
        }

        if collapse.selected_beam_id == "profit_atomsheet":
            return self._verified_result(
                glyph_address=profit.meaning_capsule.glyph_address,
                answer=profit.answer or "",
                structured_result=profit.structured_result or {},
                receipt={**dict(profit.proof_receipt), **gateway_evidence},
                contract_hash=str(profit.proof_receipt["atomsheet_sha256"]),
            )

        if collapse.selected_beam_id == "calculation_atomsheet":
            return self._verified_result(
                glyph_address=calculation.glyph_address,
                answer=calculation.answer or "",
                structured_result=calculation.structured_result or {},
                receipt={**dict(calculation.proof_receipt), **gateway_evidence},
                contract_hash=str(calculation.proof_receipt["catalog_sha256"]),
            )

        if collapse.selected_beam_id == "learned_atomsheet" and learned is not None:
            return self._verified_result(
                glyph_address=str(learned.proof_receipt["glyph_address"]),
                answer=learned.answer or "",
                structured_result=learned.structured_result or {},
                receipt={**dict(learned.proof_receipt), **gateway_evidence},
                contract_hash=str(learned.proof_receipt["contract_sha256"]),
            )

        selection = self.context_selector.select(text, context, max_bytes=context_max_bytes)
        fallback = json.dumps({
            "meaning": json.loads(profit.minimal_model_prompt or "{}"),
            "selected_context": selection.selected,
            "selected_workflow": asdict(workflow) if workflow else None,
            "model_route": asdict(model_prediction),
        }, sort_keys=True, separators=(",", ":"))
        result = AdaptiveRuntimeResult(
            schema_version="aion.adaptive_runtime.result.v1",
            route="full_model",
            model_call_required=True,
            answer=None,
            glyph_address=profit.meaning_capsule.glyph_address,
            structured_result=None,
            proof_receipt=self._seal_receipt({
                **dict(profit.proof_receipt),
                **gateway_evidence,
                "calculation_gate_reason": calculation.proof_receipt["gate_reason"],
                "context_original_utf8_bytes": selection.original_utf8_bytes,
                "context_selected_utf8_bytes": selection.selected_utf8_bytes,
            }),
            fallback_prompt=fallback,
            context_selection=selection,
        )
        self._trace(result)
        return result
