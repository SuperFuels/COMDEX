from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import WorkflowGlyph
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import WorkflowGlyphRepository


router = APIRouter(prefix="/api/workflow-glyphs", tags=["workflow-glyphs"])


class WorkflowGlyphSaveRequest(BaseModel):
    glyph: Dict[str, Any]
    rebuild_index: bool = True


class WorkflowGlyphCopyRequest(BaseModel):
    source_glyph_code: str
    source_version: Optional[str] = None
    new_glyph_code: Optional[str] = None
    name: Optional[str] = None


def get_glyph_repo() -> WorkflowGlyphRepository:
    return WorkflowGlyphRepository()


def _repo_save(repo: WorkflowGlyphRepository, glyph: WorkflowGlyph, *, rebuild_index: bool = True) -> Dict[str, Any]:
    """
    Compatibility save wrapper.

    The repository contract is the source of truth. Some earlier API drafts
    assumed save(..., rebuild_index=True), but the locked repository currently
    exposes save(glyph). This wrapper keeps the API stable without changing the
    repository contract.
    """
    try:
        return repo.save(glyph, rebuild_index=rebuild_index)  # type: ignore[arg-type]
    except TypeError:
        return repo.save(glyph)


def _repo_get(repo: WorkflowGlyphRepository, glyph_code: str, *, version: Optional[str] = None) -> Optional[WorkflowGlyph]:
    """
    Compatibility lookup wrapper.

    The Glyph Store tests locked repository save/list/search/version behaviour,
    but not a method named get(). The API exposes GET /{glyph_code}, so it
    resolves through whichever repository method exists, then falls back to list.
    """
    for name in ("get", "load", "find"):
        fn = getattr(repo, name, None)
        if not callable(fn):
            continue

        try:
            if version is not None:
                glyph = fn(glyph_code, version=version)
            else:
                glyph = fn(glyph_code)
            if glyph is not None:
                return glyph
        except TypeError:
            try:
                glyph = fn(glyph_code)
                if glyph is not None:
                    if version is None or getattr(glyph, "glyph_version", None) == version:
                        return glyph
            except Exception:
                pass
        except FileNotFoundError:
            return None

    for name in ("require",):
        fn = getattr(repo, name, None)
        if not callable(fn):
            continue

        try:
            glyph = fn(glyph_code, version=version) if version is not None else fn(glyph_code)
            if glyph is not None:
                return glyph
        except TypeError:
            try:
                glyph = fn(glyph_code)
                if glyph is not None:
                    if version is None or getattr(glyph, "glyph_version", None) == version:
                        return glyph
            except Exception:
                pass
        except FileNotFoundError:
            return None

    for name in ("latest_version", "latest", "get_latest"):
        fn = getattr(repo, name, None)
        if not callable(fn):
            continue

        if version is not None:
            continue

        try:
            glyph = fn(glyph_code)
            if glyph is not None:
                return glyph
        except Exception:
            pass

    try:
        glyphs = repo.list()
    except Exception:
        glyphs = []

    matches = [
        glyph for glyph in glyphs
        if str(getattr(glyph, "glyph_code", "")).lower() == str(glyph_code).lower()
    ]

    if version is not None:
        matches = [
            glyph for glyph in matches
            if str(getattr(glyph, "glyph_version", "")).lower() == str(version).lower()
        ]

    if not matches:
        return None

    return sorted(
        matches,
        key=lambda glyph: str(getattr(glyph, "glyph_version", "")),
        reverse=True,
    )[0]


def _glyph_prefix(code: str) -> str:
    text = str(code or "WD").strip().upper()
    if "-" in text:
        text = text.split("-", 1)[0]
    text = "".join(ch for ch in text if ch.isalnum())
    return (text or "WD")[:4]


def _next_my_glyph_code(repo: WorkflowGlyphRepository, source_code: str) -> str:
    prefix = _glyph_prefix(source_code)
    existing = {
        str(getattr(g, "glyph_code", "")).upper()
        for g in repo.list()
    }

    for number in range(9001, 10000):
        candidate = f"{prefix}-{number}"
        if candidate not in existing:
            return candidate

    raise RuntimeError(f"no_available_glyph_code_for_prefix:{prefix}")


@router.get("")
def list_glyphs(
    scope: Optional[str] = Query(default=None),
    callable_only: bool = Query(default=False),
) -> Dict[str, Any]:
    repo = get_glyph_repo()
    glyphs = repo.list(scope=scope, callable_only=callable_only)

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.list.v1",
        "count": len(glyphs),
        "scope": scope,
        "callable_only": callable_only,
        "glyphs": [g.to_dict() for g in glyphs],
    }


@router.get("/search")
def search_glyphs(
    q: str = Query(default=""),
    scope: Optional[str] = Query(default=None),
    callable_only: bool = Query(default=False),
) -> Dict[str, Any]:
    repo = get_glyph_repo()
    glyphs = repo.search(q, scope=scope, callable_only=callable_only)

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.search.v1",
        "query": q,
        "count": len(glyphs),
        "scope": scope,
        "callable_only": callable_only,
        "glyphs": [g.to_dict() for g in glyphs],
    }


@router.post("/copy")
def copy_glyph_to_my_glyphs(payload: WorkflowGlyphCopyRequest) -> Dict[str, Any]:
    repo = get_glyph_repo()

    source = _repo_get(
        repo,
        payload.source_glyph_code,
        version=payload.source_version,
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"source_glyph_not_found:{payload.source_glyph_code}",
        )

    if source.scope != "universal":
        raise HTTPException(
            status_code=400,
            detail=f"source_glyph_not_universal:{source.glyph_code}",
        )

    new_code = payload.new_glyph_code or _next_my_glyph_code(repo, source.glyph_code)

    copied = WorkflowGlyph.from_dict(source.to_dict())
    copied.glyph_code = new_code
    copied.glyph_id = f"glyph.{new_code.lower()}.{copied.glyph_version}"
    copied.name = payload.name or f"{source.name} Copy"
    copied.scope = "my"
    copied.source_glyph_code = source.glyph_code

    copied.meta = {}
    copied.finalize()

    saved = _repo_save(repo, copied, rebuild_index=True)

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.copy.v1",
        "source_glyph_code": source.glyph_code,
        "copied_glyph_code": copied.glyph_code,
        "saved": saved,
        "glyph": copied.to_dict(),
    }


@router.get("/{glyph_code}")
def get_glyph(
    glyph_code: str,
    version: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    repo = get_glyph_repo()

    glyph = _repo_get(repo, glyph_code, version=version)
    if glyph is None:
        raise HTTPException(status_code=404, detail=f"glyph_not_found:{glyph_code}")

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.get.v1",
        "glyph_code": glyph_code,
        "version": version or glyph.glyph_version,
        "glyph": glyph.to_dict(),
    }


@router.get("/{glyph_code}/versions/{version}")
def get_glyph_version(glyph_code: str, version: str) -> Dict[str, Any]:
    repo = get_glyph_repo()

    glyph = _repo_get(repo, glyph_code, version=version)
    if glyph is None:
        raise HTTPException(status_code=404, detail=f"glyph_version_not_found:{glyph_code}:{version}")

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.get_version.v1",
        "glyph_code": glyph_code,
        "version": version,
        "glyph": glyph.to_dict(),
    }


@router.post("")
def save_glyph(payload: WorkflowGlyphSaveRequest) -> Dict[str, Any]:
    repo = get_glyph_repo()

    try:
        glyph = WorkflowGlyph.from_dict(payload.glyph)
        saved = _repo_save(repo, glyph, rebuild_index=payload.rebuild_index)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"glyph_save_failed:{type(exc).__name__}:{exc}",
        ) from exc

    return {
        "ok": True,
        "schema_version": "aion.workflow_glyph_api.save.v1",
        "saved": saved,
        "glyph": glyph.to_dict(),
    }
