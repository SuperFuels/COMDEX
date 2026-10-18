"""Lean local API surface for the Tessaris macOS application.

``backend.main`` is the full historical COMDEX server.  Importing it mounts
dozens of unrelated research, blockchain, hologram, simulator and telemetry
systems and eagerly constructs their global objects.  The desktop product only
needs workflow, business, local-node, vault, boardroom and voice APIs.

Keeping this ASGI entrypoint explicit prevents opening Tessaris from becoming a
full research-stack boot while preserving the endpoints used by the renderer.
"""

from __future__ import annotations

import os
import base64
import json
import logging
from pathlib import Path
from threading import Event, Thread
from typing import Any

from dotenv import load_dotenv

_DESKTOP_PROCESS_SCOPED_ENV = {
    key: value
    for key, value in os.environ.items()
    if key.startswith("TESSARIS_DISCOVERY_")
    or key.startswith("TESSARIS_BUSINESS_VAULT_")
    or key in {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND",
        "TESSARIS_BUSINESS_NAME",
        "TESSARIS_BUSINESS_STABLE_ID",
        "TESSARIS_APPLICATION_ROOT",
        "TESSARIS_UPDATE_ROOT",
        "TESSARIS_AION_FLOW_SESSION_KEY_PATH",
        "TESSARIS_AION_FLOW_REPLAY_STORE_PATH",
    }
}

# The packaged desktop backend is launched from its bundled backend directory.
# The desktop app owns this local configuration.  Prefer its validated values
# over malformed credentials inherited from a parent shell.
# The desktop launcher supplies the isolated Vault, discovery and secret-store
# boundaries. A developer .env file may fill ordinary missing settings, but it
# must never replace those process-scoped security values.
load_dotenv(Path(__file__).resolve().parents[1] / ".env.local", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.boardroom_provider_router import router as boardroom_provider_router
from backend.api.business_runtime_router import router as business_runtime_router
from backend.api.local_node_router import router as local_node_router
from backend.api.aion_english_intelligence_router import router as aion_english_intelligence_router
from backend.api.vault_router import router as vault_router
from backend.api.workflow_architect_router import router as workflow_architect_router
from backend.api import workflow_capsule_router, workflow_glyph_router
from backend.modules.aion_business.api.boardroom_api import router as business_boardroom_router
from backend.modules.aion_business.api.brand_foundation_api import router as brand_foundation_router
from backend.modules.aion_business.api.browser_skills_api import router as browser_skills_router
from backend.modules.aion_business.api.business_twin_data_api import router as business_twin_data_router
from backend.modules.aion_business.api.container_bindings_api import router as container_bindings_router
from backend.modules.aion_business.api.department_pilot_api import router as department_pilot_router
from backend.modules.aion_business.api.finance_integrations_api import router as finance_integrations_router
from backend.modules.aion_business.api.finance_inbox_api import router as finance_inbox_router
from backend.modules.aion_business.api.finance_bookkeeping_api import router as finance_bookkeeping_router
from backend.modules.aion_business.api.finance_sales_api import router as finance_sales_router
from backend.modules.aion_business.api.sales_revenue_api import router as sales_revenue_router
from backend.modules.aion_business.api.medium_business_operating_api import router as medium_business_operating_router
from backend.modules.aion_business.api.sales_completion_api import router as sales_completion_router
from backend.modules.aion_business.api.support_case_api import router as support_case_router
from backend.modules.aion_business.api.cybersecurity_guard_api import router as cybersecurity_guard_router
from backend.modules.aion_business.api.project_management_api import router as project_management_router
from backend.modules.aion_business.api.marketing_creative_api import router as marketing_creative_router
from backend.modules.aion_business.api.marketing_connections_api import router as marketing_connections_router
from backend.modules.aion_business.api.organization_authority_api import router as organization_authority_router
from backend.modules.aion_business.api.pilot_scheduled_work_api import router as pilot_scheduled_work_router
from backend.modules.aion_business.api.pilot_operating_team_api import router as pilot_operating_team_router
from backend.modules.aion_business.api.work_schedule_api import router as work_schedule_router
from backend.modules.aion_business.api.a2a_commerce_api import public_router as a2a_commerce_public_router, internal_router as a2a_commerce_internal_router
from backend.modules.aion_business.api.workflow_api import router as business_workflow_router
from backend.modules.aion_business.api.workflow_file_cabinet_api import router as workflow_file_cabinet_router
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.pilot_scheduled_work_service import PilotScheduledWorkService
from backend.modules.aion_business.runtime.pilot_operating_team_service import PilotOperatingTeamService
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService
from backend.modules.aion_business.runtime.cybersecurity_guard_service import CybersecurityGuardScheduler
from backend.modules.aion_business.runtime.request_body_limits import ScopedRequestBodyLimitMiddleware
from backend.modules.aion_business.runtime.desktop_custody_attestation import desktop_custody_attestation
from backend.modules.aion_voice.api import router as voice_router
from backend.modules.aion_workflow.workflow_approval_repository import WorkflowApprovalRepository
from backend.modules.aion_workflow.workflow_dry_run import dry_run_workflow_glyph
from backend.modules.aion_workflow.workflow_glyph_repository import WorkflowGlyphRepository
from backend.modules.aion_workflow.workflow_resume import resume_workflow_after_approval

# Historical modules imported above may load developer dotenv files of their
# own. Reassert the launcher's validated, process-scoped custody boundary
# before constructing any desktop services or discovery controllers.
os.environ.update(_DESKTOP_PROCESS_SCOPED_ENV)

app = FastAPI(
    title="Tessaris Desktop Backend",
    version="1.0",
    docs_url=None,
    redoc_url=None,
)
DESKTOP_BACKEND_CONTRACT = 2
app.add_middleware(ScopedRequestBodyLimitMiddleware)

_desktop_pilot_scheduler_thread: Thread | None = None
_desktop_pilot_scheduler_stop = Event()
_logger = logging.getLogger("tessaris.desktop.pilot_scheduler")
_cybersecurity_guard_scheduler = CybersecurityGuardScheduler()


def _run_due_desktop_pilot_work() -> None:
    from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested

    # The legacy scheduler discovers tenants by walking the application tree.
    # In Guardian mode that tree is neither authoritative nor safe to inspect:
    # a Vault-native workspace index must drive the scheduler instead.
    if guardian_mode_requested():
        return
    root = AIONBusinessPaths.BUSINESS_CONTAINERS
    if not root.exists():
        return
    service = PilotScheduledWorkService()
    operating_team = PilotOperatingTeamService()
    work_schedule = WorkScheduleService()
    executive_briefings = workflow_capsule_router._operations_executive_service()
    for workspace in sorted(path for path in root.iterdir() if path.is_dir()):
        try:
            service.run_due(workspace.name)
            operating_team.run_due_routines(workspace.name)
            work_schedule.prepare_due_reminders(workspace.name)
            briefing_status = executive_briefings.status(workspace.name)
            if briefing_status.get("briefing_due"):
                executive_briefings.run_morning_briefing(
                    workspace.name, person_id="desktop_scheduler", force=False,
                )
        except Exception:
            _logger.exception("Pilot scheduled-work scan failed for %s", workspace.name)


def _desktop_pilot_scheduler_loop() -> None:
    while not _desktop_pilot_scheduler_stop.wait(60):
        _run_due_desktop_pilot_work()

@app.on_event("startup")
def start_support_channel_poller() -> None:
    global _desktop_pilot_scheduler_thread
    from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
    from backend.modules.aion_business.runtime.support_polling_service import SUPPORT_POLLER
    discovery_session = os.getenv("TESSARIS_DISCOVERY_AUTOSTART_SESSION", "").strip()
    discovery_isolated = os.getenv("TESSARIS_DISCOVERY_MODE", "0") == "1"
    if not discovery_isolated or discovery_session.startswith("support-"):
        SUPPORT_POLLER.start()
    # The historical creative poller scans a plaintext ~/Tessaris workspace.
    # Guardian mode must never recreate or inspect that legacy authority. A
    # Guardian-native render-job index is required before unattended polling is
    # re-enabled for sovereign business installations.
    if not guardian_mode_requested():
        from backend.modules.aion_business.runtime.creative_render_polling_service import CREATIVE_RENDER_POLLER
        CREATIVE_RENDER_POLLER.start()
    _cybersecurity_guard_scheduler.start()
    if (not discovery_isolated or discovery_session in {"scheduled-automation", "work-schedule"}) and (
        _desktop_pilot_scheduler_thread is None or not _desktop_pilot_scheduler_thread.is_alive()
    ):
        _desktop_pilot_scheduler_stop.clear()
        _desktop_pilot_scheduler_thread = Thread(
            target=_desktop_pilot_scheduler_loop,
            name="aion-desktop-pilot-scheduled-work",
            daemon=True,
        )
        _desktop_pilot_scheduler_thread.start()

@app.on_event("shutdown")
def stop_support_channel_poller() -> None:
    global _desktop_pilot_scheduler_thread
    from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
    from backend.modules.aion_business.runtime.support_polling_service import SUPPORT_POLLER
    SUPPORT_POLLER.stop()
    if not guardian_mode_requested():
        from backend.modules.aion_business.runtime.creative_render_polling_service import CREATIVE_RENDER_POLLER
        CREATIVE_RENDER_POLLER.stop()
    _cybersecurity_guard_scheduler.stop()
    _desktop_pilot_scheduler_stop.set()
    if _desktop_pilot_scheduler_thread is not None:
        _desktop_pilot_scheduler_thread.join(timeout=2)
        _desktop_pilot_scheduler_thread = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["null", "file://", "http://127.0.0.1:8080", "http://localhost:8080"],
    allow_origin_regex=r"^(file://|http://(127\.0\.0\.1|localhost)(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    workflow_capsule_router.router,
    workflow_glyph_router.router,
    workflow_architect_router,
    vault_router,
    boardroom_provider_router,
    local_node_router,
    aion_english_intelligence_router,
    business_runtime_router,
    container_bindings_router,
    brand_foundation_router,
    browser_skills_router,
    business_boardroom_router,
    business_twin_data_router,
    business_workflow_router,
    workflow_file_cabinet_router,
    finance_integrations_router,
    finance_inbox_router,
    finance_bookkeeping_router,
    finance_sales_router,
    sales_revenue_router,
    sales_completion_router,
    support_case_router,
    cybersecurity_guard_router,
    project_management_router,
    marketing_creative_router,
    marketing_connections_router,
    department_pilot_router,
    organization_authority_router,
    pilot_scheduled_work_router,
    pilot_operating_team_router,
    medium_business_operating_router,
    work_schedule_router,
    voice_router,
    a2a_commerce_public_router,
    a2a_commerce_internal_router,
):
    app.include_router(router)


if os.getenv("TESSARIS_DISCOVERY_MODE", "0") == "1":
    from backend.modules.aion_business.api.business_data_discovery_runtime_api import (
        create_business_data_external_surface_router,
        create_business_data_discovery_runtime_router,
    )
    from backend.modules.aion_business.runtime.business_data_discovery_runtime_controller import (
        BusinessDataDiscoveryRuntimeController,
    )
    from backend.modules.aion_business.runtime.business_data_external_surface_controller import (
        BusinessDataExternalSurfaceController,
    )
    from backend.modules.aion_business.runtime.business_data_discovery_environment import (
        parse_discovery_autostart,
        parse_discovery_vault_roots,
    )

    try:
        # The Electron discovery controller has always used the explicit
        # ``*_BASE64`` spelling.  Keep the older ``*_B64`` name as a
        # command-line compatibility alias, but do not require the managed
        # desktop launcher to translate or duplicate a custody secret.
        discovery_fingerprint_key_b64 = os.getenv(
            "TESSARIS_DISCOVERY_FINGERPRINT_KEY_BASE64"
        ) or os.environ["TESSARIS_DISCOVERY_FINGERPRINT_KEY_B64"]
        discovery_fingerprint_key = base64.b64decode(
            discovery_fingerprint_key_b64, validate=True
        )
        discovery_vault_roots = parse_discovery_vault_roots(
            os.environ["TESSARIS_DISCOVERY_VAULT_ROOTS"]
        )
        discovery_controller = BusinessDataDiscoveryRuntimeController(
            manifest_path=os.getenv(
                "TESSARIS_DISCOVERY_MANIFEST",
                str(Path(__file__).resolve().parents[1] / "config" / "business-data-manifest.v1.json"),
            ),
            trace_root=os.environ["TESSARIS_DISCOVERY_TRACE_ROOT"],
            source_root=Path(__file__).resolve().parents[1],
            application_root=os.environ["TESSARIS_DISCOVERY_APPLICATION_ROOT"],
            update_root=os.environ["TESSARIS_DISCOVERY_UPDATE_ROOT"],
            vault_roots=discovery_vault_roots,
            secret_store_roots=json.loads(
                os.getenv("TESSARIS_DISCOVERY_SECRET_STORE_ROOTS", "[]")
            ),
            path_fingerprint_key=discovery_fingerprint_key,
        )
        discovery_external_controller = BusinessDataExternalSurfaceController(
            manifest_path=os.getenv(
                "TESSARIS_DISCOVERY_MANIFEST",
                str(Path(__file__).resolve().parents[1] / "config" / "business-data-manifest.v1.json"),
            ),
            scenario_catalogue_path=os.getenv(
                "TESSARIS_DISCOVERY_SCENARIO_CATALOGUE",
                str(Path(__file__).resolve().parents[1] / "config" / "business-data-discovery-scenarios.v1.json"),
            ),
            trace_root=os.environ["TESSARIS_DISCOVERY_TRACE_ROOT"],
            fingerprint_key=discovery_fingerprint_key,
        )
        app.include_router(create_business_data_discovery_runtime_router(
            controller=discovery_controller,
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        app.include_router(create_business_data_external_surface_router(
            controller=discovery_external_controller,
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        # Journey 24 mounts a loopback-only, sandbox Photon control plane. Its
        # authority stays under the discovery secret-store boundary and never
        # becomes live provider configuration.
        from backend.modules.aion_business.api.photon_control_plane_api import (
            create_photon_control_plane_router,
        )
        from backend.modules.aion_business.api.photon_discovery_qualification_api import (
            create_photon_discovery_qualification_router,
        )
        from backend.modules.aion_business.api.business_vault_portable_transfer_qualification_api import (
            create_business_vault_portable_transfer_qualification_router,
        )
        from backend.modules.aion_business.api.business_vault_recovery_qualification_api import (
            create_business_vault_recovery_qualification_router,
        )
        from backend.modules.aion_business.api.diagnostic_support_qualification_api import (
            create_diagnostic_support_qualification_router,
        )
        from backend.modules.aion_business.api.business_retention_closure_qualification_api import (
            create_business_retention_closure_qualification_router,
        )
        from backend.modules.aion_business.runtime.photon_discovery_qualification import (
            build_photon_discovery_qualification_context,
        )
        discovery_secret_roots = json.loads(
            os.getenv("TESSARIS_DISCOVERY_SECRET_STORE_ROOTS", "[]")
        )
        if not discovery_secret_roots:
            raise ValueError("photon_discovery_secret_store_required")
        photon_context = build_photon_discovery_qualification_context(
            secret_store_root=discovery_secret_roots[0],
            export_root=(
                Path(discovery_secret_roots[0]).resolve()
                / "photon-qualification" / "customer-exports"
            ),
        )
        app.include_router(create_photon_control_plane_router(
            service=photon_context.service,
            authority_public_key=photon_context.access_private_key.public_key(),
        ))
        app.include_router(create_photon_discovery_qualification_router(
            context=photon_context,
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
            endpoint=f"http://127.0.0.1:{os.getenv('TESSARIS_BACKEND_PORT', '8080')}",
        ))
        portable_transfer_root = Path(discovery_secret_roots[0]).resolve() / "portable-transfer-qualification"
        app.include_router(create_business_vault_portable_transfer_qualification_router(
            source_root=portable_transfer_root / "legacy-source",
            export_root=portable_transfer_root / "customer-exports",
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        app.include_router(create_business_vault_recovery_qualification_router(
            staging_root=Path(discovery_secret_roots[0]).resolve() / "backup-recovery-qualification",
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        app.include_router(create_diagnostic_support_qualification_router(
            staging_root=Path(discovery_secret_roots[0]).resolve() / "diagnostic-support-qualification",
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        app.include_router(create_business_retention_closure_qualification_router(
            customer_export_path=(
                Path(discovery_secret_roots[0]).resolve()
                / "portable-transfer-qualification" / "customer-exports"
                / "journey25-whole-business.tessaris-export"
            ),
            backup_snapshot_path=(
                Path(discovery_secret_roots[0]).resolve()
                / "backup-recovery-qualification" / "backup-destination"
                / "journey26.tessaris-snapshot"
            ),
            access_token=os.environ["TESSARIS_DISCOVERY_ACCESS_TOKEN"],
        ))
        app.state.photon_discovery_qualification = photon_context
        discovery_autostart = parse_discovery_autostart(dict(os.environ))
        if discovery_autostart is not None:
            discovery_controller.start(
                session_id=discovery_autostart[0],
                scenario=discovery_autostart[1],
            )
    except (KeyError, ValueError) as exc:
        raise RuntimeError("Tessaris discovery mode is enabled but its secure configuration is invalid") from exc


@app.get("/health", tags=["health"])
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "tessaris_desktop",
        "desktop_contract": DESKTOP_BACKEND_CONTRACT,
        "embedding_device": os.getenv("AION_EMBEDDING_DEVICE", "automatic"),
        "business_vault_custody": desktop_custody_attestation(os.environ),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Tessaris desktop backend running"}


@app.post("/api/aion/workflows/save")
def save_aion_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return WorkflowGlyphRepository().save(payload)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/aion/workflows/{business_container}/{workflow_id}")
def get_aion_workflow(business_container: str, workflow_id: str) -> dict[str, Any]:
    record = WorkflowGlyphRepository().load(business_container, workflow_id)
    if record is None:
        return {"ok": False, "error": "Workflow not found"}
    return {"ok": True, "workflow": record}


@app.post("/api/aion/workflows/{business_container}/{workflow_id}/dry-run")
def dry_run_aion_workflow(business_container: str, workflow_id: str) -> dict[str, Any]:
    record = WorkflowGlyphRepository().load(business_container, workflow_id)
    if record is None:
        return {"ok": False, "error": "Workflow not found"}
    try:
        return dry_run_workflow_glyph(workflow_record=record)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _decide_aion_workflow_approval(
    business_container: str,
    workflow_id: str,
    approval_id: str,
    decision: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if decision not in {"approve", "reject"}:
        return {"ok": False, "error": "Unsupported approval decision"}
    try:
        record = WorkflowApprovalRepository().decide(
            business_container=business_container,
            workflow_id=workflow_id,
            approval_id=approval_id,
            decision="approved" if decision == "approve" else "rejected",
            reason=str((payload or {}).get("reason") or ""),
        )
        return {"ok": True, "approval": record}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.post("/api/aion/workflows/{business_container}/{workflow_id}/approvals/{approval_id}/approve")
def approve_aion_workflow(
    business_container: str,
    workflow_id: str,
    approval_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _decide_aion_workflow_approval(
        business_container,
        workflow_id,
        approval_id,
        "approve",
        payload,
    )


@app.post("/api/aion/workflows/{business_container}/{workflow_id}/approvals/{approval_id}/reject")
def reject_aion_workflow(
    business_container: str,
    workflow_id: str,
    approval_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _decide_aion_workflow_approval(
        business_container,
        workflow_id,
        approval_id,
        "reject",
        payload,
    )


@app.post("/api/aion/workflows/{business_container}/{workflow_id}/approvals/{approval_id}/resume")
def resume_aion_workflow(
    business_container: str,
    workflow_id: str,
    approval_id: str,
) -> dict[str, Any]:
    record = WorkflowGlyphRepository().load(business_container, workflow_id)
    if record is None:
        return {"ok": False, "error": "Workflow not found"}
    try:
        return resume_workflow_after_approval(
            workflow_record=record,
            approval_id=approval_id,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


runtime_dir = Path(os.getenv("DATA_ROOT", "data")).resolve()
if runtime_dir.exists():
    app.mount("/runtime", StaticFiles(directory=runtime_dir), name="runtime")

# Workflow-generated creative assets live under the repository-local runtime,
# separately from the business data root. Expose that owned asset store through
# a bounded static mount so desktop previews never depend on file:// access.
local_runtime_dir = Path(".runtime").resolve()
if local_runtime_dir.exists():
    app.mount(
        "/local-runtime",
        StaticFiles(directory=local_runtime_dir),
        name="local-runtime",
    )
