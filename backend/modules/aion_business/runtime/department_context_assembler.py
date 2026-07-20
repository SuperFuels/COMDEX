"""Selective, hash-bound Business Container retrieval for Department Pilots."""

from __future__ import annotations

from typing import Any

from backend.modules.aion_business.contracts.department_pilot import (
    DepartmentPilotTask,
    RetrievedEvidence,
    canonical_contract_hash,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    create_retrieved_evidence,
)


def _resolve_json_pointer(document: Any, pointer: str | None) -> Any:
    if not pointer:
        return document
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise KeyError("invalid_json_pointer")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(part)
    return current


def _bounded(value: Any, *, depth: int = 0) -> Any:
    if depth >= 5:
        return "[retrieval depth limited]"
    if isinstance(value, dict):
        return {str(key): _bounded(item, depth=depth + 1) for key, item in list(value.items())[:80]}
    if isinstance(value, list):
        return [_bounded(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, str) and len(value) > 4000:
        return value[:4000] + "…"
    return value


def _project_container(kind: str, selected: Any, department_id: str) -> dict[str, Any]:
    if not isinstance(selected, dict):
        return {"value": _bounded(selected)}

    if kind == "business_identity":
        keys = (
            "legal_name",
            "trading_name",
            "business_type",
            "sector",
            "stage",
            "country",
            "region",
            "city",
            "timezone",
            "currency",
            "description",
        )
        return {key: selected.get(key) for key in keys if selected.get(key) is not None}

    if kind == "business_map":
        keys = (
            "facts",
            "assumptions",
            "unknowns",
            "conflicts",
            "unanswered_fields",
            "department_discovery_gaps",
            "revision",
        )
        return _bounded({key: selected.get(key) for key in keys if key in selected})

    if kind == "department_intelligence":
        departments = selected.get("departments") or {}
        return {
            "department": _bounded(departments.get(department_id) or {}),
            "revision": selected.get("revision"),
        }

    if kind == "business_financial_model":
        keys = (
            "model_status",
            "currency",
            "period_basis",
            "metrics",
            "assumptions",
            "missing_information",
            "evidence_refs",
            "revision",
        )
        return _bounded({key: selected.get(key) for key in keys if key in selected})

    if kind == "business_operating_model":
        return _bounded(
            {
                "model_status": selected.get("model_status"),
                "currency": selected.get("currency"),
                "offering_count": len(selected.get("offerings") or []),
                "offering_sample": (selected.get("offerings") or [])[:20],
                "unit_economics": selected.get("unit_economics") or [],
                "inventory_metrics": selected.get("inventory_metrics") or {},
                "capacity_model": selected.get("capacity_model") or {},
                "procurement_queue": (selected.get("procurement_queue") or [])[:20],
                "revision": selected.get("revision"),
            }
        )

    if kind == "brand_foundation":
        keys = (
            "objective",
            "target_audience",
            "offer",
            "channels",
            "hard_rules",
            "brand_overview",
            "brand_positioning",
            "brand_voice",
            "messaging_rules",
        )
        return _bounded({key: selected.get(key) for key in keys if key in selected})

    return _bounded(selected)


class DepartmentContextAssembler:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def retrieve_for_task(
        self,
        task: DepartmentPilotTask,
        *,
        retrieved_at: str,
        retrieved_by: str,
    ) -> list[RetrievedEvidence]:
        evidence: list[RetrievedEvidence] = []
        for reference in task.context_refs:
            retrieval_suffix = canonical_contract_hash(
                {"reference_id": reference.reference_id, "retrieved_at": retrieved_at}
            )[7:19]
            payload = self.repository.load_optional_dict(
                task.workspace_id, reference.container_kind  # type: ignore[arg-type]
            )
            common = {
                "evidence_id": f"{task.task_id}:{reference.reference_id}:{retrieval_suffix}",
                "task_id": task.task_id,
                "department_id": task.department_id,
                "reference_id": reference.reference_id,
                "expected_content_hash": reference.content_hash,
                "retrieved_at": retrieved_at,
                "retrieved_by": retrieved_by,
            }
            if payload is None:
                evidence.append(
                    create_retrieved_evidence(
                        **common,
                        retrieval_status="missing",
                        source_content_hash=None,
                        verification_state="unverified",
                        data={},
                        issue="business_container_not_found",
                    )
                )
                continue

            try:
                selected = _resolve_json_pointer(payload, reference.json_pointer)
            except (KeyError, IndexError, ValueError, TypeError):
                evidence.append(
                    create_retrieved_evidence(
                        **common,
                        retrieval_status="missing",
                        source_content_hash=canonical_contract_hash(payload),
                        verification_state="unverified",
                        data={},
                        issue="context_json_pointer_not_found",
                    )
                )
                continue

            source_hash = canonical_contract_hash(selected)
            projected = _project_container(
                reference.container_kind, selected, task.department_id
            )
            if source_hash != reference.content_hash:
                evidence.append(
                    create_retrieved_evidence(
                        **common,
                        retrieval_status="hash_mismatch",
                        source_content_hash=source_hash,
                        verification_state="stale",
                        data=projected,
                        issue="business_container_changed_since_boardroom_approval",
                    )
                )
                continue

            evidence.append(
                create_retrieved_evidence(
                    **common,
                    retrieval_status="retrieved",
                    source_content_hash=source_hash,
                    verification_state=reference.verification_state,
                    data=projected,
                    issue=None,
                )
            )
        return evidence
