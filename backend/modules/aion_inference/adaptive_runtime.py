"""Adaptive routing, replay, context selection, and execution receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping, Optional

from .semantic_gateway import SemanticGateway
from .verified_calculations import VerifiedCalculationRouter


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.casefold()) if len(token) > 2}


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
    def __init__(self, *, replay_path: Path, trace_path: Path) -> None:
        self.semantic = SemanticGateway()
        self.calculations = VerifiedCalculationRouter()
        self.context_selector = ContextSelector()
        self.replay = ReplayStore(replay_path)
        self.trace_path = trace_path
        trace_path.parent.mkdir(parents=True, exist_ok=True)

    def _trace(self, result: AdaptiveRuntimeResult) -> None:
        event = {
            "timestamp": _utc_now(),
            "schema_version": result.schema_version,
            "route": result.route,
            "model_call_required": result.model_call_required,
            "glyph_address": result.glyph_address,
            "proof_receipt": result.proof_receipt,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

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
                proof_receipt={**dict(receipt), "replay_hit": True, "model_calls": 0},
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
                proof_receipt={**dict(receipt), "replay_hit": False, "model_calls": 0},
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
        profit = self.semantic.route(text)
        if not profit.model_call_required:
            return self._verified_result(
                glyph_address=profit.meaning_capsule.glyph_address,
                answer=profit.answer or "",
                structured_result=profit.structured_result or {},
                receipt=profit.proof_receipt,
                contract_hash=str(profit.proof_receipt["atomsheet_sha256"]),
            )

        calculation = self.calculations.route(text)
        if not calculation.model_call_required:
            return self._verified_result(
                glyph_address=calculation.glyph_address,
                answer=calculation.answer or "",
                structured_result=calculation.structured_result or {},
                receipt=calculation.proof_receipt,
                contract_hash=str(calculation.proof_receipt["catalog_sha256"]),
            )

        selection = self.context_selector.select(text, context, max_bytes=context_max_bytes)
        fallback = json.dumps({
            "meaning": json.loads(profit.minimal_model_prompt or "{}"),
            "selected_context": selection.selected,
        }, sort_keys=True, separators=(",", ":"))
        result = AdaptiveRuntimeResult(
            schema_version="aion.adaptive_runtime.result.v1",
            route="full_model",
            model_call_required=True,
            answer=None,
            glyph_address=profit.meaning_capsule.glyph_address,
            structured_result=None,
            proof_receipt={
                **dict(profit.proof_receipt),
                "calculation_gate_reason": calculation.proof_receipt["gate_reason"],
                "context_original_utf8_bytes": selection.original_utf8_bytes,
                "context_selected_utf8_bytes": selection.selected_utf8_bytes,
            },
            fallback_prompt=fallback,
            context_selection=selection,
        )
        self._trace(result)
        return result
