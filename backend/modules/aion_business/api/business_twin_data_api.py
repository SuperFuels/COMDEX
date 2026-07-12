from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from typing import Any, Dict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    BusinessFinancialModelContainer,
    BusinessIdentityContainer,
    BusinessMapContainer,
    BusinessStructureContainer,
    DepartmentIntelligenceContainer,
)
from backend.modules.aion_business.contracts.workspace import BusinessProfile, WorkspaceSpec
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_aliases, canonical_business_id
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


router = APIRouter(prefix="/api/aion/business/data", tags=["aion-business-data"])

FINANCE_ARTIFACT_CATEGORIES = {
    "spreadsheets": {".csv", ".xlsx", ".xls", ".xml", ".json"},
    "bank-statements": {".csv", ".xlsx", ".xls", ".pdf", ".ofx", ".qif"},
    "invoices-receipts": {".csv", ".xlsx", ".xls", ".pdf", ".xml", ".json"},
    "management-accounts": {".csv", ".xlsx", ".xls", ".pdf", ".xml", ".json"},
    "vat-tax": {".csv", ".xlsx", ".xls", ".pdf", ".xml", ".json"},
    "payroll": {".csv", ".xlsx", ".xls", ".pdf", ".xml", ".json"},
    "payment-processors": {".csv", ".xlsx", ".xls", ".pdf", ".json"},
    "crm-sales": {".csv", ".xlsx", ".xls", ".pdf", ".json"},
    "reports": {".csv", ".xlsx", ".xls", ".pdf", ".json"},
    "models": {".csv", ".xlsx", ".xls", ".pdf", ".json"},
    "evidence-receipts": {".csv", ".xlsx", ".xls", ".pdf", ".json"},
}
FINANCE_CABINET_FOLDERS = {
    "spreadsheets": "Spreadsheets",
    "bank-statements": "Bank Statements",
    "invoices-receipts": "Invoices & Receipts",
    "management-accounts": "Management Accounts",
    "vat-tax": "VAT & Tax",
    "payroll": "Payroll",
    "payment-processors": "Payment Processors",
    "crm-sales": "CRM & Sales",
    "reports": "Reports",
    "models": "Financial Models",
    "evidence-receipts": "Evidence & Receipts",
}
MAX_FINANCE_ARTIFACT_BYTES = 25 * 1024 * 1024


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def _object(value: Any) -> Dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _business_type(value: Any) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_")
    aliases = {
        "service": "service_business",
        "services": "service_business",
        "service_business": "service_business",
        "ecommerce": "ecommerce",
        "e-commerce": "ecommerce",
        "marketplace": "marketplace_seller",
        "marketplace_seller": "marketplace_seller",
        "agency": "agency",
        "hybrid": "hybrid",
        "mixed": "hybrid",
        "mixture": "hybrid",
    }
    return aliases.get(raw, "service_business")


class FoundationCommitRequest(BaseModel):
    packet: Dict[str, Any]
    source: str = "business_foundation"


class ContainerWriteRequest(BaseModel):
    payload: Dict[str, Any]
    source: str = "desktop_runtime"
    expected_revision: int | None = None


class BusinessMapFactsRequest(BaseModel):
    facts: list[Dict[str, Any]] = Field(default_factory=list)
    source: str = "desktop_runtime"


def _repo() -> BusinessContainerRepository:
    return BusinessContainerRepository()


def _workspaces() -> WorkspaceRepository:
    return WorkspaceRepository()


def _ensure_workspace(business_id: str, draft: Dict[str, Any]) -> None:
    repository = _workspaces()
    try:
        repository.load(business_id)
        return
    except FileNotFoundError:
        pass

    business_name = _text(draft.get("business_name") or draft.get("name")) or business_id
    repository.save(
        WorkspaceSpec(
            id=business_id,
            name=business_name,
            business_type=_business_type(draft.get("business_type") or draft.get("business_model")),
            owner=_text(draft.get("user_name") or draft.get("owner") or draft.get("role")) or "owner",
            deployment_mode="local",
            business_profile=BusinessProfile(
                legal_name=business_name,
                trading_name=business_name,
                sector=_text(draft.get("industry") or draft.get("business_type")),
                stage=_text(draft.get("business_stage") or draft.get("stage")),
                products=[_text(draft.get("offer_summary") or draft.get("products_services"))]
                if _text(draft.get("offer_summary") or draft.get("products_services")) else [],
                customer_types=[_text(draft.get("target_customers"))] if _text(draft.get("target_customers")) else [],
                preferred_tools=[_text(draft.get("current_tools") or draft.get("systems"))]
                if _text(draft.get("current_tools") or draft.get("systems")) else [],
            ),
            status="active",
        )
    )


def _migrate_legacy_aliases(candidate: str, business_id: str) -> list[Dict[str, Any]]:
    """Copy legacy underscore-scoped runtime data into the canonical hyphen scope.

    Legacy data is retained. This is deliberately non-destructive until a later
    verified cleanup migration is approved.
    """
    migrations: list[Dict[str, Any]] = []
    for alias in canonical_business_aliases(candidate):
        if alias == business_id:
            continue
        legacy_container = AIONBusinessPaths.BUSINESS_CONTAINERS / alias
        canonical_container = AIONBusinessPaths.BUSINESS_CONTAINERS / business_id
        if legacy_container.exists():
            canonical_container.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy_container, canonical_container, dirs_exist_ok=True)
            for copied_json in canonical_container.glob("*.json"):
                try:
                    payload = json.loads(copied_json.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        payload["workspace_id"] = business_id
                        if str(payload.get("id") or "").startswith(f"{alias}."):
                            payload["id"] = f"{business_id}.{str(payload['id']).split('.', 1)[1]}"
                        if isinstance(payload.get("meta"), dict):
                            payload["meta"]["workspace_id"] = business_id
                            payload["meta"]["source"] = "legacy_alias_migration"
                            payload["meta"]["updated_at"] = _now()
                        copied_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
                except Exception:
                    continue
            migrations.append({"kind": "business_container", "from": alias, "to": business_id})

        legacy_cabinet = AIONBusinessPaths.ROOT / "workflow_file_cabinets" / alias / "tree.json"
        canonical_cabinet = AIONBusinessPaths.ROOT / "workflow_file_cabinets" / business_id / "tree.json"
        if legacy_cabinet.exists() and not canonical_cabinet.exists():
            canonical_cabinet.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_cabinet, canonical_cabinet)
            try:
                tree = json.loads(canonical_cabinet.read_text(encoding="utf-8"))
                tree["workspace_id"] = business_id
                tree["business_container"] = business_id
                canonical_cabinet.write_text(json.dumps(tree, indent=2, sort_keys=True), encoding="utf-8")
            except Exception:
                pass
            migrations.append({"kind": "file_cabinet", "from": alias, "to": business_id})

        legacy_workspace = AIONBusinessPaths.WORKSPACES / f"{alias}.json"
        canonical_workspace = AIONBusinessPaths.WORKSPACES / f"{business_id}.json"
        if legacy_workspace.exists() and not canonical_workspace.exists():
            canonical_workspace.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_workspace, canonical_workspace)
            migrations.append({"kind": "workspace", "from": alias, "to": business_id})
    return migrations


def _meta(business_id: str, key: str, source: str) -> BusinessContainerMeta:
    return BusinessContainerMeta(
        workspace_id=business_id,
        container_key=key,
        updated_at=_now(),
        source=source,
    )


def _receipt(*, business_id: str, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "business_id": business_id,
        "container_kind": kind,
        "revision": int(payload.get("revision") or 1),
        "payload_hash": _hash(payload),
        "written_at": _now(),
        "storage_state": "committed_to_business_container",
    }


def _safe_filename(value: str) -> str:
    name = Path(str(value or "upload")).name.strip()
    stem = re.sub(r"[^a-zA-Z0-9_. -]+", "-", name).strip(". ")
    return stem[:180] or "upload"


def _ensure_folder(children: list[Dict[str, Any]], *, node_id: str, name: str, node_type: str = "folder") -> Dict[str, Any]:
    node = next((item for item in children if isinstance(item, dict) and item.get("id") == node_id), None)
    if node is None:
        node = {"id": node_id, "name": name, "type": node_type, "children": []}
        children.append(node)
    node["name"] = name
    node["type"] = node_type
    if not isinstance(node.get("children"), list):
        node["children"] = []
    return node


def _add_finance_file_cabinet_pointer(*, business_id: str, category: str, record: Dict[str, Any]) -> Dict[str, Any]:
    tree = WorkflowFileCabinetRepository.load(business_id)
    folders = tree.get("folders")
    if not isinstance(folders, list):
        folders = list((tree.get("root") or {}).get("children") or [])
        tree["folders"] = folders

    finance = _ensure_folder(folders, node_id="folder_finance", name="Finance", node_type="department")
    for key, label in FINANCE_CABINET_FOLDERS.items():
        _ensure_folder(finance["children"], node_id=f"folder_finance_{key.replace('-', '_')}", name=label)
    destination = _ensure_folder(
        finance["children"],
        node_id=f"folder_finance_{category.replace('-', '_')}",
        name=FINANCE_CABINET_FOLDERS[category],
    )

    pointer_id = f"finance_artifact_pointer_{record['artifact_id']}"
    pointer = {
        "id": pointer_id,
        "name": record["target"]["artifact_name"],
        "type": "business_container_artifact",
        "document_type": record["target"]["artifact_type"],
        "source_of_truth": "business_container",
        "file_cabinet_role": "index_pointer_only",
        "status": "committed",
        "target": {
            "business_container_id": business_id,
            "sub_container": "finance",
            "category": category,
            "artifact_type": record["target"]["artifact_type"],
            "storage_path": record["storage_path"],
            "artifact_id": record["artifact_id"],
            "artifact_hash": record["artifact_hash"],
            "receipt_hash": record["receipt_hash"],
            "replay_locator_hash": record["replay_locator_hash"],
        },
    }
    existing_index = next((index for index, item in enumerate(destination["children"]) if item.get("id") == pointer_id), None)
    if existing_index is None:
        destination["children"].append(pointer)
    else:
        destination["children"][existing_index] = pointer
    tree["root"] = {**_object(tree.get("root")), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
    WorkflowFileCabinetRepository.save(business_id, tree)
    return pointer


@router.get("/identity/{candidate}")
def resolve_business_identity(candidate: str) -> Dict[str, Any]:
    try:
        business_id = canonical_business_id(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "business_id": business_id,
        "workspace_id": business_id,
        "container_id": business_id,
        "aliases": canonical_business_aliases(candidate),
    }


@router.post("/foundation/{candidate}")
def commit_foundation(candidate: str, request: FoundationCommitRequest) -> Dict[str, Any]:
    try:
        business_id = canonical_business_id(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    packet = _object(request.packet)
    draft = _object(packet.get("foundation_draft"))
    business_map = _object(packet.get("business_map"))
    migrations = _migrate_legacy_aliases(candidate, business_id)
    _ensure_workspace(business_id, draft)
    repository = _repo()

    name = _text(draft.get("business_name") or draft.get("name")) or business_id
    identity = BusinessIdentityContainer(
        id=f"{business_id}.business_identity",
        workspace_id=business_id,
        meta=_meta(business_id, "business_identity", request.source),
        legal_name=name,
        trading_name=name,
        business_type=_business_type(draft.get("business_type") or draft.get("business_model")),
        sector=_text(draft.get("industry") or draft.get("business_type")),
        stage=_text(draft.get("business_stage") or draft.get("stage")),
        owner=_text(draft.get("user_name") or draft.get("owner") or draft.get("role")),
        country=_text(draft.get("country")) or "unspecified",
        region=_text(draft.get("region") or draft.get("service_area") or draft.get("location")),
        city=_text(draft.get("city")),
        timezone=_text(draft.get("timezone")) or "UTC",
        currency=_text(draft.get("currency")) or "unspecified",
        primary_domain=_text(draft.get("primary_domain")),
        website_url=_text(draft.get("website_url") or draft.get("website")),
        primary_email=_text(draft.get("contact_email") or draft.get("primary_email")),
        description=_text(draft.get("offer_summary") or draft.get("products_services")),
        source_refs=[request.source, str(packet.get("schema_version") or "foundation_packet")],
    )
    repository.save_model(identity)

    structure = BusinessStructureContainer(
        id=f"{business_id}.business_structure",
        workspace_id=business_id,
        meta=_meta(business_id, "business_structure", request.source),
        identity={
            "workspace_id": business_id,
            "business_name": name,
            "legal_name": name,
            "public_brand_name": name,
            "business_type": _business_type(draft.get("business_type") or draft.get("business_model")),
            "country": _text(draft.get("country")) or "unspecified",
            "region": _text(draft.get("region") or draft.get("service_area") or draft.get("location")),
            "city": _text(draft.get("city")),
            "timezone": _text(draft.get("timezone")) or "UTC",
            "currency": _text(draft.get("currency")) or "unspecified",
            "primary_domain": _text(draft.get("primary_domain")),
            "website_url": _text(draft.get("website_url") or draft.get("website")),
            "primary_email": _text(draft.get("contact_email") or draft.get("primary_email")),
            "description": _text(draft.get("offer_summary") or draft.get("products_services")),
            "founder_name": _text(draft.get("user_name") or draft.get("owner")),
            "onboarding_status": "foundation_complete",
            "active": True,
        },
        services=[{
            "id": f"{business_id}.service.foundation",
            "workspace_id": business_id,
            "name": _text(draft.get("offer_summary") or draft.get("products_services")) or "Primary service",
            "slug": "primary-service",
            "description": _text(draft.get("offer_summary") or draft.get("products_services")),
            "delivery_mode": "onsite",
            "pricing_type": "quote",
            "currency": _text(draft.get("currency")) or "EUR",
            "service_area": [_text(draft.get("service_area") or draft.get("location"))] if _text(draft.get("service_area") or draft.get("location")) else [],
            "status": "active",
            "active": True,
        }] if draft.get("offer_summary") or draft.get("products_services") else [],
        revenue_streams=[{
            "id": f"{business_id}.revenue.foundation",
            "workspace_id": business_id,
            "name": "Primary revenue stream",
            "stream_type": "service_sales",
            "cadence": "variable",
            "status": "active",
            "description": _text(draft.get("revenue_model") or draft.get("business_model")),
            "currency": _text(draft.get("currency")) or "EUR",
            "active": True,
        }] if draft.get("revenue_model") or draft.get("business_model") else [],
        fulfillment_processes=[{
            "id": f"{business_id}.fulfillment.foundation",
            "workspace_id": business_id,
            "name": "Primary delivery process",
            "fulfillment_mode": "onsite_service",
            "status": "active",
            "description": _text(draft.get("delivery_model")),
            "active": True,
        }] if draft.get("delivery_model") else [],
        functions=[{
            "id": f"{business_id}.function.{key}",
            "workspace_id": business_id,
            "department_key": key,
            "key": key,
            "name": key.title(),
            "description": f"{key.title()} business function",
            "status": "draft",
            "active": True,
        } for key in ["finance", "marketing", "sales", "operations", "support"]],
        teams=[],
    )
    repository.save_model(structure)

    map_model = BusinessMapContainer(
        id=f"{business_id}.business_map",
        workspace_id=business_id,
        meta=_meta(business_id, "business_map", request.source),
        facts=_list(business_map.get("facts")),
        assumptions=_list(business_map.get("assumptions")),
        unknowns=_list(business_map.get("unknowns")),
        conflicts=_list(business_map.get("conflicts")),
        unanswered_fields=[str(x) for x in _list(business_map.get("unanswered_fields"))],
        department_discovery_gaps=[str(x) for x in _list(business_map.get("department_discovery_gaps"))],
        source_refs=[request.source, str(packet.get("schema_version") or "foundation_packet")],
        revision=1,
    )
    repository.save_model(map_model)

    try:
        ledger = repository.load_department_intelligence(business_id)
    except FileNotFoundError:
        ledger = DepartmentIntelligenceContainer(
            id=f"{business_id}.department_intelligence",
            workspace_id=business_id,
            meta=_meta(business_id, "department_intelligence", request.source),
            departments={key: {"department": key, "status": "needs_discovery"} for key in ["finance", "marketing", "sales", "operations", "support"]},
        )
        repository.save_model(ledger)

    return {
        "ok": True,
        "business_id": business_id,
        "legacy_alias_migrations": migrations,
        "containers": {
            "business_identity": _receipt(business_id=business_id, kind="business_identity", payload=identity.model_dump(mode="json")),
            "business_structure": _receipt(business_id=business_id, kind="business_structure", payload=structure.model_dump(mode="json")),
            "business_map": _receipt(business_id=business_id, kind="business_map", payload=map_model.model_dump(mode="json")),
            "department_intelligence": _receipt(business_id=business_id, kind="department_intelligence", payload=ledger.model_dump(mode="json")),
        },
    }


def _read_container(candidate: str, kind: str) -> Dict[str, Any]:
    try:
        business_id = canonical_business_id(candidate)
        payload = _repo().load_dict(business_id, kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"{kind}_not_found") from exc
    return {"ok": True, "business_id": business_id, "payload": payload, "receipt": _receipt(business_id=business_id, kind=kind, payload=payload)}


def _next_revision(existing: Dict[str, Any] | None, expected: int | None) -> int:
    current = int((existing or {}).get("revision") or 0)
    if expected is not None and current != expected:
        raise HTTPException(status_code=409, detail={"reason": "revision_conflict", "expected": expected, "current": current})
    return current + 1


@router.get("/business-map/{candidate}")
def get_business_map(candidate: str) -> Dict[str, Any]:
    return _read_container(candidate, "business_map")


@router.put("/business-map/{candidate}")
def put_business_map(candidate: str, request: ContainerWriteRequest) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    repository = _repo()
    existing = repository.load_optional_dict(business_id, "business_map")
    payload = _object(request.payload)
    payload.update({"id": f"{business_id}.business_map", "workspace_id": business_id, "kind": "business_map"})
    payload["revision"] = _next_revision(existing, request.expected_revision)
    payload["meta"] = _meta(business_id, "business_map", request.source).model_dump(mode="json")
    model = BusinessMapContainer(**payload)
    repository.save_model(model)
    data = model.model_dump(mode="json")
    return {"ok": True, "business_id": business_id, "payload": data, "receipt": _receipt(business_id=business_id, kind="business_map", payload=data)}


@router.post("/business-map/{candidate}/facts")
def append_business_map_facts(candidate: str, request: BusinessMapFactsRequest) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    repository = _repo()
    try:
        model = repository.load_business_map(business_id)
    except FileNotFoundError:
        model = BusinessMapContainer(
            id=f"{business_id}.business_map",
            workspace_id=business_id,
            meta=_meta(business_id, "business_map", request.source),
        )

    existing_keys = {
        (str(item.get("function") or ""), str(item.get("field") or ""), json.dumps(item.get("value"), sort_keys=True, default=str), str(item.get("source_ref") or ""))
        for item in model.facts if isinstance(item, dict)
    }
    appended = 0
    for incoming in request.facts:
        fact = _object(incoming)
        fact.setdefault("business_id", business_id)
        fact.setdefault("classification", "founder_provided_fact")
        fact.setdefault("confidence", 0.88)
        fact.setdefault("verification_status", "unverified")
        fact.setdefault("observed_at", _now())
        fact.setdefault("created_at", _now())
        key = (str(fact.get("function") or ""), str(fact.get("field") or ""), json.dumps(fact.get("value"), sort_keys=True, default=str), str(fact.get("source_ref") or ""))
        if key in existing_keys:
            continue
        model.facts.append(fact)
        existing_keys.add(key)
        appended += 1

    model.revision = int(model.revision or 0) + (1 if appended else 0)
    model.meta.updated_at = _now()
    model.meta.source = request.source
    repository.save_model(model)
    payload = model.model_dump(mode="json")
    return {"ok": True, "business_id": business_id, "appended": appended, "payload": payload, "receipt": _receipt(business_id=business_id, kind="business_map", payload=payload)}


@router.get("/department-intelligence/{candidate}")
def get_department_intelligence(candidate: str) -> Dict[str, Any]:
    return _read_container(candidate, "department_intelligence")


@router.put("/department-intelligence/{candidate}")
def put_department_intelligence(candidate: str, request: ContainerWriteRequest) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    repository = _repo()
    existing = repository.load_optional_dict(business_id, "department_intelligence")
    payload = _object(request.payload)
    payload["departments"] = {
        **_object((existing or {}).get("departments")),
        **_object(payload.get("departments")),
    }
    payload.update({"id": f"{business_id}.department_intelligence", "workspace_id": business_id, "kind": "department_intelligence"})
    payload["revision"] = _next_revision(existing, request.expected_revision)
    payload["meta"] = _meta(business_id, "department_intelligence", request.source).model_dump(mode="json")
    model = DepartmentIntelligenceContainer(**payload)
    repository.save_model(model)
    data = model.model_dump(mode="json")
    return {"ok": True, "business_id": business_id, "payload": data, "receipt": _receipt(business_id=business_id, kind="department_intelligence", payload=data)}


@router.get("/finance-model/{candidate}")
def get_finance_model(candidate: str) -> Dict[str, Any]:
    return _read_container(candidate, "business_financial_model")


@router.put("/finance-model/{candidate}")
def put_finance_model(candidate: str, request: ContainerWriteRequest) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    repository = _repo()
    existing = repository.load_optional_dict(business_id, "business_financial_model")
    payload = _object(request.payload)
    payload.update({"id": f"{business_id}.business_financial_model", "workspace_id": business_id, "kind": "business_financial_model"})
    payload["revision"] = _next_revision(existing, request.expected_revision)
    payload["meta"] = _meta(business_id, "business_financial_model", request.source).model_dump(mode="json")
    model = BusinessFinancialModelContainer(**payload)
    repository.save_model(model)
    data = model.model_dump(mode="json")
    return {"ok": True, "business_id": business_id, "payload": data, "receipt": _receipt(business_id=business_id, kind="business_financial_model", payload=data)}


@router.post("/finance-artifacts/{candidate}")
async def upload_finance_artifact(
    candidate: str,
    category: str = Form(...),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    try:
        business_id = canonical_business_id(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    category = str(category or "").strip().lower().replace("_", "-")
    allowed = FINANCE_ARTIFACT_CATEGORIES.get(category)
    if allowed is None:
        raise HTTPException(status_code=400, detail="unsupported_finance_artifact_category")

    filename = _safe_filename(file.filename or "upload")
    extension = Path(filename).suffix.lower()
    if extension not in allowed:
        raise HTTPException(status_code=400, detail=f"unsupported_file_type_for_{category}:{extension or 'none'}")

    data = await file.read(MAX_FINANCE_ARTIFACT_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="empty_file")
    if len(data) > MAX_FINANCE_ARTIFACT_BYTES:
        raise HTTPException(status_code=413, detail="finance_artifact_too_large")

    digest = sha256(data).hexdigest()
    artifact_id = f"artifact_{digest[:24]}"
    artifact_dir = AIONBusinessPaths.business_container_dir(business_id) / "finance" / category
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{artifact_id}_{filename}"
    destination = (artifact_dir / stored_name).resolve()
    business_root = AIONBusinessPaths.business_container_dir(business_id).resolve()
    try:
        destination.relative_to(business_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="artifact_path_escape") from exc

    destination.write_bytes(data)
    relative_storage_path = f"business_containers/{business_id}/finance/{category}/{stored_name}"
    target = {
        "business_id": business_id,
        "business_container_id": business_id,
        "sub_container": "finance",
        "artifact_type": "spreadsheet" if extension in {".csv", ".xlsx", ".xls"} else "document",
        "artifact_name": filename,
    }
    provenance = {
        "mission_id": "finance_onboarding",
        "mission_run_id": f"finance_upload_{artifact_id}",
        "step_id": f"finance_{category}_upload",
        "tool_id": "finance_file_ingestion",
        "created_by": "user_upload",
        "uploaded_at": _now(),
    }
    source_payload_hash = _hash({"filename": filename, "size": len(data), "mime_type": file.content_type, "category": category})
    receipt_hash = _hash({"artifact_hash": f"sha256:{digest}", "source_payload_hash": source_payload_hash, "provenance": provenance, "storage_path": relative_storage_path})
    record = {
        "schema_version": "aion.business_container_artifact_record.v1",
        "artifact_id": artifact_id,
        "target": target,
        "provenance": provenance,
        "artifact_hash": f"sha256:{digest}",
        "source_payload_hash": source_payload_hash,
        "receipt_hash": receipt_hash,
        "storage_path": relative_storage_path,
        "storage_state": "committed_to_business_container",
        "session_vfs_only": False,
        "live_side_effects_enabled": False,
        "byte_size": len(data),
        "mime_type": file.content_type or "application/octet-stream",
        "category": category,
    }
    record["replay_locator"] = {
        "business_id": business_id,
        "business_container_id": business_id,
        "department_id": "finance",
        "category": category,
        "storage_path": relative_storage_path,
        "artifact_id": artifact_id,
        "receipt_hash": receipt_hash,
    }
    record["replay_locator_hash"] = _hash(record["replay_locator"])
    receipt_path = artifact_dir / f"{artifact_id}.artifact.json"
    receipt_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

    pointer = _add_finance_file_cabinet_pointer(business_id=business_id, category=category, record=record)
    return {"ok": True, "business_id": business_id, "record": record, "file_cabinet_pointer": pointer}


@router.get("/boardroom-context/{candidate}")
def get_boardroom_context(candidate: str) -> Dict[str, Any]:
    business_id = canonical_business_id(candidate)
    repository = _repo()

    def optional(kind: str) -> Dict[str, Any]:
        return repository.load_optional_dict(business_id, kind) or {}

    business_map = optional("business_map")
    ledger = optional("department_intelligence")
    finance_model = optional("business_financial_model")
    evidence_refs = _list(finance_model.get("evidence_refs"))
    envelope = {
        "schema_version": "aion.boardroom_context_envelope.v1",
        "business_id": business_id,
        "snapshot_id": f"boardroom_context_{business_id}_{int(datetime.now(UTC).timestamp())}",
        "generated_at": _now(),
        "persistent_truth_source": "business_containers",
        "boardroom_projection_only": True,
        "business_identity": optional("business_identity"),
        "business_structure": optional("business_structure"),
        "business_map_projection": {
            "facts": _list(business_map.get("facts")),
            "assumptions": _list(business_map.get("assumptions")),
            "unknowns": _list(business_map.get("unknowns")),
            "conflicts": _list(business_map.get("conflicts")),
            "revision": business_map.get("revision"),
        },
        "function_models": {"finance": finance_model},
        "department_intelligence": _object(ledger.get("departments")),
        "evidence_index": evidence_refs,
        "source_revisions": {
            "business_map": business_map.get("revision"),
            "department_intelligence": ledger.get("revision"),
            "finance": finance_model.get("revision"),
        },
        "execution_boundary": {
            "approval_gated": True,
            "live_external_side_effects_performed": False,
            "raw_model_tool_access_allowed": False,
            "provider_memory_mutation_allowed": False,
        },
    }
    envelope["context_hash"] = _hash(envelope)
    return {"ok": True, "business_id": business_id, "context": envelope}
