from __future__ import annotations

import json
import base64
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.services.aion_mission_mode.boardroom_session_artifacts import (
    commit_boardroom_session_artifact,
    create_file_cabinet_pointer_for_boardroom_session,
)

router = APIRouter(
    prefix="/api/aion/business/workflow-file-cabinet",
    tags=["aion-business-workflow-file-cabinet"],
)


class CabinetArtifactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=240)
    content_type: str = Field(default="application/octet-stream", min_length=1, max_length=160)
    data_base64: str = Field(min_length=1)
    parent_id: str = Field(default="root", min_length=1, max_length=160)
    display_name: str | None = Field(default=None, max_length=240)
    document_type: str = Field(default="original", min_length=1, max_length=120)
    actor_id: str = Field(default="workflow-file-cabinet", min_length=1, max_length=160)


class CabinetGeneratedDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=2_000_000)
    parent_id: str = Field(default="root", min_length=1, max_length=160)
    display_name: str | None = Field(default=None, max_length=240)
    document_type: str = Field(default="generated_document", min_length=1, max_length=120)
    actor_id: str = Field(default="workflow-file-cabinet", min_length=1, max_length=160)


class CabinetMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent_id: str = Field(min_length=1, max_length=160)
    actor_id: str = Field(default="workflow-file-cabinet", min_length=1, max_length=160)


class CabinetTombstoneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="superseded", min_length=1, max_length=500)
    actor_id: str = Field(default="workflow-file-cabinet", min_length=1, max_length=160)


def _registered_workspace_id(workspace_id: str) -> str:
    try:
        return canonical_business_id(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{workspace_id}")
def get_workflow_file_cabinet(workspace_id: str) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.load(_registered_workspace_id(workspace_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}")
def save_workflow_file_cabinet(workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.save(
            _registered_workspace_id(workspace_id), payload
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}/artifacts")
def upload_file_cabinet_artifact(
    workspace_id: str, request: CabinetArtifactRequest,
) -> Dict[str, Any]:
    try:
        data = base64.b64decode(request.data_base64, validate=True)
        if not data:
            raise ValueError("file_cabinet_artifact_empty")
        if len(data) > 25 * 1024 * 1024:
            raise ValueError("file_cabinet_artifact_exceeds_25_mib")
        return {
            "ok": True,
            **WorkflowFileCabinetRepository.add_artifact(
                _registered_workspace_id(workspace_id),
                data=data,
                original_name=request.filename,
                content_type=request.content_type,
                parent_id=request.parent_id,
                display_name=request.display_name,
                document_type=request.document_type,
                actor_id=request.actor_id,
            ),
        }
    except HTTPException:
        raise
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}/generated-documents")
def generate_file_cabinet_document(
    workspace_id: str, request: CabinetGeneratedDocumentRequest,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            **WorkflowFileCabinetRepository.add_artifact(
                _registered_workspace_id(workspace_id),
                data=request.text.encode("utf-8"),
                original_name=request.filename,
                content_type="text/plain; charset=utf-8",
                parent_id=request.parent_id,
                display_name=request.display_name,
                document_type=request.document_type,
                actor_id=request.actor_id,
                generated=True,
            ),
        }
    except HTTPException:
        raise
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}/items/{item_id}/move")
def move_file_cabinet_item(
    workspace_id: str, item_id: str, request: CabinetMoveRequest,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            **WorkflowFileCabinetRepository.move_item(
                _registered_workspace_id(workspace_id), item_id,
                parent_id=request.parent_id, actor_id=request.actor_id,
            ),
        }
    except HTTPException:
        raise
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}/items/{item_id}/tombstone")
def tombstone_file_cabinet_item(
    workspace_id: str, item_id: str, request: CabinetTombstoneRequest,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            **WorkflowFileCabinetRepository.tombstone_item(
                _registered_workspace_id(workspace_id), item_id,
                reason=request.reason, actor_id=request.actor_id,
            ),
        }
    except HTTPException:
        raise
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}/boardroom-sessions")
def save_boardroom_session_artifact(workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the complete Board meeting packet before publishing its cabinet pointer."""
    try:
        safe_workspace_id = _registered_workspace_id(workspace_id)
        business_id = _registered_workspace_id(str(payload.get("business_id") or ""))
        session_id = str(payload.get("session_id") or "").strip()
        session_type = str(payload.get("session_type") or "business_assessment").strip()

        if not session_id:
            raise ValueError("session_id_required")
        if business_id != safe_workspace_id:
            raise ValueError("boardroom_workspace_business_mismatch")

        guardian_enabled = guardian_mode_requested()
        record = commit_boardroom_session_artifact(
            business_id=business_id,
            session_id=session_id,
            session_type=session_type,
            full_session_payload=payload,
            platform_root=None if guardian_enabled else AIONBusinessPaths.ROOT,
        )
        if guardian_enabled:
            encoded = json.dumps(
                payload, indent=2, sort_keys=True, ensure_ascii=False
            ).encode("utf-8")
            stored = WorkflowFileCabinetRepository.put_artifact(
                safe_workspace_id,
                data=encoded,
                original_name=f"{session_id}.json",
                content_type="application/json",
                actor_id="boardroom-session",
                object_id=f"board-{record['artifact_id'][-48:]}",
            )
            record["vault_object_id"] = stored["vault_object_id"]
            record["persisted"] = True
            record["persisted_uri"] = f"guardian://original_files/{stored['vault_object_id']}"
            record["replay_locator"] = {
                **(record.get("replay_locator") or {}),
                "vault_object_id": stored["vault_object_id"],
            }
            record["replay_locator"].pop("storage_path", None)
            from backend.services.aion_mission_mode.department_capability_map import stable_hash
            record["replay_locator_hash"] = stable_hash(record["replay_locator"])
            runtime = configured_business_vault_runtime()
            VaultDomainStore(runtime.guardian, actor_id="boardroom-session").put(
                "file_cabinet.governance",
                workspace_id=safe_workspace_id,
                entity_id=str(record["artifact_id"]),
                payload=record,
                expected_version=None,
                idempotency_key=f"boardroom-session-{record['artifact_id']}",
            )
        return {
            "ok": True,
            "record": record,
            "pointer": create_file_cabinet_pointer_for_boardroom_session(record),
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{workspace_id}/items/{item_id}/preview")
def preview_workflow_file_cabinet_item(workspace_id: str, item_id: str) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.preview(
            _registered_workspace_id(workspace_id), item_id
        )
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
