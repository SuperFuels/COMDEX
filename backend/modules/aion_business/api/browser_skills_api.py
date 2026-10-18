from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


router = APIRouter(
    prefix="/api/aion/business",
    tags=["aion-business-browser-skills"],
)

BASE = Path(".runtime/AION_BUSINESS")
DOMAIN_ID = "train_agent.automations"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_id(value: str, fallback: str) -> str:
    raw = str(value or "").strip() or fallback
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", raw).strip("_")
    return safe or fallback


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {path.name}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"JSONDecodeError in {path}: {exc}",
        ) from exc


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def _list_json(folder: Path) -> List[Dict[str, Any]]:
    if not folder.exists():
        return []

    items: List[Dict[str, Any]] = []

    for path in sorted(folder.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            # Skip corrupt individual runtime asset but do not break the whole UI.
            continue

    return items


def _skill_dir(workspace_id: str) -> Path:
    return BASE / "browser_skills" / _safe_id(workspace_id, "default")


def _chain_dir(workspace_id: str) -> Path:
    return BASE / "browser_chains" / _safe_id(workspace_id, "default")


def _skill_path(workspace_id: str, skill_id: str) -> Path:
    return _skill_dir(workspace_id) / f"{_safe_id(skill_id, 'browser_skill')}.json"


def _chain_path(workspace_id: str, chain_id: str) -> Path:
    return _chain_dir(workspace_id) / f"{_safe_id(chain_id, 'browser_chain')}.json"


def _guardian_store() -> VaultDomainStore | None:
    if not guardian_mode_requested():
        return None
    return VaultDomainStore(
        configured_business_vault_runtime().guardian,
        actor_id="browser-skills-api",
    )


def _entity(kind: str, record_id: str) -> str:
    return f"browser_automation/{kind}/{_safe_id(record_id, kind)}"


def _guardian_save(
    store: VaultDomainStore, workspace_id: str, kind: str, record_id: str,
    payload: Dict[str, Any], *, idempotency_key: str | None = None,
) -> Dict[str, Any]:
    workspace = canonical_business_id(workspace_id)
    entity_id = _entity(kind, record_id)
    current = store.get_optional(DOMAIN_ID, workspace_id=workspace, entity_id=entity_id)
    store.put(
        DOMAIN_ID, workspace_id=workspace, entity_id=entity_id, payload=payload,
        expected_version=int(current["version"]) if current else None,
        idempotency_key=idempotency_key,
    )
    return payload


def _import_legacy(
    store: VaultDomainStore, workspace_id: str, kind: str, folder: Path,
) -> None:
    workspace = canonical_business_id(workspace_id)
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record_id = _safe_id(
            payload.get("skill_id") or payload.get("chain_id") or payload.get("id") or path.stem,
            kind,
        )
        entity_id = _entity(kind, record_id)
        if store.get_optional(DOMAIN_ID, workspace_id=workspace, entity_id=entity_id) is None:
            _guardian_save(
                store, workspace, kind, record_id,
                {**payload, "legacy_source_retained": True},
                idempotency_key=f"browser-automation-import-{kind}-{record_id}",
            )


def _guardian_list(
    store: VaultDomainStore, workspace_id: str, kind: str, folder: Path,
) -> List[Dict[str, Any]]:
    workspace = canonical_business_id(workspace_id)
    _import_legacy(store, workspace, kind, folder)
    prefix = f"browser_automation/{kind}/"
    return [
        dict(row["payload"])
        for row in store.list(DOMAIN_ID, workspace_id=workspace)
        if str(row.get("entity_id") or "").startswith(prefix)
        and not bool((row.get("payload") or {}).get("__deleted__"))
    ]


class BrowserSkillPayload(BaseModel):
    skill: Dict[str, Any] = Field(default_factory=dict)


class BrowserChainPayload(BaseModel):
    chain: Dict[str, Any] = Field(default_factory=dict)


@router.get("/browser-skills/{workspace_id}")
def list_browser_skills(workspace_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    items = (
        _guardian_list(store, workspace_id, "skills", _skill_dir(workspace_id))
        if store else _list_json(_skill_dir(workspace_id))
    )
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "count": len(items),
        "items": items,
    }


@router.post("/browser-skills/{workspace_id}")
def save_browser_skill(workspace_id: str, request: BrowserSkillPayload) -> Dict[str, Any]:
    skill = dict(request.skill or {})

    skill_id = _safe_id(
        skill.get("skill_id") or skill.get("id") or f"browser_skill_{int(datetime.now().timestamp())}",
        "browser_skill",
    )

    now = _utc_now()

    skill.setdefault("schema_version", "aion.browser_skill.v1")
    skill["skill_id"] = skill_id
    skill["workspace_id"] = workspace_id
    skill.setdefault("status", "draft")
    skill.setdefault("created_at", now)
    skill["updated_at"] = now

    store = _guardian_store()
    saved = (
        _guardian_save(store, workspace_id, "skills", skill_id, skill)
        if store else _write_json(_skill_path(workspace_id, skill_id), skill)
    )

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "skill_id": skill_id,
        "item": saved,
    }


@router.get("/browser-skills/{workspace_id}/{skill_id}")
def get_browser_skill(workspace_id: str, skill_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    if store:
        _import_legacy(store, workspace_id, "skills", _skill_dir(workspace_id))
        row = store.get_optional(
            DOMAIN_ID, workspace_id=canonical_business_id(workspace_id),
            entity_id=_entity("skills", skill_id),
        )
        if row is None or bool((row.get("payload") or {}).get("__deleted__")):
            raise HTTPException(status_code=404, detail="Browser skill not found")
        item = dict(row["payload"])
    else:
        item = _read_json(_skill_path(workspace_id, skill_id))
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "skill_id": skill_id,
        "item": item,
    }


@router.delete("/browser-skills/{workspace_id}/{skill_id}")
def delete_browser_skill(workspace_id: str, skill_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    if store:
        _guardian_save(
            store, workspace_id, "skills", skill_id,
            {"__deleted__": True, "skill_id": skill_id, "workspace_id": workspace_id,
             "deleted_at": _utc_now()},
        )
        return {"ok": True, "workspace_id": workspace_id, "skill_id": skill_id, "deleted": True}
    path = _skill_path(workspace_id, skill_id)

    if path.exists():
        path.unlink()

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "skill_id": skill_id,
        "deleted": True,
    }


@router.get("/browser-chains/{workspace_id}")
def list_browser_chains(workspace_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    items = (
        _guardian_list(store, workspace_id, "chains", _chain_dir(workspace_id))
        if store else _list_json(_chain_dir(workspace_id))
    )
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "count": len(items),
        "items": items,
    }


@router.post("/browser-chains/{workspace_id}")
def save_browser_chain(workspace_id: str, request: BrowserChainPayload) -> Dict[str, Any]:
    chain = dict(request.chain or {})

    chain_id = _safe_id(
        chain.get("chain_id") or chain.get("id") or f"browser_chain_{int(datetime.now().timestamp())}",
        "browser_chain",
    )

    now = _utc_now()

    chain.setdefault("schema_version", "aion.browser_skill_chain.v1")
    chain["chain_id"] = chain_id
    chain["workspace_id"] = workspace_id
    chain.setdefault("status", "draft")
    chain.setdefault("created_at", now)
    chain["updated_at"] = now

    store = _guardian_store()
    saved = (
        _guardian_save(store, workspace_id, "chains", chain_id, chain)
        if store else _write_json(_chain_path(workspace_id, chain_id), chain)
    )

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "item": saved,
    }


@router.get("/browser-chains/{workspace_id}/{chain_id}")
def get_browser_chain(workspace_id: str, chain_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    if store:
        _import_legacy(store, workspace_id, "chains", _chain_dir(workspace_id))
        row = store.get_optional(
            DOMAIN_ID, workspace_id=canonical_business_id(workspace_id),
            entity_id=_entity("chains", chain_id),
        )
        if row is None or bool((row.get("payload") or {}).get("__deleted__")):
            raise HTTPException(status_code=404, detail="Browser chain not found")
        item = dict(row["payload"])
    else:
        item = _read_json(_chain_path(workspace_id, chain_id))
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "item": item,
    }


@router.delete("/browser-chains/{workspace_id}/{chain_id}")
def delete_browser_chain(workspace_id: str, chain_id: str) -> Dict[str, Any]:
    store = _guardian_store()
    if store:
        _guardian_save(
            store, workspace_id, "chains", chain_id,
            {"__deleted__": True, "chain_id": chain_id, "workspace_id": workspace_id,
             "deleted_at": _utc_now()},
        )
        return {"ok": True, "workspace_id": workspace_id, "chain_id": chain_id, "deleted": True}
    path = _chain_path(workspace_id, chain_id)

    if path.exists():
        path.unlink()

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "deleted": True,
    }
