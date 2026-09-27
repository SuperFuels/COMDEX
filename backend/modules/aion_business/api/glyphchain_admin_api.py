"""Signed-desktop administration surface for explicit GlyphChain participation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    AionFlowSessionAuthority,
    VerifiedAionFlowSession,
)
from backend.modules.p2p.network_participation import (
    NetworkParticipationError,
    NetworkParticipationStore,
    participation_from_env,
)
from backend.modules.p2p.network_identity import NetworkIdentityError, NetworkIdentityStore
from backend.modules.p2p.network_health import NetworkHealthStore, build_health_snapshot
from backend.modules.p2p.peer_store import get_peer_by_node_id, list_peers, peer_store_status
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519
from backend.modules.p2p.transport_http import post_file
from backend.modules.chain_sim.chain_sim_ledger import (
    install_verified_ledger_database,
    persist_database_path,
    persist_get_checkpoint,
    persist_ledger_storage_status,
)
from backend.modules.chain_sim.ledger_snapshot import (
    LedgerSnapshotError,
    SNAPSHOT_MEDIA_TYPE,
    export_ledger_snapshot,
    verify_ledger_snapshot,
)
from backend.modules.chain_sim.ledger_storage import configured_ledger_limit_bytes
from backend.modules.chain_sim.ledger_pruning import LedgerPruningError, compact_ledger_copy
from backend.modules.consensus.finality_checkpoint import (
    FinalityCheckpointError,
    load_trusted_checkpoint_from_env,
    write_public_checkpoint,
)
from backend.modules.consensus.protocol_upgrade import (
    ProtocolUpgradeError,
    ProtocolUpgradeStore,
)
from backend.modules.consensus.validator_governance import (
    ValidatorGovernanceError,
    ValidatorGovernanceStore,
)


router = APIRouter(
    prefix="/api/aion/business/glyphchain-admin",
    tags=["aion-glyphchain-admin"],
)
_authority = AionFlowSessionAuthority()


async def require_signed_desktop_admin(request: Request) -> VerifiedAionFlowSession:
    """Require possession of the enrolled desktop session for every operation."""
    staged_root: Path | None = None
    try:
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        if request.url.path in {
            "/api/aion/business/glyphchain-admin/snapshot/verify",
            "/api/aion/business/glyphchain-admin/snapshot/import",
        }:
            staged_root, snapshot, body_hash = await _stage_signed_snapshot(request)
            request.state.glyphchain_snapshot_upload = (staged_root, snapshot)
            return _authority.verify_body_hash(
                method=request.method,
                target=target,
                body_hash=body_hash,
                headers=request.headers,
            )
        body = await request.body()
        return _authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc:
        if staged_root is not None:
            shutil.rmtree(staged_root, ignore_errors=True)
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        if staged_root is not None:
            shutil.rmtree(staged_root, ignore_errors=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _stage_signed_snapshot(request: Request) -> tuple[Path, Path, str]:
    content_type = str(request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != SNAPSHOT_MEDIA_TYPE:
        raise HTTPException(status_code=415, detail="glyphchain_snapshot_media_type_required")
    maximum = configured_ledger_limit_bytes() + (6 * 1024 * 1024)
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > maximum:
        raise HTTPException(status_code=413, detail="glyphchain_snapshot_archive_too_large")

    root = Path(tempfile.mkdtemp(prefix="glyphchain-snapshot-upload-"))
    os.chmod(root, 0o700)
    snapshot = root / "received.glyphchain-snapshot"
    digest = hashlib.sha256()
    total = 0
    try:
        with snapshot.open("xb") as stream:
            async for chunk in request.stream():
                if not chunk:
                    continue
                total += len(chunk)
                if total > maximum:
                    raise HTTPException(status_code=413, detail="glyphchain_snapshot_archive_too_large")
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if total <= 0:
            raise HTTPException(status_code=413, detail="glyphchain_snapshot_archive_too_large")
        os.chmod(snapshot, 0o600)
        return root, snapshot, digest.hexdigest()
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def participation_store() -> NetworkParticipationStore:
    configured = str(os.getenv("GLYPHCHAIN_PARTICIPATION_DIR", "") or "").strip()
    if configured:
        root = Path(configured)
    else:
        state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
        root = state_root / "participation"
    return NetworkParticipationStore(root)


def network_identity_store() -> NetworkIdentityStore:
    configured = str(os.getenv("GLYPHCHAIN_NETWORK_KEY_DIR", "") or "").strip()
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    root = Path(configured) if configured else state_root / "network-identity"
    chain_id = str(os.getenv("GLYPHCHAIN_CHAIN_ID", "") or os.getenv("CHAIN_ID", "") or "glyphchain-dev")
    node_id = str(os.getenv("GLYPHCHAIN_NODE_ID", "") or os.getenv("P2P_NODE_ID", "") or "dev-node")
    return NetworkIdentityStore(root, chain_id=chain_id, node_id=node_id)


def network_health_store() -> NetworkHealthStore:
    configured = str(os.getenv("GLYPHCHAIN_HEALTH_DIR", "") or "").strip()
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    return NetworkHealthStore(Path(configured) if configured else state_root / "health")


def protocol_upgrade_store() -> ProtocolUpgradeStore:
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    configured = str(os.getenv("GLYPHCHAIN_PROTOCOL_UPGRADE_DIR", "") or "").strip()
    chain_id = str(os.getenv("GLYPHCHAIN_CHAIN_ID", "") or os.getenv("CHAIN_ID", "") or "glyphchain-dev")
    node_id = str(os.getenv("GLYPHCHAIN_NODE_ID", "") or os.getenv("P2P_NODE_ID", "") or "dev-node")
    return ProtocolUpgradeStore(Path(configured) if configured else state_root / "protocol-upgrade", chain_id=chain_id, node_id=node_id)


def validator_governance_store() -> ValidatorGovernanceStore:
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    configured = str(os.getenv("GLYPHCHAIN_VALIDATOR_GOVERNANCE_DIR", "") or "").strip()
    return ValidatorGovernanceStore(
        Path(configured) if configured else state_root / "validator-governance",
        current_checkpoint=_trusted_checkpoint().value,
    )


class ConfigureParticipationInput(BaseModel):
    role: str = Field(min_length=1, max_length=20)
    confirmation: str = Field(default="", max_length=80)
    storage_limit_bytes: int = Field(default=512 * 1024 * 1024, ge=64 * 1024 * 1024)
    public_connectivity_acknowledged: bool = False
    availability_acknowledged: bool = False
    key_custody_acknowledged: bool = False
    governance_approval_id: str = Field(default="", max_length=240)
    validator_set_checkpoint_id: str = Field(default="", max_length=240)


class DisableParticipationInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: str = Field(min_length=1, max_length=80)


class RotateNetworkIdentityInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: str = Field(min_length=1, max_length=80)


class NetworkRecoveryInput(BaseModel):
    password: str = Field(min_length=12, max_length=1024)


class NetworkRecoveryImportInput(NetworkRecoveryInput):
    recovery_bundle: dict[str, Any]
    acknowledge_device_key_restore: bool = False


class NetworkHealthHistoryInput(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)


class PartitionSafetyHaltClearInput(BaseModel):
    halt_id: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: str = Field(min_length=1, max_length=100)


class ProtocolUpgradeScheduleInput(BaseModel):
    target_version: int = Field(ge=2, le=1_000_000)
    activation_height: int = Field(ge=1)
    release_manifest_sha256: str = Field(min_length=64, max_length=64)
    validator_checkpoint_id: str = Field(min_length=1, max_length=240)
    governance_approval_id: str = Field(min_length=1, max_length=240)
    confirmation: str = Field(min_length=1, max_length=100)


class ProtocolUpgradeCancelInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: str = Field(min_length=1, max_length=100)


class ProtocolUpgradeCompleteInput(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)


class ValidatorGovernanceProposalInput(BaseModel):
    next_checkpoint: dict[str, Any]
    action: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=2000)
    governance_reference: str = Field(min_length=1, max_length=240)
    confirmation: str = Field(min_length=1, max_length=100)


class ValidatorGovernanceApprovalInput(BaseModel):
    validator_id: str = Field(min_length=1, max_length=240)
    signature_base64: str = Field(min_length=1, max_length=1024)


class ValidatorGovernanceFinalizeInput(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)


class SnapshotPeerSyncInput(BaseModel):
    peer_node_id: str = Field(min_length=1, max_length=240)
    confirmation: str = Field(min_length=1, max_length=80)


class PruneLedgerInput(BaseModel):
    confirmation: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)


def _call(operation):
    try:
        return operation()
    except NetworkParticipationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _identity_call(operation):
    try:
        return operation()
    except (NetworkIdentityError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _trusted_checkpoint():
    try:
        checkpoint = load_trusted_checkpoint_from_env()
    except (FinalityCheckpointError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_trusted_checkpoint_unavailable:{exc}") from exc
    if checkpoint is None:
        raise HTTPException(status_code=503, detail="glyphchain_trusted_checkpoint_required")
    return checkpoint


def _snapshot_call(operation):
    try:
        return operation()
    except LedgerSnapshotError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_snapshot_unavailable:{exc}") from exc


def _pruning_call(operation):
    try:
        return operation()
    except LedgerPruningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_pruning_unavailable:{exc}") from exc


def _pruning_archive_root() -> Path:
    configured = str(os.getenv("GLYPHCHAIN_PRUNING_ARCHIVE_DIR", "") or "").strip()
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    root = Path(configured).expanduser() if configured else state_root / "pruning-archives"
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


@router.post("/status")
def participation_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    store = participation_store()
    return {
        "ok": True,
        "workspace_id": session.workspace_id,
        "operator_id": session.person_id,
        "participation": _call(store.status),
        "audit_chain_valid": _call(store.verify_audit_chain),
        "authenticated_by": "signed_desktop_session",
    }


@router.post("/configure")
def configure_participation(
    payload: ConfigureParticipationInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    state = _call(lambda: participation_store().configure(
        role=payload.role,
        operator_id=session.person_id,
        confirmation=payload.confirmation,
        storage_limit_bytes=payload.storage_limit_bytes,
        public_connectivity_acknowledged=payload.public_connectivity_acknowledged,
        availability_acknowledged=payload.availability_acknowledged,
        key_custody_acknowledged=payload.key_custody_acknowledged,
        governance_approval_id=payload.governance_approval_id,
        validator_set_checkpoint_id=payload.validator_set_checkpoint_id,
    ))
    return {"ok": True, "participation": state, "restart_required": True}


@router.post("/disable")
def disable_participation(
    payload: DisableParticipationInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    if payload.confirmation != "DISABLE GLYPHCHAIN PARTICIPATION":
        raise HTTPException(status_code=422, detail="network_participation_disable_confirmation_required")
    state = _call(lambda: participation_store().disable_elevated_participation(
        operator_id=session.person_id,
        reason=payload.reason,
    ))
    return {"ok": True, "participation": state, "restart_required": True}


@router.post("/network-identity/status")
def network_identity_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    store = network_identity_store()
    return {"ok": True, "workspace_id": session.workspace_id,
            "identity": _identity_call(store.identity),
            "rotation_chain_valid": _identity_call(store.verify_rotation_chain)}


@router.post("/network-identity/rotate")
def rotate_network_identity(
    payload: RotateNetworkIdentityInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    return {"ok": True, **_identity_call(lambda: network_identity_store().rotate(
        actor_id=session.person_id, reason=payload.reason, confirmation=payload.confirmation,
    ))}


@router.post("/network-identity/recovery/export")
def export_network_identity_recovery(
    payload: NetworkRecoveryInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    return {"ok": True, "workspace_id": session.workspace_id,
            "recovery_bundle": _identity_call(lambda: network_identity_store().export_recovery_bundle(payload.password))}


@router.post("/network-identity/recovery/import")
def import_network_identity_recovery(
    payload: NetworkRecoveryImportInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    if not payload.acknowledge_device_key_restore:
        raise HTTPException(status_code=422, detail="acknowledge_device_key_restore_required")
    return {"ok": True, **_identity_call(lambda: network_identity_store().import_recovery_bundle(
        payload.recovery_bundle, payload.password,
    ))}


@router.post("/health/snapshot")
def capture_network_health(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        from backend.modules.p2p.ingress import get_lanes

        store = network_health_store()
        previous_records = store.history(limit=1)
        storage = peer_store_status()
        snapshot = build_health_snapshot(
            consensus=get_engine().status(),
            peers=list_peers(),
            peer_limit=int(storage.get("peer_limit") or 0),
            ingress=get_lanes().snapshot(),
            ledger_storage=persist_ledger_storage_status(),
            previous=previous_records[-1] if previous_records else None,
        )
        saved = store.append(snapshot)
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "health": saved,
            "history_chain_valid": store.verify(),
            "authenticated_by": "signed_desktop_session",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_health_unavailable:{type(exc).__name__}") from exc


@router.post("/partition-recovery/status")
def partition_recovery_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "partition_recovery": get_engine().status().get("partition_recovery"),
            "authenticated_by": "signed_desktop_session",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_partition_recovery_unavailable:{type(exc).__name__}") from exc


@router.post("/partition-recovery/clear-safety-halt")
def clear_partition_recovery_safety_halt(
    payload: PartitionSafetyHaltClearInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        state = get_engine().clear_partition_safety_halt(
            halt_id=payload.halt_id,
            operator_id=session.person_id,
            reason=payload.reason,
            confirmation=payload.confirmation,
        )
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "partition_recovery": state,
            "authenticated_by": "signed_desktop_session",
            "consensus_resumes_after_next_trusted_peer_assessment": True,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_partition_recovery_unavailable:{type(exc).__name__}") from exc


@router.post("/protocol-upgrade/status")
def protocol_upgrade_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "protocol_upgrade": get_engine().status().get("protocol_upgrade"),
            "authenticated_by": "signed_desktop_session",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_protocol_upgrade_unavailable:{type(exc).__name__}") from exc


@router.post("/protocol-upgrade/schedule")
def schedule_protocol_upgrade(
    payload: ProtocolUpgradeScheduleInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        engine = get_engine()
        checkpoint = _trusted_checkpoint()
        if payload.validator_checkpoint_id != checkpoint.checkpoint_id:
            raise HTTPException(status_code=422, detail="protocol upgrade checkpoint does not match trusted checkpoint")
        finalized = int(engine.status().get("finalized_height") or 0)
        state = protocol_upgrade_store().schedule(
            target_version=payload.target_version,
            activation_height=payload.activation_height,
            release_manifest_sha256=payload.release_manifest_sha256,
            validator_checkpoint_id=payload.validator_checkpoint_id,
            governance_approval_id=payload.governance_approval_id,
            operator_id=session.person_id,
            confirmation=payload.confirmation,
            current_finalized_height=finalized,
        )
        return {"ok": True, "protocol_upgrade": state, "signed_hello_refresh_required": True}
    except HTTPException:
        raise
    except ProtocolUpgradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_protocol_upgrade_unavailable:{type(exc).__name__}") from exc


@router.post("/protocol-upgrade/cancel")
def cancel_protocol_upgrade(
    payload: ProtocolUpgradeCancelInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        finalized = int(get_engine().status().get("finalized_height") or 0)
        state = protocol_upgrade_store().cancel(
            operator_id=session.person_id,
            reason=payload.reason,
            confirmation=payload.confirmation,
            current_finalized_height=finalized,
        )
        return {"ok": True, "protocol_upgrade": state, "signed_hello_refresh_required": True}
    except ProtocolUpgradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_protocol_upgrade_unavailable:{type(exc).__name__}") from exc


@router.post("/protocol-upgrade/complete")
def complete_protocol_upgrade(
    payload: ProtocolUpgradeCompleteInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        finalized = int(get_engine().status().get("finalized_height") or 0)
        state = protocol_upgrade_store().complete(
            operator_id=session.person_id,
            confirmation=payload.confirmation,
            current_finalized_height=finalized,
        )
        return {"ok": True, "protocol_upgrade": state, "signed_hello_refresh_required": True}
    except ProtocolUpgradeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_protocol_upgrade_unavailable:{type(exc).__name__}") from exc


@router.post("/validator-governance/status")
def validator_governance_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        return {"ok": True, "workspace_id": session.workspace_id,
                "validator_governance": validator_governance_store().status(),
                "authenticated_by": "signed_desktop_session"}
    except (ValidatorGovernanceError, FinalityCheckpointError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validator-governance/propose")
def propose_validator_governance(
    payload: ValidatorGovernanceProposalInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        finalized = int(get_engine().status().get("finalized_height") or 0)
        state = validator_governance_store().propose(
            next_checkpoint=payload.next_checkpoint, action=payload.action,
            reason=payload.reason, governance_reference=payload.governance_reference,
            operator_id=session.person_id, confirmation=payload.confirmation,
            current_finalized_height=finalized,
        )
        return {"ok": True, "validator_governance": state}
    except ValidatorGovernanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validator-governance/sign-local-approval")
def sign_local_validator_governance_approval(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        from backend.modules.consensus.engine import get_engine
        store = validator_governance_store(); state = store.status()
        proposal = state.get("proposal")
        if not isinstance(proposal, dict):
            raise ValidatorGovernanceError("no validator governance proposal is active")
        approval = get_engine().sign_validator_governance_approval(proposal)
        state = store.add_approval(approval, operator_id=session.person_id)
        return {"ok": True, "approval": approval, "validator_governance": state}
    except (ValidatorGovernanceError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validator-governance/add-approval")
def add_validator_governance_approval(
    payload: ValidatorGovernanceApprovalInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        state = validator_governance_store().add_approval(
            payload.model_dump(), operator_id=session.person_id,
        )
        return {"ok": True, "validator_governance": state}
    except ValidatorGovernanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validator-governance/finalize")
def finalize_validator_governance(
    payload: ValidatorGovernanceFinalizeInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        result = validator_governance_store().finalize(
            operator_id=session.person_id, confirmation=payload.confirmation,
        )
        root = validator_governance_store().root
        checkpoint_path = write_public_checkpoint(result["next_checkpoint"], root / "next-validator-checkpoint.json")
        proof_path = root / "validator-transition-proof.json"
        temporary = proof_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(result["transition_proof"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o644); os.replace(temporary, proof_path)
        return {"ok": True, "validator_governance": {
            key: value for key, value in result.items() if key not in {"transition_proof", "next_checkpoint"}
        }, "checkpoint_path": str(checkpoint_path), "transition_proof_path": str(proof_path),
            "restart_required_at_height": result["restart_required_at_height"]}
    except ValidatorGovernanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/storage/status")
def glyphchain_storage_status(
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    try:
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "ledger_storage": persist_ledger_storage_status(),
            "peer_storage": peer_store_status(),
            "authenticated_by": "signed_desktop_session",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_storage_status_unavailable:{type(exc).__name__}") from exc


@router.post("/snapshot/export")
def export_snapshot(
    background_tasks: BackgroundTasks,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
):
    from backend.modules.consensus.engine import get_engine

    database = persist_database_path()
    ledger_checkpoint = persist_get_checkpoint() or {}
    height = int(ledger_checkpoint.get("last_height") or 0)
    if database is None or height <= 0:
        raise HTTPException(status_code=409, detail="glyphchain_snapshot_checkpoint_unavailable")
    trusted = _trusted_checkpoint()
    engine = get_engine()
    receipt = engine.finality_receipt(height=height)
    certificate = receipt.get("quorum_finality_certificate") if isinstance(receipt, dict) else None
    if not isinstance(certificate, dict):
        raise HTTPException(status_code=409, detail="glyphchain_snapshot_finality_certificate_unavailable")
    temporary_root = Path(tempfile.mkdtemp(prefix="glyphchain-snapshot-api-"))
    output = temporary_root / f"glyphchain-{height}.glyphchain-snapshot"
    try:
        manifest = _snapshot_call(lambda: export_ledger_snapshot(
            database_path=database,
            output_path=output,
            chain_id=engine.chain_id,
            network_id=engine.network_id,
            finality_certificate=certificate,
            validator_checkpoint=trusted.value,
        ))
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    background_tasks.add_task(shutil.rmtree, temporary_root, True)
    return FileResponse(
        output,
        media_type=SNAPSHOT_MEDIA_TYPE,
        filename=f"glyphchain-{manifest['snapshot_id'][:16]}-h{height}.glyphchain-snapshot",
        background=background_tasks,
        headers={"X-GlyphChain-Snapshot-Id": str(manifest["snapshot_id"])},
    )


async def _received_snapshot(request: Request) -> tuple[Path, Path]:
    staged = getattr(request.state, "glyphchain_snapshot_upload", None)
    if isinstance(staged, tuple) and len(staged) == 2:
        root, snapshot = staged
        request.state.glyphchain_snapshot_upload = None
        return Path(root), Path(snapshot)
    content_type = str(request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != SNAPSHOT_MEDIA_TYPE:
        raise HTTPException(status_code=415, detail="glyphchain_snapshot_media_type_required")
    maximum = configured_ledger_limit_bytes() + (6 * 1024 * 1024)
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > maximum:
        raise HTTPException(status_code=413, detail="glyphchain_snapshot_archive_too_large")
    body = await request.body()
    if not body or len(body) > maximum:
        raise HTTPException(status_code=413, detail="glyphchain_snapshot_archive_too_large")
    root = Path(tempfile.mkdtemp(prefix="glyphchain-snapshot-upload-"))
    snapshot = root / "received.glyphchain-snapshot"
    snapshot.write_bytes(body)
    os.chmod(snapshot, 0o600)
    return root, snapshot


@router.post("/snapshot/verify")
async def verify_snapshot(
    request: Request,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    from backend.modules.consensus.engine import get_engine

    root, snapshot = await _received_snapshot(request)
    verified = None
    try:
        engine = get_engine()
        verified = _snapshot_call(lambda: verify_ledger_snapshot(
            snapshot,
            trusted_checkpoint=_trusted_checkpoint(),
            expected_chain_id=engine.chain_id,
            expected_network_id=engine.network_id,
        ))
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "snapshot": verified.summary(),
            "installed": False,
            "authenticated_by": "signed_desktop_session",
        }
    finally:
        if verified is not None:
            verified.cleanup()
        shutil.rmtree(root, ignore_errors=True)


@router.post("/snapshot/import")
async def import_snapshot(
    request: Request,
    confirmation: str = Query(default="", max_length=80),
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    from backend.modules.consensus.engine import get_engine

    root, snapshot = await _received_snapshot(request)
    verified = None
    try:
        if confirmation != "INSTALL_VERIFIED_GLYPHCHAIN_SNAPSHOT":
            raise HTTPException(status_code=422, detail="glyphchain_snapshot_install_confirmation_required")
        participation = _call(participation_from_env)
        if str(participation.get("role") or "light") != "light":
            raise HTTPException(status_code=409, detail="glyphchain_snapshot_import_requires_light_role")
        current = persist_get_checkpoint() or {}
        minimum_height = int(current.get("last_height") or 0)
        engine = get_engine()
        verified = _snapshot_call(lambda: verify_ledger_snapshot(
            snapshot,
            trusted_checkpoint=_trusted_checkpoint(),
            expected_chain_id=engine.chain_id,
            expected_network_id=engine.network_id,
            minimum_height=minimum_height,
        ))
        summary = verified.summary()
        installation = _snapshot_call(lambda: install_verified_ledger_database(
            verified.database_path,
            expected_sha256=str(summary["ledger"]["database_sha256"]),
        ))
        certificate = getattr(verified, "finality_certificate", None)
        consensus_recovery = (
            _snapshot_call(lambda: engine.apply_verified_snapshot_finality(
                snapshot_summary=summary,
                finality_certificate=certificate,
            ))
            if isinstance(certificate, dict) else
            {"applied": False, "reason": "test_or_legacy_verified_snapshot_without_retained_certificate"}
        )
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "operator_id": session.person_id,
            "snapshot": summary,
            "installation": installation,
            "consensus_recovery": consensus_recovery,
            "restart_required": True,
            "authenticated_by": "signed_desktop_session",
        }
    finally:
        if verified is not None:
            verified.cleanup()
        shutil.rmtree(root, ignore_errors=True)


@router.post("/snapshot/sync-from-peer")
async def sync_snapshot_from_peer(
    payload: SnapshotPeerSyncInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    from backend.modules.consensus.engine import get_engine

    if payload.confirmation != "SYNC_VERIFIED_GLYPHCHAIN_SNAPSHOT":
        raise HTTPException(status_code=422, detail="glyphchain_snapshot_sync_confirmation_required")
    participation = _call(participation_from_env)
    if str(participation.get("role") or "light") != "light":
        raise HTTPException(status_code=409, detail="glyphchain_snapshot_import_requires_light_role")
    peer = get_peer_by_node_id(payload.peer_node_id)
    if peer is None or bool(getattr(peer, "banned", False)) or not bool(getattr(peer, "hello_ok", False)):
        raise HTTPException(status_code=422, detail="glyphchain_snapshot_peer_not_verified")
    peer_url = str(getattr(peer, "base_url", "") or "").strip().rstrip("/")
    if not peer_url:
        raise HTTPException(status_code=422, detail="glyphchain_snapshot_peer_endpoint_missing")

    engine = get_engine()
    current = persist_get_checkpoint() or {}
    minimum_height = int(current.get("last_height") or 0)
    node_id = str(os.getenv("GLYPHCHAIN_NODE_ID", "") or os.getenv("P2P_NODE_ID", "") or "dev-node").strip()
    val_id = str(os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()
    legacy_private_key = str(os.getenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", "") or "").strip().lower()
    if legacy_private_key:
        private_key = legacy_private_key
    elif str(os.getenv("GLYPHCHAIN_NETWORK_KEY_DIR", "") or "").strip():
        identity = network_identity_store()
        private_key = _identity_call(identity.active_private_key_hex)
    else:
        raise HTTPException(
            status_code=503,
            detail="glyphchain_snapshot_sync_requires_active_router_network_identity",
        )
    request_payload = {
        "want": "latest_finalized_snapshot",
        "minimum_height": minimum_height,
        "request_nonce": secrets.token_hex(16),
    }
    request_payload["sig_hex"] = sign_ed25519(
        private_key,
        canonical_p2p_sign_bytes(
            msg_type="SNAPSHOT_REQ", chain_id=engine.chain_id, payload=request_payload,
        ),
    )
    envelope = {
        "type": "SNAPSHOT_REQ",
        "from_node_id": node_id,
        "from_val_id": val_id,
        "chain_id": engine.chain_id,
        "ts_ms": float(time.time() * 1000.0),
        "payload": request_payload,
        "hops": 0,
    }
    headers = {
        "x-glyphchain-p2p-node-id": node_id,
        "x-glyphchain-p2p-chain-id": engine.chain_id,
    }
    if val_id:
        headers["x-glyphchain-p2p-val-id"] = val_id
    temporary_root = Path(tempfile.mkdtemp(prefix="glyphchain-peer-sync-"))
    snapshot = temporary_root / "peer.glyphchain-snapshot"
    verified = None
    try:
        transport = await post_file(
            peer_url,
            "/api/p2p/snapshot_req",
            envelope,
            output_path=snapshot,
            expected_media_type=SNAPSHOT_MEDIA_TYPE,
            max_bytes=configured_ledger_limit_bytes() + (6 * 1024 * 1024),
            headers=headers,
        )
        verified = _snapshot_call(lambda: verify_ledger_snapshot(
            snapshot,
            trusted_checkpoint=_trusted_checkpoint(),
            expected_chain_id=engine.chain_id,
            expected_network_id=engine.network_id,
            minimum_height=minimum_height + 1,
        ))
        summary = verified.summary()
        transmitted_id = str(transport.get("snapshot_id") or "")
        if transmitted_id and transmitted_id != str(summary["snapshot_id"]):
            raise HTTPException(status_code=422, detail="glyphchain_snapshot_transport_identity_mismatch")
        installation = _snapshot_call(lambda: install_verified_ledger_database(
            verified.database_path,
            expected_sha256=str(summary["ledger"]["database_sha256"]),
        ))
        certificate = getattr(verified, "finality_certificate", None)
        consensus_recovery = (
            _snapshot_call(lambda: engine.apply_verified_snapshot_finality(
                snapshot_summary=summary,
                finality_certificate=certificate,
            ))
            if isinstance(certificate, dict) else
            {"applied": False, "reason": "test_or_legacy_verified_snapshot_without_retained_certificate"}
        )
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "operator_id": session.person_id,
            "peer_node_id": payload.peer_node_id,
            "snapshot": summary,
            "transport_bytes": int(transport.get("bytes") or 0),
            "installation": installation,
            "consensus_recovery": consensus_recovery,
            "restart_required": True,
            "authenticated_by": "signed_desktop_session",
        }
    except HTTPException:
        raise
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"glyphchain_snapshot_peer_sync_failed:{exc}") from exc
    finally:
        if verified is not None:
            verified.cleanup()
        shutil.rmtree(temporary_root, ignore_errors=True)


@router.post("/storage/prune-with-archive")
def prune_ledger_with_verified_archive(
    payload: PruneLedgerInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    """Compact historical rows only after retaining an independently verifiable archive."""
    from backend.modules.chain_sim import chain_sim_config, chain_sim_model, chain_sim_state
    from backend.modules.staking import staking_model
    from backend.modules.consensus.engine import get_engine

    if payload.confirmation != "PRUNE_GLYPHCHAIN_HISTORY_WITH_VERIFIED_ARCHIVE":
        raise HTTPException(status_code=422, detail="glyphchain_pruning_confirmation_required")
    participation = _call(participation_from_env)
    if str(participation.get("role") or "light") != "light":
        raise HTTPException(status_code=409, detail="glyphchain_pruning_requires_light_role")
    database = persist_database_path()
    checkpoint = persist_get_checkpoint() or {}
    height = int(checkpoint.get("last_height") or 0)
    if database is None or height <= 1:
        raise HTTPException(status_code=409, detail="glyphchain_pruning_insufficient_finalized_history")
    engine = get_engine()
    finality = engine.finality_receipt(height=height)
    certificate = finality.get("quorum_finality_certificate") if isinstance(finality, dict) else None
    if not isinstance(certificate, dict):
        raise HTTPException(status_code=409, detail="glyphchain_pruning_finality_certificate_unavailable")
    trusted = _trusted_checkpoint()
    archive = _pruning_archive_root() / f"glyphchain-full-history-h{height}-{secrets.token_hex(8)}.glyphchain-snapshot"
    temporary_root = Path(tempfile.mkdtemp(prefix="glyphchain-prune-"))
    verified = None
    try:
        manifest = _snapshot_call(lambda: export_ledger_snapshot(
            database_path=database,
            output_path=archive,
            chain_id=engine.chain_id,
            network_id=engine.network_id,
            finality_certificate=certificate,
            validator_checkpoint=trusted.value,
        ))
        os.chmod(archive, 0o600)
        verified = _snapshot_call(lambda: verify_ledger_snapshot(
            archive,
            trusted_checkpoint=trusted,
            expected_chain_id=engine.chain_id,
            expected_network_id=engine.network_id,
            minimum_height=height,
        ))
        exported_state = chain_sim_state.export_chain_state(
            cfg_mod=chain_sim_config,
            bank_mod=chain_sim_model,
            staking_mod=staking_model,
        )
        if str(exported_state.get("state_root") or "") != str(checkpoint.get("last_state_root") or ""):
            raise HTTPException(status_code=409, detail="glyphchain_pruning_live_state_not_at_checkpoint")
        compacted = temporary_root / "compacted-ledger.sqlite3"
        result = _pruning_call(lambda: compact_ledger_copy(
            database_path=verified.database_path,
            output_path=compacted,
            archive_path=archive,
            snapshot_manifest=manifest,
            base_state=dict(exported_state["state"]),
            base_state_root=str(exported_state["state_root"]),
            operator_id=session.person_id,
            reason=payload.reason,
        ))

        # A second consistent backup must still match the retained archive.
        # Any intervening ledger write aborts pruning rather than losing history.
        recheck = temporary_root / "recheck.glyphchain-snapshot"
        recheck_manifest = _snapshot_call(lambda: export_ledger_snapshot(
            database_path=database,
            output_path=recheck,
            chain_id=engine.chain_id,
            network_id=engine.network_id,
            finality_certificate=certificate,
            validator_checkpoint=trusted.value,
        ))
        if str(recheck_manifest["ledger"]["database_sha256"]) != str(manifest["ledger"]["database_sha256"]):
            raise HTTPException(status_code=409, detail="glyphchain_pruning_concurrent_ledger_change")
        installation = _snapshot_call(lambda: install_verified_ledger_database(
            compacted,
            expected_sha256=str(result["database_sha256"]),
        ))
        return {
            "ok": True,
            "workspace_id": session.workspace_id,
            "operator_id": session.person_id,
            "reason": payload.reason,
            "pruning": result,
            "archive": {
                "snapshot_id": manifest["snapshot_id"],
                "height": height,
                "retained": True,
            },
            "installation": installation,
            "restart_required": True,
            "authenticated_by": "signed_desktop_session",
        }
    except Exception:
        # Never remove an already completed archive on a failed compaction; it
        # remains useful recovery evidence and prevents a false deletion claim.
        raise
    finally:
        if verified is not None:
            verified.cleanup()
        shutil.rmtree(temporary_root, ignore_errors=True)


@router.post("/health/history")
def network_health_history(
    payload: NetworkHealthHistoryInput,
    session: VerifiedAionFlowSession = Depends(require_signed_desktop_admin),
) -> dict[str, Any]:
    store = network_health_store()
    return {
        "ok": True,
        "workspace_id": session.workspace_id,
        "history": store.history(limit=payload.limit),
        "history_chain_valid": store.verify(),
        "privacy_boundary": "aggregate_only_no_peer_addresses_node_ids_transactions_documents_or_signatures",
    }
