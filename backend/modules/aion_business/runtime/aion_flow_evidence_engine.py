from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Mapping

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


Retriever = Callable[[str], Iterable[Mapping[str, Any]]]
Validator = Callable[[Any, Mapping[str, Any]], tuple[bool, list[str]]]


class AionFlowEvidenceEngine:
    """Provider-neutral evidence packs with deterministic validation and fail-closed provenance."""

    def __init__(self, *, maximum_documents: int = 40, maximum_chars: int = 250_000) -> None:
        self.maximum_documents = max(1, min(int(maximum_documents), 200))
        self.maximum_chars = max(1_000, min(int(maximum_chars), 2_000_000))
        self._retrievers: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Validator] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._revoked_sources: Dict[str, Dict[str, Any]] = {}
        self.register_validator("json_schema", self._validate_json_schema)
        self.register_validator("calculation", self._validate_calculation)

    def register_retriever(
        self,
        retriever_id: str,
        *,
        source_kind: str,
        retrieve: Retriever,
        allowed_purposes: Iterable[str],
        public: bool = False,
    ) -> None:
        if source_kind not in {"file", "email", "calendar", "crm", "accounting", "database", "public_web"}:
            raise ValueError("evidence_source_kind_invalid")
        purposes = sorted({str(item).strip() for item in allowed_purposes if str(item).strip()})
        if not retriever_id.strip() or not purposes:
            raise ValueError("evidence_retriever_identity_and_purpose_required")
        self._retrievers[retriever_id] = {
            "source_kind": source_kind,
            "retrieve": retrieve,
            "allowed_purposes": purposes,
            "public": bool(public),
        }

    def register_validator(self, validator_id: str, validator: Validator) -> None:
        if not validator_id.strip() or not callable(validator):
            raise ValueError("evidence_validator_invalid")
        self._validators[validator_id] = validator

    def retrieve(
        self,
        retriever_id: str,
        *,
        query: str,
        purpose: str,
        cache_seconds: int = 0,
    ) -> Dict[str, Any]:
        route = self._retrievers.get(retriever_id)
        if not route:
            raise KeyError("evidence_retriever_not_registered")
        if purpose not in route["allowed_purposes"]:
            raise PermissionError("evidence_purpose_not_allowed")
        if not query.strip():
            raise ValueError("evidence_query_required")
        key = canonical_hash({"retriever_id": retriever_id, "query": query, "purpose": purpose})
        cached = self._cache.get(key)
        if cached and cache_seconds > 0 and self._age_seconds(cached["retrieved_at"]) <= min(cache_seconds, 86_400):
            return {**cached, "cache": "hit"}
        rows = list(route["retrieve"](query))[: self.maximum_documents]
        documents, used = [], 0
        for index, row in enumerate(rows):
            content = str(row.get("content") or "")
            if not content or used + len(content) > self.maximum_chars:
                continue
            source_id = str(row.get("source_id") or f"{retriever_id}:{index}")
            if source_id in self._revoked_sources:
                continue
            used += len(content)
            document = {
                "source_id": source_id,
                "source_kind": route["source_kind"],
                "uri": str(row.get("uri") or ""),
                "title": str(row.get("title") or "")[:300],
                "observed_at": str(row.get("observed_at") or utc_now_iso()),
                "retrieved_at": utc_now_iso(),
                "source_class": str(row.get("source_class") or ("public" if route["public"] else "customer_authorized")),
                "quality": max(0.0, min(float(row.get("quality", 0.5)), 1.0)),
                "content": content,
                "content_hash": canonical_hash(content),
                "status": "available",
            }
            documents.append(document)
        result = {
            "schema_version": "aion.flow.retrieved_evidence.v1",
            "retriever_id": retriever_id,
            "query": query,
            "purpose": purpose,
            "retrieved_at": utc_now_iso(),
            "documents": documents,
            "interpretation": None,
            "bounded": True,
            "cache": "miss",
        }
        result["retrieval_hash"] = canonical_hash(result)
        self._cache[key] = result
        return result

    def build_pack(
        self,
        retrievals: Iterable[Mapping[str, Any]],
        *,
        claims: Iterable[Mapping[str, Any]],
        required_evidence: bool = True,
        maximum_age_seconds: int = 86_400,
        minimum_quality: float = 0.0,
    ) -> Dict[str, Any]:
        documents = []
        for retrieval in retrievals:
            documents.extend(dict(item) for item in retrieval.get("documents") or [])
        by_id = {item["source_id"]: item for item in documents if item.get("source_id")}
        normalized_claims, errors = [], []
        verdicts: Dict[str, set[str]] = {}
        for item in claims:
            claim = str(item.get("claim") or "").strip()
            source_ids = list(dict.fromkeys(str(value) for value in item.get("source_ids") or []))
            missing = [value for value in source_ids if value not in by_id]
            stale = [value for value in source_ids if value in by_id and self._age_seconds(by_id[value]["observed_at"]) > maximum_age_seconds]
            low_quality = [value for value in source_ids if value in by_id and float(by_id[value]["quality"]) < minimum_quality]
            if not claim:
                errors.append("claim_text_required")
            if missing:
                errors.append(f"claim_source_missing:{','.join(missing)}")
            if stale:
                errors.append(f"claim_source_stale:{','.join(stale)}")
            if low_quality:
                errors.append(f"claim_source_quality_below_threshold:{','.join(low_quality)}")
            if required_evidence and not source_ids:
                errors.append("claim_evidence_required")
            verdict = str(item.get("verdict") or "interpretation").strip().lower()
            key = " ".join(claim.lower().split())
            verdicts.setdefault(key, set()).add(verdict)
            normalized_claims.append({
                "claim": claim,
                "verdict": verdict,
                "source_ids": source_ids,
                "confidence": max(0.0, min(float(item.get("confidence", 0.0)), 1.0)),
                "status": "supported" if source_ids and not (missing or stale or low_quality) else "unresolved",
            })
        contradictions = [claim for claim, values in verdicts.items() if len(values - {"interpretation", "unknown"}) > 1]
        if contradictions:
            errors.extend(f"claim_contradiction:{claim}" for claim in contradictions)
        pack = {
            "schema_version": "aion.flow.evidence_pack.v1",
            "documents": documents,
            "claims": normalized_claims,
            "contradictions": contradictions,
            "errors": sorted(set(errors)),
            "status": "verified" if not errors else "unresolved",
            "evidence_and_interpretation_separated": True,
            "created_at": utc_now_iso(),
        }
        pack["evidence_pack_hash"] = canonical_hash(pack)
        if required_evidence and (not documents or errors):
            pack["downstream_execution_allowed"] = False
        else:
            pack["downstream_execution_allowed"] = True
        return pack

    def validate(self, validator_id: str, value: Any, rule: Mapping[str, Any]) -> Dict[str, Any]:
        validator = self._validators.get(validator_id)
        if not validator:
            raise KeyError("evidence_validator_not_registered")
        passed, errors = validator(value, rule)
        result = {"validator_id": validator_id, "passed": bool(passed), "errors": list(errors), "validated_at": utc_now_iso()}
        result["validation_hash"] = canonical_hash(result)
        return result

    def revoke_source(self, source_id: str, *, reason: str) -> Dict[str, Any]:
        if not source_id.strip() or not reason.strip():
            raise ValueError("source_revocation_identity_and_reason_required")
        event = {"source_id": source_id, "reason": reason, "revoked_at": utc_now_iso()}
        event["revocation_hash"] = canonical_hash(event)
        self._revoked_sources[source_id] = event
        for cached in self._cache.values():
            for document in cached.get("documents") or []:
                if document.get("source_id") == source_id:
                    document["status"] = "revoked"
        return event

    @staticmethod
    def _validate_json_schema(value: Any, rule: Mapping[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        if rule.get("type") == "object" and not isinstance(value, Mapping):
            errors.append("expected_object")
        if isinstance(value, Mapping):
            errors.extend(f"required_field_missing:{key}" for key in rule.get("required") or [] if key not in value)
            properties = rule.get("properties") or {}
            for key, specification in properties.items():
                if key not in value:
                    continue
                expected = specification.get("type")
                matches = {
                    "string": isinstance(value[key], str), "number": isinstance(value[key], (int, float)) and not isinstance(value[key], bool),
                    "integer": isinstance(value[key], int) and not isinstance(value[key], bool), "boolean": isinstance(value[key], bool),
                    "array": isinstance(value[key], list), "object": isinstance(value[key], Mapping),
                }.get(expected, True)
                if not matches:
                    errors.append(f"field_type_invalid:{key}")
        return not errors, errors

    @staticmethod
    def _validate_calculation(value: Any, rule: Mapping[str, Any]) -> tuple[bool, list[str]]:
        try:
            actual = float(value)
            expected = float(rule["expected"])
            tolerance = max(0.0, float(rule.get("tolerance", 0)))
        except (KeyError, TypeError, ValueError):
            return False, ["calculation_rule_invalid"]
        passed = abs(actual - expected) <= tolerance
        return passed, [] if passed else ["calculation_outside_tolerance"]

    @staticmethod
    def _age_seconds(value: str) -> float:
        try:
            instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - instant).total_seconds())
        except ValueError:
            return float("inf")
