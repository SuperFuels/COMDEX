from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api/aion/business",
    tags=["aion-business-browser-skills"],
)

BASE = Path(".runtime/AION_BUSINESS")


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


class BrowserSkillPayload(BaseModel):
    skill: Dict[str, Any] = Field(default_factory=dict)


class BrowserChainPayload(BaseModel):
    chain: Dict[str, Any] = Field(default_factory=dict)


@router.get("/browser-skills/{workspace_id}")
def list_browser_skills(workspace_id: str) -> Dict[str, Any]:
    items = _list_json(_skill_dir(workspace_id))
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

    saved = _write_json(_skill_path(workspace_id, skill_id), skill)

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "skill_id": skill_id,
        "item": saved,
    }


@router.get("/browser-skills/{workspace_id}/{skill_id}")
def get_browser_skill(workspace_id: str, skill_id: str) -> Dict[str, Any]:
    item = _read_json(_skill_path(workspace_id, skill_id))
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "skill_id": skill_id,
        "item": item,
    }


@router.delete("/browser-skills/{workspace_id}/{skill_id}")
def delete_browser_skill(workspace_id: str, skill_id: str) -> Dict[str, Any]:
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
    items = _list_json(_chain_dir(workspace_id))
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

    saved = _write_json(_chain_path(workspace_id, chain_id), chain)

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "item": saved,
    }


@router.get("/browser-chains/{workspace_id}/{chain_id}")
def get_browser_chain(workspace_id: str, chain_id: str) -> Dict[str, Any]:
    item = _read_json(_chain_path(workspace_id, chain_id))
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "item": item,
    }


@router.delete("/browser-chains/{workspace_id}/{chain_id}")
def delete_browser_chain(workspace_id: str, chain_id: str) -> Dict[str, Any]:
    path = _chain_path(workspace_id, chain_id)

    if path.exists():
        path.unlink()

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "chain_id": chain_id,
        "deleted": True,
    }
