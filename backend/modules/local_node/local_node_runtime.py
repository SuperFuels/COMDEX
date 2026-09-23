from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib
import json
import sqlite3
from backend.modules.local_node.contracts_cloud_sync import CloudSyncRemoteCommand
from backend.modules.local_node.contracts_local_node import (
    DeploymentMode,
    LocalNodeConfig,
    utc_now_iso,
)

from uuid import uuid4
from backend.modules.local_node.local_queue_store import LocalQueueStore
from backend.modules.local_node.local_approval_store import LocalApprovalStore
from backend.modules.local_node.local_audit_store import LocalAuditStore
from backend.modules.local_node.local_node_health import LocalNodeHealth
from backend.modules.local_node.local_node_control import LocalNodeControl
from backend.modules.local_node.node_state_store import NodeStateStore
from backend.modules.local_node.workflow_runner_host import WorkflowRunnerHost
from backend.modules.local_node.sync_cursor_store import SyncCursorStore
from backend.modules.local_node.local_sync_endpoints import LocalSyncEndpoints
from backend.modules.local_node.local_scheduler_host import LocalSchedulerHost
from backend.modules.local_node.train_task_store import TrainTaskStore
from backend.modules.local_node.train_task_approval_store import TrainTaskApprovalStore
from backend.modules.local_node.tool_registry import ToolRegistryStore
from backend.modules.local_node.external_tool_discovery import ExternalToolDiscoveryService
from backend.modules.local_node.connector_registry import ConnectorRegistryStore
from backend.modules.local_node.pilot_authority_policy import PilotAuthorityPolicyStore
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_run_repository import (
    WorkflowRunRepository,
)
from backend.modules.aion_agents.runtime.agent_definition_repository import (
    AgentDefinitionRepository,
)
from backend.modules.aion_agents.runtime.approval_request_repository import (
    ApprovalRequestRepository,
)
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_execution_runtime import (
    WorkflowExecutionRuntime,
)
from backend.modules.aion_agents.runtime.trigger_service import TriggerService
from backend.modules.aion_agents.runtime.agent_service import AgentService
from backend.modules.aion_agents.runtime.manual_trigger_service import (
    ManualTriggerService,
)
from backend.modules.aion_agents.runtime.marketing_operator_seed import (
    seed_marketing_operator_bundle,
)

try:
    from backend.modules.aion_business.runtime.business_container_service import (
        BusinessContainerService,
    )
except Exception:
    BusinessContainerService = None  # type: ignore[misc,assignment]


class LocalNodeRuntime:
    def __init__(self, config: LocalNodeConfig) -> None:
        self.config = config
        self.base_dir = str(config.base_dir)

        self.queue_store = LocalQueueStore(self.base_dir)
        self.approval_store = LocalApprovalStore(self.base_dir)
        self.audit_store = LocalAuditStore(self.base_dir)
        self.node_state_store = NodeStateStore(self.base_dir)
        self.sync_cursor_store = SyncCursorStore(self.base_dir)
        self.train_task_store = TrainTaskStore(self.base_dir)
        self.train_task_approval_store = TrainTaskApprovalStore(self.base_dir)
        self.external_tool_discovery = ExternalToolDiscoveryService(self.base_dir)
        self.pilot_authority_policy = PilotAuthorityPolicyStore(self.base_dir)

        self.deployment_mode = (
            config.deployment_mode.value
            if isinstance(config.deployment_mode, DeploymentMode)
            else str(config.deployment_mode)
        )

        self.health = LocalNodeHealth(
            node_id=config.node_id,
            workspace_id=config.workspace_id,
            deployment_mode=self.deployment_mode,
            node_state_store=self.node_state_store,
        )

        self.control = LocalNodeControl(
            node_id=config.node_id,
            workspace_id=config.workspace_id,
            node_state_store=self.node_state_store,
        )

        self.runner_host = WorkflowRunnerHost(
            queue_store=self.queue_store,
            approval_store=self.approval_store,
            audit_store=self.audit_store,
            node_state_store=self.node_state_store,
        )

        self.sync_endpoints = LocalSyncEndpoints(
            node_id=config.node_id,
            workspace_id=config.workspace_id,
            deployment_mode=self.deployment_mode,
            queue_store=self.queue_store,
            approval_store=self.approval_store,
            audit_store=self.audit_store,
            node_state_store=self.node_state_store,
            sync_cursor_store=self.sync_cursor_store,
        )

        self.business_container_service = (
            BusinessContainerService() if BusinessContainerService is not None else None
        )

        self._init_agent_runtime()

        self.scheduler = LocalSchedulerHost(
            heartbeat_interval_seconds=config.heartbeat_interval_seconds,
            get_control_status=self.control.get_status,
            heartbeat_fn=self.heartbeat,
            run_next_fn=self.run_next,
            list_due_triggers_fn=self.run_due_triggers,
            append_audit_fn=self._append_audit,
        )

        self.node_state_store.save_node_snapshot(
            {
                "node_id": self.config.node_id,
                "workspace_id": self.config.workspace_id,
                "deployment_mode": self.deployment_mode,
                "status": "created",
                "updated_at": utc_now_iso(),
            }
        )

        self._ensure_canonical_business_containers()
        self._seed_default_agent_bundle()

    def _init_agent_runtime(self) -> None:
        self.workflow_definition_repository = WorkflowDefinitionRepository(
            base_dir=self.base_dir,
        )
        self.workflow_run_repository = WorkflowRunRepository(
            base_dir=self.base_dir,
        )
        self.agent_definition_repository = AgentDefinitionRepository(
            base_dir=self.base_dir,
        )
        self.approval_request_repository = ApprovalRequestRepository(
            base_dir=self.base_dir,
        )
        self.trigger_definition_repository = TriggerDefinitionRepository(
            base_dir=self.base_dir,
        )

        self.workflow_execution_runtime = WorkflowExecutionRuntime(
            workflow_definition_repository=self.workflow_definition_repository,
            workflow_run_repository=self.workflow_run_repository,
            approval_request_repository=self.approval_request_repository,
        )

        self.trigger_service = TriggerService(
            repository=self.trigger_definition_repository,
        )

        self.agent_service = AgentService(
            agent_repository=self.agent_definition_repository,
            workflow_repository=self.workflow_definition_repository,
            trigger_repository=self.trigger_definition_repository,
        )

        self.manual_trigger_service = ManualTriggerService(
            trigger_repository=self.trigger_definition_repository,
            workflow_repository=self.workflow_definition_repository,
            execution_runtime=self.workflow_execution_runtime,
        )

    def seed_customer_onboarding_train_task(self) -> Dict[str, Any]:
        workflow_id = "workflow_gmail_to_hubspot_welcome_v1"

        payload = {
            "workflow_id": workflow_id,
            "name": "Gmail lead to HubSpot and welcome draft",
            "department_key": "operations",
            "operator_id": "operator_customer_onboarding_v1",
            "enabled": False,
            "version": 1,
            "trigger": {
                "trigger_type": "gmail_message_match",
                "account_id": "default",
                "query": "is:unread",
                "dedupe": True,
                "max_results": 10,
            },
            "extraction": {
                "step_type": "extract_customer_details",
                "fields": [
                    {
                        "key": "name",
                        "label": "Customer name",
                        "required": False,
                        "description": "Name of the customer or lead.",
                    },
                    {
                        "key": "email",
                        "label": "Email",
                        "required": True,
                        "description": "Customer email address.",
                    },
                    {
                        "key": "phone",
                        "label": "Phone",
                        "required": False,
                        "description": "Customer phone number if present.",
                    },
                    {
                        "key": "company",
                        "label": "Company",
                        "required": False,
                        "description": "Company name if present.",
                    },
                    {
                        "key": "enquiry_type",
                        "label": "Enquiry type",
                        "required": False,
                        "description": "What the customer appears to be asking about.",
                    },
                ],
            },
            "hubspot": {
                "step_type": "hubspot_create_or_update_contact",
                "account_id": "default",
                "match_field": "email",
                "dry_run": True,
                "field_mapping": {
                    "email": "email",
                    "name": "firstname",
                    "phone": "phone",
                    "company": "company",
                    "enquiry_type": "message",
                },
            },
            "email_draft": {
                "step_type": "gmail_draft_welcome_email",
                "account_id": "default",
                "to_field": "email",
                "subject_template": "Welcome — thanks for your enquiry",
                "body_template": (
                    "Hi {{name}},\n\n"
                    "Thanks for getting in touch. We’ve received your enquiry about {{enquiry_type}} "
                    "and will come back to you shortly.\n\n"
                    "Best,\n"
                    "{{business_name}}"
                ),
            },
            "approval": {
                "step_type": "approval_checkpoint",
                "approval_mode": "ask_before_external_action",
                "title": "Review new customer automation",
                "require_human": True,
            },
            "metadata": {
                "phase": "phase_1_trigger_automation",
                "created_by": "system_seed",
            },
        }

        saved = self.train_task_store.save_workflow(
            self.config.workspace_id,
            workflow_id,
            payload,
        )

        self._append_audit(
            event_type="local_node.train_task_seeded",
            message="Customer onboarding train-task workflow seeded",
            payload={
                "workflow_id": workflow_id,
                "enabled": saved.get("enabled"),
            },
        )

        return {
            "ok": True,
            "item": saved,
            "at": utc_now_iso(),
        }


    def test_customer_onboarding_train_task(
        self,
        *,
        sample_email: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sample_email = sample_email or {}

        email_from = str(sample_email.get("from") or "").strip()
        subject = str(sample_email.get("subject") or "").strip()
        body = str(sample_email.get("body") or "").strip()
        email_id = str(sample_email.get("id") or "sample_email").strip()

        combined = f"{email_from}\n{subject}\n{body}"

        import re

        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            combined,
        )
        phone_match = re.search(
            r"(\+?\d[\d\s().-]{7,}\d)",
            combined,
        )
        name_match = re.search(
            r"(?:my name is|i am|i'm)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})",
            combined,
            flags=re.IGNORECASE,
        )

        extracted = {
            "name": name_match.group(1).strip() if name_match else "",
            "email": email_match.group(0).strip() if email_match else "",
            "phone": phone_match.group(1).strip() if phone_match else "",
            "company": "",
            "enquiry_type": subject or "Customer enquiry",
        }

        hubspot_action = {
            "step_type": "hubspot_create_or_update_contact",
            "dry_run": True,
            "match_field": "email",
            "would_create_or_update_contact": bool(extracted.get("email")),
            "field_mapping": {
                "email": extracted.get("email"),
                "firstname": extracted.get("name"),
                "phone": extracted.get("phone"),
                "company": extracted.get("company"),
                "message": extracted.get("enquiry_type"),
            },
        }

        first_name = extracted.get("name") or "there"
        business_name = "Costa Conexion"

        email_draft = {
            "step_type": "gmail_draft_welcome_email",
            "dry_run": True,
            "to": extracted.get("email"),
            "subject": "Welcome — thanks for your enquiry",
            "body": (
                f"Hi {first_name},\n\n"
                f"Thanks for getting in touch. We’ve received your enquiry about "
                f"{extracted.get('enquiry_type') or 'your request'} and will come back to you shortly.\n\n"
                f"Best,\n{business_name}"
            ),
        }

        approval = {
            "step_type": "approval_checkpoint",
            "approval_mode": "ask_before_external_action",
            "require_human": True,
            "title": "Review new customer automation",
            "status": "waiting_approval",
        }

        result = {
            "ok": True,
            "workflow_id": "workflow_gmail_to_hubspot_welcome_v1",
            "operator_id": "operator_customer_onboarding_v1",
            "department_key": "operations",
            "mode": "test_run",
            "input": {
                "sample_email_id": email_id,
                "from": email_from,
                "subject": subject,
            },
            "steps": [
                {
                    "step": 1,
                    "label": "Gmail trigger matched",
                    "ok": True,
                    "output": {
                        "email_id": email_id,
                        "query": "is:unread",
                    },
                },
                {
                    "step": 2,
                    "label": "Extract customer details",
                    "ok": bool(extracted.get("email")),
                    "output": extracted,
                },
                {
                    "step": 3,
                    "label": "Prepare HubSpot contact action",
                    "ok": True,
                    "output": hubspot_action,
                },
                {
                    "step": 4,
                    "label": "Prepare welcome email draft",
                    "ok": True,
                    "output": email_draft,
                },
                {
                    "step": 5,
                    "label": "Human approval checkpoint",
                    "ok": True,
                    "output": approval,
                },
            ],
            "extracted_customer": extracted,
            "hubspot_action": hubspot_action,
            "email_draft": email_draft,
            "approval": approval,
            "at": utc_now_iso(),
        }

        self._append_audit(
            event_type="local_node.train_task_customer_onboarding_test_run",
            message="Customer onboarding train-task test run completed",
            payload={
                "workflow_id": result["workflow_id"],
                "sample_email_id": email_id,
                "extracted_email": extracted.get("email"),
                "requires_approval": True,
            },
        )

        return result

    def get_gmail_connect_url(self) -> Dict[str, Any]:
        """
        Phase 2C Gmail OAuth consent URL generation.

        This generates a Google OAuth consent URL when the local OAuth client
        env config is present. It still does not exchange the callback code yet.
        """
        import os
        import secrets
        from urllib.parse import urlencode

        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        client_id = str(os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        redirect_uri = str(
            os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
            or "http://127.0.0.1:8080/api/local-node/connectors/gmail/oauth/callback"
        ).strip()

        scopes = [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/calendar.events",
        ]

        health = self.connector_registry.gmail_health()

        if not client_id:
            self._append_audit(
                event_type="local_node.gmail_connector_connect_failed",
                message="Gmail OAuth connect URL could not be generated: missing client id",
                payload={
                    "connector_id": health.get("connector_id"),
                    "account_id": health.get("account_id"),
                    "reason": "missing_google_oauth_client_id",
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
                level="warning",
            )

            return {
                "ok": False,
                "reason": "gmail_oauth_config_missing",
                "message": "GOOGLE_OAUTH_CLIENT_ID is not set. Add Google OAuth client config before connecting Gmail.",
                "connect_url": None,
                "connector": health,
                "required_env": [
                    "GOOGLE_OAUTH_CLIENT_ID",
                    "GOOGLE_OAUTH_CLIENT_SECRET",
                    "GOOGLE_OAUTH_REDIRECT_URI",
                ],
                "dry_run": True,
                "external_writes_enabled": False,
                "at": utc_now_iso(),
            }

        oauth_state = secrets.token_urlsafe(32)

        config = self.connector_registry.save_gmail_config(
            {
                "auth_status": "connect_url_generated",
                "connector_health": "not_connected",
                "oauth_state": oauth_state,
                "oauth_started_at": utc_now_iso(),
                "oauth_redirect_uri": redirect_uri,
                "oauth_scopes": scopes,
                "last_error": None,
                "dry_run_only": True,
                "external_writes_enabled": False,
            }
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": oauth_state,
        }

        connect_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

        self._append_audit(
            event_type="local_node.gmail_connector_connect_url_generated",
            message="Gmail OAuth connect URL generated",
            payload={
                "connector_id": config.get("connector_id"),
                "account_id": config.get("account_id"),
                "auth_status": config.get("auth_status"),
                "redirect_uri": redirect_uri,
                "scopes": scopes,
                "dry_run_only": True,
                "external_writes_enabled": False,
            },
        )

        return {
            "ok": True,
            "reason": "gmail_oauth_connect_url_generated",
            "message": "Gmail OAuth consent URL generated. Open connect_url to continue.",
            "connect_url": connect_url,
            "connector": self.connector_registry.gmail_health(),
            "scopes": scopes,
            "redirect_uri": redirect_uri,
            "dry_run": True,
            "external_writes_enabled": False,
            "next_required": [
                "Open consent URL",
                "Handle OAuth callback/code exchange",
                "Store token reference securely",
                "Update Gmail connector auth_status to connected",
            ],
            "at": utc_now_iso(),
        }

    def handle_gmail_oauth_callback(
        self,
        *,
        code: str,
        state: str,
        error: str = "",
    ) -> Dict[str, Any]:
        """
        Phase 2C Gmail OAuth callback/code exchange.

        This exchanges the Google OAuth code for tokens and stores them locally.
        External writes remain disabled; Gmail access is readonly for polling.
        """
        import json
        import os
        import urllib.error
        import urllib.parse
        import urllib.request

        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        config = self.connector_registry.get_gmail_config()
        expected_state = str(config.get("oauth_state") or "")
        redirect_uri = str(
            config.get("oauth_redirect_uri")
            or os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
            or "http://127.0.0.1:8080/api/local-node/connectors/gmail/oauth/callback"
        )

        if error:
            self.connector_registry.save_gmail_config(
                {
                    "auth_status": "not_connected",
                    "connector_health": "not_connected",
                    "last_error": f"Google OAuth error: {error}",
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                }
            )

            self._append_audit(
                event_type="local_node.gmail_connector_oauth_failed",
                message="Gmail OAuth callback returned an error",
                payload={
                    "error": error,
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
                level="warning",
            )

            return {
                "ok": False,
                "reason": "google_oauth_error",
                "error": error,
                "connector": self.connector_registry.gmail_health(),
                "at": utc_now_iso(),
            }

        if not code:
            return {
                "ok": False,
                "reason": "missing_oauth_code",
                "error": "OAuth callback did not include a code",
                "connector": self.connector_registry.gmail_health(),
                "at": utc_now_iso(),
            }

        if not state or not expected_state or state != expected_state:
            self._append_audit(
                event_type="local_node.gmail_connector_oauth_failed",
                message="Gmail OAuth callback state mismatch",
                payload={
                    "has_state": bool(state),
                    "has_expected_state": bool(expected_state),
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
                level="warning",
            )

            return {
                "ok": False,
                "reason": "oauth_state_mismatch",
                "error": "OAuth state mismatch",
                "connector": self.connector_registry.gmail_health(),
                "at": utc_now_iso(),
            }

        client_id = str(os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        client_secret = str(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()

        if not client_id or not client_secret:
            return {
                "ok": False,
                "reason": "gmail_oauth_config_missing",
                "error": "GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET is missing",
                "connector": self.connector_registry.gmail_health(),
                "at": utc_now_iso(),
            }

        token_request_body = urllib.parse.urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_request_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response_body = response.read().decode("utf-8")
                token_payload = json.loads(response_body)
        except Exception as exc:
            error_message = str(exc)
            self.connector_registry.save_gmail_config(
                {
                    "auth_status": "not_connected",
                    "connector_health": "not_connected",
                    "last_error": f"OAuth token exchange failed: {error_message}",
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                }
            )

            self._append_audit(
                event_type="local_node.gmail_connector_oauth_failed",
                message="Gmail OAuth token exchange failed",
                payload={
                    "error": error_message,
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
                level="error",
            )

            return {
                "ok": False,
                "reason": "oauth_token_exchange_failed",
                "error": error_message,
                "connector": self.connector_registry.gmail_health(),
                "at": utc_now_iso(),
            }

        token_store_result = self.connector_registry.save_gmail_token_payload(token_payload)

        config = self.connector_registry.save_gmail_config(
            {
                "auth_status": "connected",
                "connector_health": "available",
                "token_reference": token_store_result.get("token_reference"),
                "token_stored_at": token_store_result.get("stored_at"),
                "last_error": None,
                "dry_run_only": True,
                "external_writes_enabled": False,
            }
        )

        self._append_audit(
            event_type="local_node.gmail_connector_connected",
            message="Gmail connector connected",
            payload={
                "connector_id": config.get("connector_id"),
                "account_id": config.get("account_id"),
                "auth_status": config.get("auth_status"),
                "token_reference": config.get("token_reference"),
                "dry_run_only": True,
                "external_writes_enabled": False,
            },
        )

        return {
            "ok": True,
            "reason": "gmail_oauth_connected",
            "message": "Gmail connected. Aion remains dry-run only.",
            "connector": self.connector_registry.gmail_health(),
            "token_reference": config.get("token_reference"),
            "dry_run": True,
            "external_writes_enabled": False,
            "at": utc_now_iso(),
        }

    def disconnect_gmail_connector(self) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        config = self.connector_registry.save_gmail_config(
            {
                "auth_status": "not_connected",
                "connector_health": "not_connected",
                "last_error": "Gmail disconnected locally",
                "dry_run_only": True,
                "external_writes_enabled": False,
            }
        )

        self._append_audit(
            event_type="local_node.gmail_connector_disconnected",
            message="Gmail connector disconnected",
            payload={
                "connector_id": config.get("connector_id"),
                "account_id": config.get("account_id"),
                "auth_status": config.get("auth_status"),
                "dry_run_only": config.get("dry_run_only"),
                "external_writes_enabled": config.get("external_writes_enabled"),
            },
        )

        return {
            "ok": True,
            "item": config,
            "health": self.connector_registry.gmail_health(),
            "at": utc_now_iso(),
        }

    def _ensure_connector_registry(self) -> None:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))


    def _hubspot_mcp_b64url(self, raw: bytes) -> str:
        import base64

        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _hubspot_mcp_pkce_pair(self) -> Dict[str, str]:
        import hashlib
        import secrets

        verifier = self._hubspot_mcp_b64url(secrets.token_bytes(48))
        challenge = self._hubspot_mcp_b64url(
            hashlib.sha256(verifier.encode("utf-8")).digest()
        )

        return {
            "code_verifier": verifier,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

    def get_hubspot_mcp_connect_url(self) -> Dict[str, Any]:
        import os
        import secrets
        import urllib.parse

        self._ensure_connector_registry()

        client_id = os.getenv("HUBSPOT_MCP_CLIENT_ID", "").strip()
        app_id = os.getenv("HUBSPOT_MCP_APP_ID", "").strip()
        redirect_uri = (
            os.getenv("HUBSPOT_MCP_REDIRECT_URI", "").strip()
            or "http://127.0.0.1:8080/api/local-node/connectors/hubspot/mcp/oauth/callback"
        )
        authorize_url = (
            os.getenv("HUBSPOT_MCP_AUTHORIZE_URL", "").strip()
            or "https://mcp-eu1.hubspot.com/oauth/authorize/user"
        )
        server_url = (
            os.getenv("HUBSPOT_MCP_SERVER_URL", "").strip()
            or "https://mcp-eu1.hubspot.com"
        )

        if not client_id:
            return {
                "ok": False,
                "reason": "hubspot_mcp_oauth_config_missing",
                "message": "HUBSPOT_MCP_CLIENT_ID is not set.",
                "required_env": [
                    "HUBSPOT_MCP_CLIENT_ID",
                    "HUBSPOT_MCP_REDIRECT_URI",
                    "HUBSPOT_MCP_AUTHORIZE_URL",
                    "HUBSPOT_MCP_TOKEN_URL",
                    "HUBSPOT_MCP_SERVER_URL",
                ],
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        pkce = self._hubspot_mcp_pkce_pair()
        state = secrets.token_urlsafe(32)

        item = self.connector_registry.get_hubspot_config()
        item.update(
            {
                "auth_status": "connect_url_generated",
                "connector_health": "not_connected",
                "oauth_provider": "hubspot_mcp",
                "oauth_state": state,
                "oauth_started_at": utc_now_iso(),
                "oauth_redirect_uri": redirect_uri,
                "oauth_authorize_url": authorize_url,
                "mcp_server_url": server_url,
                "mcp_app_id": app_id or None,
                "mcp_client_id": client_id,
                "pkce_code_verifier": pkce["code_verifier"],
                "pkce_code_challenge": pkce["code_challenge"],
                "pkce_code_challenge_method": pkce["code_challenge_method"],
                "last_error": None,
                "dry_run_only": True,
                "external_writes_enabled": False,
            }
        )
        saved = self.connector_registry.save_hubspot_config(item)

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "code_challenge": pkce["code_challenge"],
            "code_challenge_method": pkce["code_challenge_method"],
        }

        # HubSpot MCP auth app scopes are usually configured on the app.
        # Optional override remains available for future compatibility.
        scope = os.getenv("HUBSPOT_MCP_SCOPES", "").strip()
        if scope:
            params["scope"] = scope

        connect_url = f"{authorize_url}?{urllib.parse.urlencode(params)}"

        self._append_audit(
            event_type="local_node.hubspot_mcp_connect_url_generated",
            message="HubSpot MCP OAuth connect URL generated",
            payload={
                "account_id": saved.get("account_id"),
                "mcp_app_id": app_id or None,
                "redirect_uri": redirect_uri,
                "server_url": server_url,
                "external_writes_enabled": False,
                "dry_run_only": True,
            },
        )

        return {
            "ok": True,
            "reason": "hubspot_mcp_connect_url_generated",
            "message": "HubSpot MCP OAuth consent URL generated. Open connect_url to continue.",
            "connect_url": connect_url,
            "connector": self.get_hubspot_connector_health(),
            "redirect_uri": redirect_uri,
            "mcp_server_url": server_url,
            "mcp_app_id": app_id or None,
            "dry_run_only": True,
            "external_writes_enabled": False,
            "next_required": [
                "Open consent URL",
                "Handle OAuth callback/code exchange",
                "Store MCP token reference securely",
                "Update HubSpot connector auth_status to connected",
            ],
            "at": utc_now_iso(),
        }

    def handle_hubspot_mcp_oauth_callback(
        self,
        *,
        code: str = "",
        state: str = "",
        error: str = "",
    ) -> Dict[str, Any]:
        import json
        import os
        import urllib.parse
        import urllib.request

        self._ensure_connector_registry()

        item = self.connector_registry.get_hubspot_config()

        if error:
            item.update(
                {
                    "auth_status": "not_connected",
                    "connector_health": "not_connected",
                    "last_error": error,
                }
            )
            saved = self.connector_registry.save_hubspot_config(item)

            self._append_audit(
                event_type="local_node.hubspot_mcp_oauth_failed",
                message="HubSpot MCP OAuth failed",
                payload={"error": error, "state": state},
                level="error",
            )

            return {
                "ok": False,
                "reason": "hubspot_mcp_oauth_error",
                "error": error,
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        expected_state = str(item.get("oauth_state") or "")
        if not state or state != expected_state:
            return {
                "ok": False,
                "reason": "hubspot_mcp_oauth_state_mismatch",
                "error": "OAuth state mismatch.",
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        if not code:
            return {
                "ok": False,
                "reason": "hubspot_mcp_oauth_code_missing",
                "error": "OAuth callback did not include a code.",
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        client_id = os.getenv("HUBSPOT_MCP_CLIENT_ID", "").strip()
        client_secret = os.getenv("HUBSPOT_MCP_CLIENT_SECRET", "").strip()
        redirect_uri = (
            os.getenv("HUBSPOT_MCP_REDIRECT_URI", "").strip()
            or str(item.get("oauth_redirect_uri") or "")
        )
        token_url = (
            os.getenv("HUBSPOT_MCP_TOKEN_URL", "").strip()
            or "https://mcp-eu1.hubspot.com/oauth/v3/token"
        )
        code_verifier = str(item.get("pkce_code_verifier") or "")

        if not client_id or not redirect_uri or not code_verifier:
            return {
                "ok": False,
                "reason": "hubspot_mcp_oauth_config_missing",
                "error": "Missing client_id, redirect_uri, or PKCE verifier.",
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        form = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        if client_secret:
            form["client_secret"] = client_secret

        request = urllib.request.Request(
            token_url,
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                token_payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            try:
                body = exc.read().decode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                body = ""

            error_text = f"{exc}: {body}" if body else str(exc)
            item.update(
                {
                    "auth_status": "not_connected",
                    "connector_health": "not_connected",
                    "last_error": error_text,
                }
            )
            self.connector_registry.save_hubspot_config(item)

            self._append_audit(
                event_type="local_node.hubspot_mcp_token_exchange_failed",
                message="HubSpot MCP token exchange failed",
                payload={
                    "error": error_text,
                    "token_url": token_url,
                    "redirect_uri": redirect_uri,
                },
                level="error",
            )

            return {
                "ok": False,
                "reason": "hubspot_mcp_token_exchange_failed",
                "error": error_text,
                "connector": self.get_hubspot_connector_health(),
                "at": utc_now_iso(),
            }

        token_store_result = self.connector_registry.save_hubspot_token_payload(
            {
                **token_payload,
                "provider": "hubspot_mcp",
                "token_url": token_url,
                "redirect_uri": redirect_uri,
                "mcp_server_url": os.getenv("HUBSPOT_MCP_SERVER_URL", "").strip()
                    or str(item.get("mcp_server_url") or "https://mcp-eu1.hubspot.com"),
                "stored_at": utc_now_iso(),
            }
        )

        item = self.connector_registry.get_hubspot_config()
        item.update(
            {
                "auth_status": "connected",
                "connector_health": "available",
                "oauth_provider": "hubspot_mcp",
                "last_error": None,
                "dry_run_only": True,
                "external_writes_enabled": False,
            }
        )
        self.connector_registry.save_hubspot_config(item)

        self._append_audit(
            event_type="local_node.hubspot_mcp_connected",
            message="HubSpot MCP connected",
            payload={
                "account_id": item.get("account_id"),
                "mcp_app_id": item.get("mcp_app_id"),
                "token_reference": item.get("token_reference"),
                "dry_run_only": True,
                "external_writes_enabled": False,
            },
        )

        return {
            "ok": True,
            "reason": "hubspot_mcp_oauth_connected",
            "message": "HubSpot MCP connected. Aion remains dry-run only until write gates are explicitly enabled.",
            "connector": self.get_hubspot_connector_health(),
            "token_reference": item.get("token_reference"),
            "dry_run_only": True,
            "external_writes_enabled": False,
            "at": utc_now_iso(),
        }

    def get_hubspot_connector_health(self) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        item = self.connector_registry.get_hubspot_config()

        return {
            "ok": True,
            "connector_id": item.get("connector_id") or "connector.hubspot.default",
            "provider": "hubspot",
            "account_id": item.get("account_id") or "default",
            "auth_status": item.get("auth_status") or "not_connected",
            "connector_health": item.get("connector_health") or "not_connected",
            "scopes": item.get("scopes") or [],
            "portal_id": item.get("portal_id"),
            "portal_name": item.get("portal_name"),
            "last_check_at": item.get("last_check_at"),
            "last_error": item.get("last_error"),
            "dry_run_only": item.get("dry_run_only") is not False,
            "external_writes_enabled": item.get("external_writes_enabled") is True,
            "at": utc_now_iso(),
        }

    def update_hubspot_connector_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        item = self.connector_registry.get_hubspot_config()

        allowed = {
            "account_id",
            "auth_status",
            "connector_health",
            "scopes",
            "portal_id",
            "portal_name",
            "dry_run_only",
            "external_writes_enabled",
            "last_error",
        }

        for key, value in (updates or {}).items():
            if key in allowed:
                item[key] = value

        # Phase 6 safety default: external writes stay locked unless explicitly enabled later.
        if item.get("external_writes_enabled") is not True:
            item["external_writes_enabled"] = False
            item["dry_run_only"] = True

        saved = self.connector_registry.save_hubspot_config(item)

        self._append_audit(
            event_type="local_node.hubspot_connector_config_updated",
            message="HubSpot connector config updated",
            payload={
                "account_id": saved.get("account_id"),
                "auth_status": saved.get("auth_status"),
                "connector_health": saved.get("connector_health"),
                "dry_run_only": saved.get("dry_run_only"),
                "external_writes_enabled": saved.get("external_writes_enabled"),
            },
        )

        return {
            "ok": True,
            "item": saved,
            "health": self.get_hubspot_connector_health(),
            "at": utc_now_iso(),
        }

    def disconnect_hubspot_connector(self) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        item = self.connector_registry.disconnect_hubspot()

        self._append_audit(
            event_type="local_node.hubspot_connector_disconnected",
            message="HubSpot connector disconnected",
            payload={
                "account_id": item.get("account_id"),
                "auth_status": item.get("auth_status"),
                "connector_health": item.get("connector_health"),
            },
        )

        return {
            "ok": True,
            "item": item,
            "health": self.get_hubspot_connector_health(),
            "at": utc_now_iso(),
        }

    def get_gmail_connector_health(self) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        health = self.connector_registry.gmail_health()

        self._append_audit(
            event_type="local_node.gmail_connector_health_checked",
            message="Gmail connector health checked",
            payload=health,
        )

        return health

    def update_gmail_connector_config(
        self,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        # Phase 2C safety: external writes remain blocked regardless of request.
        safe_updates = {
            **(updates or {}),
            "dry_run_only": True,
            "external_writes_enabled": False,
        }

        config = self.connector_registry.save_gmail_config(safe_updates)

        self._append_audit(
            event_type="local_node.gmail_connector_config_updated",
            message="Gmail connector config updated",
            payload={
                "connector_id": config.get("connector_id"),
                "account_id": config.get("account_id"),
                "auth_status": config.get("auth_status"),
                "polling_enabled": config.get("polling_enabled"),
                "dry_run_only": config.get("dry_run_only"),
                "external_writes_enabled": config.get("external_writes_enabled"),
            },
        )

        return {
            "ok": True,
            "item": config,
            "health": self.connector_registry.gmail_health(),
            "at": utc_now_iso(),
        }

    def list_external_tools(self) -> Dict[str, Any]:
        result = self.external_tool_discovery.list_external_tools()

        self._append_audit(
            event_type="local_node.external_tools_discovered",
            message="External connector tools discovered",
            payload={
                "count": result.get("count", 0),
                "providers": result.get("providers", {}),
                "safety": result.get("safety", {}),
            },
        )

        return result

    def _get_external_tool_by_id(self, tool_id: str) -> Dict[str, Any]:
        result = self.external_tool_discovery.list_external_tools()
        for tool in result.get("items", []):
            if str(tool.get("tool_id") or "") == str(tool_id or ""):
                return tool
        return {}

    def dry_run_external_tool(
        self,
        *,
        tool_id: str,
        payload: Dict[str, Any],
        workflow_id: str = "",
        run_id: str = "",
    ) -> Dict[str, Any]:
        tool_id = str(tool_id or "").strip()

        if not tool_id:
            return {
                "ok": False,
                "error": "tool_id is required",
                "at": utc_now_iso(),
            }

        tool = self._get_external_tool_by_id(tool_id)
        if not tool:
            return {
                "ok": False,
                "error": "External tool not found",
                "tool_id": tool_id,
                "at": utc_now_iso(),
            }

        provider = str(tool.get("provider") or "unknown")
        action_type = str(tool.get("action_type") or "")
        risk_level = str(tool.get("risk_level") or "unknown")
        permission_mode = str(tool.get("permission_mode") or "dry_run_only")
        external_write = tool.get("external_write") is True
        requires_approval = tool.get("requires_approval") is True
        connector_health = str(tool.get("connector_health") or "unknown")

        blocked_by_policy = (
            external_write
            and permission_mode in {"dry_run_only", "blocked", "approval_required"}
        )

        prepared_payload = {
            "tool_id": tool_id,
            "tool_name": tool.get("name"),
            "provider": provider,
            "action_type": action_type,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "input_payload": payload or {},
            "risk_level": risk_level,
            "permission_mode": permission_mode,
            "requires_approval": requires_approval,
            "external_write": external_write,
            "external_write_blocked": blocked_by_policy,
            "connector_health": connector_health,
            "dry_run": True,
        }

        self._append_audit(
            event_type="local_node.external_tool_invocation_prepared",
            message="External tool invocation prepared",
            payload=prepared_payload,
        )

        output_payload: Dict[str, Any] = {
            "ok": True,
            "tool_id": tool_id,
            "tool_name": tool.get("name"),
            "provider": provider,
            "provider_category": tool.get("provider_category"),
            "server_id": tool.get("server_id"),
            "tool_name_external": tool.get("tool_name"),
            "action_type": action_type,
            "dry_run": True,
            "input_payload": payload or {},
            "output_payload": {
                "dry_run": True,
                "would_execute": external_write,
                "external_write_blocked": blocked_by_policy,
                "connector_health": connector_health,
            },
            "risk_level": risk_level,
            "permission_mode": permission_mode,
            "requires_approval": requires_approval,
            "external_write": external_write,
            "external_write_blocked": blocked_by_policy,
            "blocked_by_policy": blocked_by_policy,
            "connector_health": connector_health,
            "at": utc_now_iso(),
        }

        if action_type == "crm_contact_upsert":
            output_payload["output_payload"] = {
                "dry_run": True,
                "would_create_or_update_contact": bool((payload or {}).get("email")),
                "match_field": "email",
                "field_mapping": payload or {},
                "external_write_blocked": True,
                "connector_health": connector_health,
            }

        elif action_type == "hris_employee_lookup":
            output_payload["output_payload"] = {
                "dry_run": True,
                "matched": False,
                "employee": None,
                "note": "Read-only StackOne HRIS lookup stub. No external connector call made.",
                "connector_health": connector_health,
            }

        elif action_type == "ats_candidate_action":
            output_payload["output_payload"] = {
                "dry_run": True,
                "would_apply_candidate_action": bool((payload or {}).get("candidate_email")),
                "action": (payload or {}).get("action"),
                "external_write_blocked": True,
                "connector_health": connector_health,
            }

        elif action_type == "google_cloud_api_registry":
            output_payload["output_payload"] = {
                "dry_run": True,
                "planned_operation": payload or {},
                "external_write_blocked": True,
                "connector_health": connector_health,
            }

        if blocked_by_policy:
            self._append_audit(
                event_type="local_node.external_tool_blocked_by_policy",
                message="External tool blocked by policy",
                payload={
                    **prepared_payload,
                    "blocked_by_policy": True,
                },
                level="warning",
            )

        self._append_audit(
            event_type="local_node.external_tool_dry_run_completed",
            message="External tool dry-run completed",
            payload={
                **prepared_payload,
                "output_payload": output_payload.get("output_payload"),
                "blocked_by_policy": blocked_by_policy,
            },
        )

        return output_payload

    def list_tools(self) -> Dict[str, Any]:
        if not hasattr(self, "tool_registry") or self.tool_registry is None:
            self.tool_registry = ToolRegistryStore(str(self.base_dir))
        self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        tools = self.tool_registry.list_tools()

        self._append_audit(
            event_type="local_node.tool_registry_listed",
            message="Aion tool registry listed",
            payload={
                "tool_count": len(tools),
            },
        )

        return {
            "ok": True,
            "items": tools,
            "count": len(tools),
            "at": utc_now_iso(),
        }

    def _get_tool_by_action_type(self, action_type: str) -> Dict[str, Any]:
        if not hasattr(self, "tool_registry") or self.tool_registry is None:
            self.tool_registry = ToolRegistryStore(str(self.base_dir))

        tool = self.tool_registry.find_by_action_type(action_type)
        if tool:
            return tool

        return {
            "tool_id": f"tool.unknown.{action_type}",
            "name": action_type,
            "provider": "manual_stub",
            "action_type": action_type,
            "risk_level": "read_only",
            "permission_mode": "dry_run_only",
            "dry_run_supported": True,
            "requires_approval": False,
            "external_write": False,
            "enabled": False,
            "connector_health": "placeholder",
        }

    def _decorate_tool_output(
        self,
        output: Dict[str, Any],
        *,
        action_type: str,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        tool = self._get_tool_by_action_type(action_type)
        external_write = tool.get("external_write") is True
        permission_mode = str(tool.get("permission_mode") or "dry_run_only")
        blocked_by_policy = external_write and permission_mode in {"dry_run_only", "blocked"} and not dry_run

        return {
            **output,
            "tool_id": tool.get("tool_id"),
            "tool_name": tool.get("name"),
            "tool_provider": tool.get("provider"),
            "action_type": tool.get("action_type") or action_type,
            "risk_level": tool.get("risk_level"),
            "permission_mode": permission_mode,
            "requires_approval": tool.get("requires_approval") is True,
            "external_write": external_write,
            "external_write_blocked": external_write and permission_mode == "dry_run_only",
            "blocked_by_policy": blocked_by_policy,
        }

    def _audit_tool_result(
        self,
        *,
        workflow_id: str,
        workflow_name: str,
        run_id: str,
        step_number: int,
        step_title: str,
        output: Dict[str, Any],
    ) -> None:
        tool_id = output.get("tool_id")
        if not tool_id:
            return

        payload = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "run_id": run_id,
            "step": step_number,
            "title": step_title,
            "tool_id": tool_id,
            "tool_name": output.get("tool_name"),
            "provider": output.get("tool_provider"),
            "action_type": output.get("action_type"),
            "risk_level": output.get("risk_level"),
            "permission_mode": output.get("permission_mode"),
            "dry_run": output.get("dry_run", True),
            "requires_approval": output.get("requires_approval") is True,
            "external_write": output.get("external_write") is True,
            "external_write_blocked": output.get("external_write_blocked") is True,
        }

        self._append_audit(
            event_type="local_node.tool_invocation_prepared",
            message="Tool invocation prepared",
            payload=payload,
        )

        if output.get("blocked_by_policy") is True or output.get("external_write_blocked") is True:
            self._append_audit(
                event_type="local_node.tool_blocked_by_policy",
                message="Tool blocked by policy",
                payload=payload,
            )

        if output.get("dry_run", True) is True:
            self._append_audit(
                event_type="local_node.tool_dry_run_completed",
                message="Tool dry-run completed",
                payload=payload,
            )

    def toggle_train_task_workflow(
        self,
        workflow_id: str,
        enabled: bool,
    ) -> Dict[str, Any]:
        workflow = self.train_task_store.get_workflow(
            self.config.workspace_id,
            workflow_id,
        )

        if not workflow:
            return {
                "ok": False,
                "error": "Workflow not found",
                "workflow_id": workflow_id,
                "at": utc_now_iso(),
            }

        workflow["enabled"] = bool(enabled)

        metadata = workflow.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        metadata["last_toggled_by"] = "operations_agents_desktop"
        metadata["last_toggled_at"] = utc_now_iso()
        workflow["metadata"] = metadata

        saved = self.train_task_store.save_workflow(
            self.config.workspace_id,
            workflow_id,
            workflow,
        )

        self._append_audit(
            event_type="local_node.train_task_workflow_toggled",
            message="Train-task workflow enabled state changed",
            payload={
                "workflow_id": workflow_id,
                "enabled": saved.get("enabled") is True,
            },
        )

        return {
            "ok": True,
            "item": saved,
            "workflow_id": workflow_id,
            "enabled": saved.get("enabled") is True,
            "at": utc_now_iso(),
        }

    def list_train_task_workflows(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "items": self.train_task_store.list_workflows(self.config.workspace_id),
            "at": utc_now_iso(),
        }

    def save_train_task_workflow(
        self,
        workflow: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(workflow, dict):
            raise ValueError("workflow must be an object")

        name = str(workflow.get("name") or "").strip()
        if not name:
            raise ValueError("workflow.name is required")

        workflow_id = str(
            workflow.get("workflow_id")
            or workflow.get("id")
            or ""
        ).strip()

        if not workflow_id:
            slug = (
                name.lower()
                .replace("&", "and")
                .replace("/", " ")
                .replace("\\", " ")
                .replace("—", " ")
                .replace("-", " ")
            )
            slug = "_".join(part for part in slug.split() if part)
            workflow_id = f"workflow_{slug}_v1"

        payload = {
            **workflow,
            "workflow_id": workflow_id,
            "department_key": workflow.get("department_key") or "operations",
            "operator_id": workflow.get("operator_id") or "operator_custom_train_task_v1",
            "enabled": bool(workflow.get("enabled", False)),
            "version": int(workflow.get("version") or 1),
            "metadata": {
                **(workflow.get("metadata") or {}),
                "phase": "phase_1_trigger_automation",
                "created_by": "train_task_wizard",
                "source": "operations_agents_desktop",
            },
        }

        saved = self.train_task_store.save_workflow(
            self.config.workspace_id,
            workflow_id,
            payload,
        )

        self._append_audit(
            event_type="local_node.train_task_workflow_saved",
            message="Train-task workflow saved from Operations Agents wizard",
            payload={
                "workflow_id": workflow_id,
                "department_key": saved.get("department_key"),
                "enabled": saved.get("enabled"),
            },
        )

        return {
            "ok": True,
            "item": saved,
            "at": utc_now_iso(),
        }

    def _build_train_task_proposed_actions(
        self,
        *,
        hubspot_action: Dict[str, Any],
        email_draft: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "action_id": "hubspot_contact_upsert_dry_run",
                "label": "HubSpot contact update",
                "tool_id": hubspot_action.get("tool_id") or "tool.hubspot.contact_upsert_dry_run.v1",
                "risk_level": hubspot_action.get("risk_level") or "external_write",
                "permission_mode": hubspot_action.get("permission_mode") or "dry_run_only",
                "dry_run": hubspot_action.get("dry_run", True) is not False,
                "external_write": hubspot_action.get("external_write") is True,
                "external_write_blocked": hubspot_action.get("external_write_blocked") is not False,
                "payload": hubspot_action,
            },
            {
                "action_id": "gmail_draft_preview",
                "label": "Gmail draft preview",
                "tool_id": email_draft.get("tool_id") or "tool.gmail.draft_preview.v1",
                "risk_level": email_draft.get("risk_level") or "draft_only",
                "permission_mode": email_draft.get("permission_mode") or "dry_run_only",
                "dry_run": email_draft.get("dry_run", True) is not False,
                "external_write": email_draft.get("external_write") is True,
                "external_write_blocked": email_draft.get("external_write_blocked") is True,
                "payload": email_draft,
            },
        ]

    def _create_train_task_approval_from_replay(
        self,
        *,
        workflow: Dict[str, Any],
        result: Dict[str, Any],
        run_id: str,
        trigger_source: str = "test_run",
    ) -> Dict[str, Any]:
        from uuid import uuid4

        workflow_id = str(result.get("workflow_id") or workflow.get("workflow_id") or "")
        workflow_name = str(result.get("workflow_name") or workflow.get("name") or workflow_id)
        extracted_customer = result.get("extracted_customer") or {}
        hubspot_action = result.get("hubspot_action") or {}
        email_draft = result.get("email_draft") or {}
        approval_checkpoint = result.get("approval") or {}

        proposed_actions = self._build_train_task_proposed_actions(
            hubspot_action=hubspot_action,
            email_draft=email_draft,
        )

        risk_levels = [str(action.get("risk_level") or "") for action in proposed_actions]
        risk_level = "external_write" if "external_write" in risk_levels else "draft_only"

        approval_id = f"approval_train_task_{uuid4().hex[:12]}"

        payload = {
            "approval_id": approval_id,
            "approval_type": "train_task_replay_approval",
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "run_id": run_id,
            "title": approval_checkpoint.get("title") or f"Review {workflow_name}",
            "description": (
                "Review the proposed dry-run actions prepared by Aion. "
                "Approving this item will only store the approval decision in Phase 3; "
                "it will not create Gmail drafts or write to HubSpot yet."
            ),
            "trigger_source": trigger_source,
            "message_id": result.get("message_id"),
            "poll_id": result.get("poll_id"),
            "extracted_customer": extracted_customer,
            "proposed_actions": proposed_actions,
            "gmail_draft": email_draft,
            "crm_payload": hubspot_action,
            "risk_level": risk_level,
            "status": "pending",
            "approval_mode": approval_checkpoint.get("approval_mode") or "ask_before_external_action",
            "dry_run": True,
            "external_writes_enabled": False,
            "created_at": utc_now_iso(),
            "decision": None,
            "resolution_note": None,
        }

        saved = self.train_task_approval_store.save_approval(
            self.config.workspace_id,
            approval_id,
            payload,
        )

        self._append_audit(
            event_type="local_node.train_task_approval_created",
            message="Train-task approval created",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "trigger_source": trigger_source,
                "risk_level": risk_level,
                "status": "pending",
                "dry_run": True,
                "external_writes_enabled": False,
            },
        )

        return saved

    def list_train_task_approvals(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        return {
            "ok": True,
            "items": self.train_task_approval_store.list_approvals(
                self.config.workspace_id,
                status=status,
                limit=limit,
            ),
            "at": utc_now_iso(),
        }

    def run_external_tool_workflow_test(
        self,
        *,
        workflow_id: str = "workflow_phase5_stackone_tool_reference_test",
        tool_id: str = "tool.stackone.crm.contact_upsert.v1",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from uuid import uuid4

        run_id = f"run_{workflow_id}_{uuid4().hex[:10]}"

        input_payload = payload or {
            "email": "jane@example.com",
            "firstname": "Jane",
            "phone": "07123 456789",
            "company": "CostaConnect",
        }

        workflow = {
            "workflow_id": workflow_id,
            "name": "Phase 5 StackOne tool reference test",
            "department_key": "operations",
            "operator_id": "operator_phase5_external_tool_test",
            "enabled": True,
            "version": 1,
            "steps": [
                {
                    "step_id": "step_1_external_tool_dry_run",
                    "type": "external_tool_action",
                    "tool_id": tool_id,
                    "action_id": "external_tool_dry_run",
                    "input_mapping": {
                        "fixed_payload": input_payload,
                    },
                    "output_mapping": {
                        "output_name": "external_tool_result",
                    },
                    "approval_requirement": "approval_required_for_live_write",
                    "dry_run": True,
                }
            ],
            "metadata": {
                "phase": "phase_5_stackone_mcp_pilot",
                "source": "external_tool_workflow_test",
            },
        }

        external_result = self.dry_run_external_tool(
            tool_id=tool_id,
            payload=input_payload,
            workflow_id=workflow_id,
            run_id=run_id,
        )

        result = {
            "ok": external_result.get("ok") is True,
            "workflow_id": workflow_id,
            "workflow_name": workflow["name"],
            "workflow": workflow,
            "run_id": run_id,
            "mode": "external_tool_dry_run_test",
            "steps": [
                {
                    "step": 1,
                    "title": "External tool dry-run",
                    "ok": external_result.get("ok") is True,
                    "tool_id": tool_id,
                    "output": external_result,
                }
            ],
            "external_tool_result": external_result,
            "dry_run": True,
            "external_write_blocked": external_result.get("external_write_blocked") is True,
            "blocked_by_policy": external_result.get("blocked_by_policy") is True,
            "at": utc_now_iso(),
        }

        self.train_task_store.save_run(
            self.config.workspace_id,
            run_id,
            result,
        )

        self._append_audit(
            event_type="local_node.external_tool_workflow_test_completed",
            message="External tool workflow test completed",
            payload={
                "workflow_id": workflow_id,
                "run_id": run_id,
                "tool_id": tool_id,
                "ok": result["ok"],
                "dry_run": True,
                "external_write_blocked": result["external_write_blocked"],
                "blocked_by_policy": result["blocked_by_policy"],
            },
        )

        return result

    def _get_hubspot_mcp_token_payload(self) -> Dict[str, Any]:
        self._ensure_connector_registry()
        return self.connector_registry.read_hubspot_token_payload()

    def _hubspot_mcp_access_token(self) -> str:
        token_payload = self._get_hubspot_mcp_token_payload()
        token = str(token_payload.get("access_token") or "").strip()

        if not token:
            raise RuntimeError("HubSpot MCP access token missing. Reconnect HubSpot MCP.")

        return token

    def _hubspot_mcp_server_url(self) -> str:
        import os

        token_payload = self._get_hubspot_mcp_token_payload()
        server_url = (
            os.getenv("HUBSPOT_MCP_SERVER_URL", "").strip()
            or str(token_payload.get("mcp_server_url") or "").strip()
            or "https://mcp.hubspot.com"
        )

        return server_url.rstrip("/") + "/"

    def _parse_mcp_response_body(self, body: str) -> Dict[str, Any]:
        import json

        text = str(body or "").strip()

        if not text:
            return {}

        # Some streamable HTTP MCP servers return server-sent events.
        # Parse the final/first JSON data line if response is SSE.
        if text.startswith("event:") or text.startswith("data:"):
            data_lines = []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    value = line[len("data:"):].strip()
                    if value and value != "[DONE]":
                        data_lines.append(value)

            for value in reversed(data_lines):
                try:
                    return json.loads(value)
                except Exception:
                    continue

            return {
                "raw": text,
                "parse_warning": "Could not parse SSE MCP response as JSON.",
            }

        return json.loads(text)

    def _hubspot_mcp_rpc(
        self,
        *,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Any = 1,
    ) -> Dict[str, Any]:
        import json
        import urllib.request

        access_token = self._hubspot_mcp_access_token()
        url = self._hubspot_mcp_server_url()

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }

        if params is not None:
            payload["params"] = params

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2025-06-18",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return self._parse_mcp_response_body(body)
        except Exception as exc:
            try:
                body = exc.read().decode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                body = ""

            status = getattr(exc, "code", None)
            headers = {}
            try:
                headers = dict(getattr(exc, "headers", {}) or {})
            except Exception:
                headers = {}

            error_text = f"{exc}: {body}" if body else str(exc)
            raise RuntimeError(
                json.dumps(
                    {
                        "error": error_text,
                        "status": status,
                        "headers": headers,
                        "body": body,
                    },
                    ensure_ascii=False,
                    default=str,
                )
            ) from exc

    def list_hubspot_mcp_remote_tools(self) -> Dict[str, Any]:
        self._ensure_connector_registry()

        health = self.get_hubspot_connector_health()
        if health.get("auth_status") != "connected":
            return {
                "ok": False,
                "reason": "hubspot_mcp_not_connected",
                "error": "HubSpot MCP connector is not connected.",
                "connector": health,
                "at": utc_now_iso(),
            }

        started_at = utc_now_iso()

        self._append_audit(
            event_type="local_node.hubspot_mcp_tools_list_started",
            message="HubSpot MCP remote tools list started",
            payload={
                "server_url": self._hubspot_mcp_server_url(),
                "started_at": started_at,
            },
        )

        try:
            initialize = self._hubspot_mcp_rpc(
                method="initialize",
                params={
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "aion-local-node",
                        "version": "0.1.0",
                    },
                },
                request_id=1,
            )

            tools_response = self._hubspot_mcp_rpc(
                method="tools/list",
                params={},
                request_id=2,
            )

            tools = []
            result = tools_response.get("result") or {}
            if isinstance(result, dict):
                tools = result.get("tools") or []

            self._append_audit(
                event_type="local_node.hubspot_mcp_tools_list_completed",
                message="HubSpot MCP remote tools list completed",
                payload={
                    "tool_count": len(tools) if isinstance(tools, list) else 0,
                    "server_url": self._hubspot_mcp_server_url(),
                },
            )

            return {
                "ok": True,
                "server_url": self._hubspot_mcp_server_url(),
                "initialize": initialize,
                "tools_response": tools_response,
                "items": tools if isinstance(tools, list) else [],
                "count": len(tools) if isinstance(tools, list) else 0,
                "at": utc_now_iso(),
            }

        except Exception as exc:
            error = str(exc)

            self._append_audit(
                event_type="local_node.hubspot_mcp_tools_list_failed",
                message="HubSpot MCP remote tools list failed",
                payload={
                    "error": error,
                    "server_url": self._hubspot_mcp_server_url(),
                },
                level="error",
            )

            return {
                "ok": False,
                "reason": "hubspot_mcp_tools_list_failed",
                "error": error,
                "server_url": self._hubspot_mcp_server_url(),
                "at": utc_now_iso(),
            }

    def _hubspot_mcp_tools_call(
        self,
        *,
        name: str,
        arguments: Dict[str, Any],
        request_id: Any = 10,
    ) -> Dict[str, Any]:
        return self._hubspot_mcp_rpc(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments,
            },
            request_id=request_id,
        )

    def _extract_hubspot_mcp_contact_reference(
        self,
        mcp_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        import json
        import re

        text_parts = []

        result = mcp_response.get("result") or {}
        content = result.get("content") if isinstance(result, dict) else None

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                    elif item.get("type") == "json":
                        text_parts.append(json.dumps(item, default=str))
                else:
                    text_parts.append(str(item))

        raw_text = "\n".join(text_parts).strip()

        contact_id = ""
        hubspot_url = ""

        # Try JSON first.
        for part in text_parts:
            try:
                parsed = json.loads(part)
            except Exception:
                continue

            def walk(value):
                nonlocal contact_id, hubspot_url
                if isinstance(value, dict):
                    for k, v in value.items():
                        key = str(k).lower()
                        if key in {"id", "objectid", "object_id", "contactid", "contact_id"} and not contact_id:
                            if v is not None:
                                contact_id = str(v)
                        if "url" in key and not hubspot_url:
                            if isinstance(v, str) and "hubspot" in v:
                                hubspot_url = v
                        walk(v)
                elif isinstance(value, list):
                    for entry in value:
                        walk(entry)

            walk(parsed)

        # Fallback regex over text.
        if not contact_id:
            match = re.search(r'["\']?id["\']?\s*[:=]\s*["\']?(\d+)["\']?', raw_text)
            if match:
                contact_id = match.group(1)

        if not hubspot_url:
            match = re.search(r'https://app\.hubspot\.com/[^\s"\']+', raw_text)
            if match:
                hubspot_url = match.group(0)

        return {
            "contact_id": contact_id,
            "hubspot_url": hubspot_url,
            "raw_text": raw_text,
        }

    def call_hubspot_mcp_tool_readonly_test(
        self,
        *,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tool_name = str(tool_name or "").strip()
        arguments = arguments or {}

        allowed = {
            "get_user_details",
            "get_properties",
            "search_properties",
            "search_crm_objects",
            "get_crm_objects",
            "tool_guidance",
        }

        if tool_name not in allowed:
            return {
                "ok": False,
                "reason": "tool_not_allowed_for_readonly_test",
                "error": f"Tool {tool_name} is not allowed on this read-only test endpoint.",
                "allowed": sorted(allowed),
                "at": utc_now_iso(),
            }

        self._append_audit(
            event_type="local_node.hubspot_mcp_readonly_tool_call_started",
            message="HubSpot MCP read-only tool call started",
            payload={
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

        try:
            response = self._hubspot_mcp_tools_call(
                name=tool_name,
                arguments=arguments,
                request_id=30,
            )

            self._append_audit(
                event_type="local_node.hubspot_mcp_readonly_tool_call_completed",
                message="HubSpot MCP read-only tool call completed",
                payload={
                    "tool_name": tool_name,
                    "has_error": "error" in response,
                },
            )

            return {
                "ok": "error" not in response,
                "tool_name": tool_name,
                "response": response,
                "at": utc_now_iso(),
            }

        except Exception as exc:
            error = str(exc)

            self._append_audit(
                event_type="local_node.hubspot_mcp_readonly_tool_call_failed",
                message="HubSpot MCP read-only tool call failed",
                payload={
                    "tool_name": tool_name,
                    "error": error,
                },
                level="error",
            )

            return {
                "ok": False,
                "reason": "hubspot_mcp_readonly_tool_call_failed",
                "tool_name": tool_name,
                "error": error,
                "at": utc_now_iso(),
            }

    def execute_train_task_approval_hubspot_mcp_write(
        self,
        *,
        approval_id: str,
        executed_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        approval_id = str(approval_id or "").strip()

        if not approval_id:
            return {
                "ok": False,
                "error": "approval_id is required",
                "at": utc_now_iso(),
            }

        approval = self.train_task_approval_store.get_approval(
            self.config.workspace_id,
            approval_id,
        )

        if not approval:
            return {
                "ok": False,
                "error": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        workflow_id = str(approval.get("workflow_id") or "")
        workflow_name = str(approval.get("workflow_name") or workflow_id)
        run_id = str(approval.get("run_id") or "")

        def fail(reason: str, error: str, level: str = "warning") -> Dict[str, Any]:
            updated = {
                **approval,
                "hubspot_write_executed": False,
                "hubspot_write_blocked": True,
                "hubspot_write_block_reason": reason,
                "hubspot_write_error": error,
                "hubspot_write_attempted_at": utc_now_iso(),
                "hubspot_write_mode": "mcp",
            }

            saved = self.train_task_approval_store.save_approval(
                self.config.workspace_id,
                approval_id,
                updated,
            )

            self._append_audit(
                event_type="local_node.hubspot_mcp_write_failed",
                message="HubSpot MCP write failed or blocked",
                payload={
                    "approval_id": approval_id,
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "reason": reason,
                    "error": error,
                    "hubspot_write_executed": False,
                },
                level=level,
            )

            return {
                "ok": False,
                "approval_id": approval_id,
                "reason": reason,
                "error": error,
                "item": saved,
                "hubspot_write_executed": False,
                "at": utc_now_iso(),
            }

        if str(approval.get("status") or "") not in {"approved", "draft_created"}:
            return fail(
                "approval_not_approved",
                "Approval must be approved before HubSpot MCP write.",
            )

        if approval.get("hubspot_write_executed") is True:
            return {
                "ok": False,
                "approval_id": approval_id,
                "reason": "already_executed",
                "error": "HubSpot write already executed for this approval.",
                "hubspot_contact_result": approval.get("hubspot_contact_result"),
                "hubspot_write_executed": True,
                "at": utc_now_iso(),
            }

        health = self.get_hubspot_connector_health()

        if health.get("auth_status") != "connected":
            return fail(
                "hubspot_mcp_not_connected",
                "HubSpot MCP connector is not connected.",
            )

        if health.get("connector_health") != "available":
            return fail(
                "hubspot_mcp_unavailable",
                "HubSpot MCP connector is not available.",
            )

        if health.get("dry_run_only") is True:
            return fail(
                "hubspot_mcp_dry_run_only",
                "HubSpot MCP connector is still dry-run only.",
            )

        if health.get("external_writes_enabled") is not True:
            return fail(
                "hubspot_mcp_external_writes_disabled",
                "HubSpot MCP external writes are disabled.",
            )

        crm_payload = approval.get("crm_payload") or {}
        mapped = self._map_crm_payload_to_hubspot_mcp_contact(crm_payload)

        email = str(mapped.get("email") or "").strip()
        if not email or "@" not in email:
            return fail(
                "invalid_contact_payload",
                "Valid contact email is required for HubSpot MCP write.",
            )

        properties = {
            "email": email,
        }

        for key in ["firstname", "phone", "company"]:
            value = str(mapped.get(key) or "").strip()
            if value:
                properties[key] = value

        arguments = {
            "createRequest": {
                "objects": [
                    {
                        "objectType": "contacts",
                        "properties": properties,
                    }
                ]
            },
            "confirmationState": "CONFIRMED",
        }

        self._append_audit(
            event_type="local_node.hubspot_mcp_write_started",
            message="HubSpot MCP contact write started",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "tool_name": "manage_crm_objects",
                "email": email,
                "properties": properties,
                "executed_by": executed_by,
            },
        )

        try:
            mcp_response = self._hubspot_mcp_tools_call(
                name="manage_crm_objects",
                arguments=arguments,
                request_id=20,
            )

            if "error" in mcp_response:
                return fail(
                    "hubspot_mcp_tool_error",
                    str(mcp_response.get("error")),
                    level="error",
                )

            reference = self._extract_hubspot_mcp_contact_reference(mcp_response)

            contact_result = {
                "ok": True,
                "tool_name": "manage_crm_objects",
                "action": "created_or_updated",
                "contact_id": reference.get("contact_id") or "",
                "hubspot_url": reference.get("hubspot_url") or "",
                "properties": properties,
                "mcp_response": mcp_response,
                "raw_text": reference.get("raw_text") or "",
            }

            updated = {
                **approval,
                "status": "hubspot_written",
                "hubspot_write_mode": "mcp",
                "hubspot_write_executed": True,
                "hubspot_write_blocked": False,
                "hubspot_contact_result": contact_result,
                "hubspot_contact_id": contact_result["contact_id"],
                "hubspot_url": contact_result["hubspot_url"],
                "hubspot_mcp_write_result": mcp_response,
                "hubspot_write_executed_at": utc_now_iso(),
                "hubspot_write_executed_by": executed_by,
            }

            saved = self.train_task_approval_store.save_approval(
                self.config.workspace_id,
                approval_id,
                updated,
            )

            self._append_audit(
                event_type="local_node.hubspot_mcp_contact_written",
                message="HubSpot MCP contact write completed",
                payload={
                    "approval_id": approval_id,
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "tool_name": "manage_crm_objects",
                    "contact_id": contact_result["contact_id"],
                    "hubspot_url": contact_result["hubspot_url"],
                    "email": email,
                    "hubspot_write_executed": True,
                },
            )

            return {
                "ok": True,
                "approval_id": approval_id,
                "action": "created_or_updated",
                "tool_name": "manage_crm_objects",
                "contact_id": contact_result["contact_id"],
                "hubspot_url": contact_result["hubspot_url"],
                "hubspot_contact_result": contact_result,
                "item": saved,
                "hubspot_write_executed": True,
                "at": utc_now_iso(),
            }

        except Exception as exc:
            return fail(
                "hubspot_mcp_api_error",
                str(exc),
                level="error",
            )

    def _map_crm_payload_to_hubspot_mcp_contact(
        self,
        crm_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        field_mapping = crm_payload.get("field_mapping") or {}

        if not isinstance(field_mapping, dict):
            field_mapping = {}

        return {
            "email": str(field_mapping.get("email") or "").strip(),
            "firstname": str(field_mapping.get("firstname") or field_mapping.get("name") or "").strip(),
            "phone": str(field_mapping.get("phone") or "").strip(),
            "company": str(field_mapping.get("company") or "").strip(),
            "message": str(field_mapping.get("message") or "").strip(),
        }

    def dry_run_train_task_approval_hubspot_mcp(
        self,
        *,
        approval_id: str,
        executed_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        approval_id = str(approval_id or "").strip()

        if not approval_id:
            return {
                "ok": False,
                "error": "approval_id is required",
                "at": utc_now_iso(),
            }

        approval = self.train_task_approval_store.get_approval(
            self.config.workspace_id,
            approval_id,
        )

        if not approval:
            return {
                "ok": False,
                "error": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        workflow_id = str(approval.get("workflow_id") or "")
        workflow_name = str(approval.get("workflow_name") or workflow_id)
        run_id = str(approval.get("run_id") or "")
        crm_payload = approval.get("crm_payload") or {}

        mapped_payload = self._map_crm_payload_to_hubspot_mcp_contact(crm_payload)

        result = self.dry_run_external_tool(
            tool_id="tool.mcp.hubspot.contact_upsert.v1",
            payload=mapped_payload,
            workflow_id=workflow_id,
            run_id=run_id,
        )

        updated = {
            **approval,
            "hubspot_mcp_dry_run_result": result,
            "hubspot_mcp_payload": mapped_payload,
            "hubspot_mcp_dry_run_at": utc_now_iso(),
            "hubspot_mcp_executed_by": executed_by,
            "hubspot_write_executed": False,
            "hubspot_write_blocked": True,
            "hubspot_write_block_reason": "phase_6d_mcp_dry_run_only",
        }

        saved = self.train_task_approval_store.save_approval(
            self.config.workspace_id,
            approval_id,
            updated,
        )

        self._append_audit(
            event_type="local_node.hubspot_mcp_contact_dry_run_completed",
            message="HubSpot MCP contact dry-run completed",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "tool_id": "tool.mcp.hubspot.contact_upsert.v1",
                "email": mapped_payload.get("email"),
                "dry_run": True,
                "external_write_blocked": True,
                "hubspot_write_executed": False,
            },
        )

        return {
            "ok": result.get("ok") is True,
            "approval_id": approval_id,
            "tool_id": "tool.mcp.hubspot.contact_upsert.v1",
            "mapped_payload": mapped_payload,
            "dry_run_result": result,
            "item": saved,
            "dry_run": True,
            "external_write_blocked": True,
            "hubspot_write_executed": False,
            "at": utc_now_iso(),
        }

    def execute_train_task_approval_hubspot_write(
        self,
        *,
        approval_id: str,
        executed_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        approval_id = str(approval_id or "").strip()

        if not approval_id:
            return {
                "ok": False,
                "error": "approval_id is required",
                "at": utc_now_iso(),
            }

        approval = self.train_task_approval_store.get_approval(
            self.config.workspace_id,
            approval_id,
        )

        if not approval:
            return {
                "ok": False,
                "error": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        workflow_id = str(approval.get("workflow_id") or "")
        workflow_name = str(approval.get("workflow_name") or workflow_id)
        run_id = str(approval.get("run_id") or "")
        crm_payload = approval.get("crm_payload") or {}

        self._append_audit(
            event_type="local_node.hubspot_write_started",
            message="HubSpot write attempt started",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "executed_by": executed_by,
                "dry_run": False,
            },
        )

        def block(reason: str, error: str) -> Dict[str, Any]:
            updated = {
                **approval,
                "hubspot_write_executed": False,
                "hubspot_write_blocked": True,
                "hubspot_write_block_reason": reason,
                "hubspot_write_error": error,
                "hubspot_write_attempted_at": utc_now_iso(),
            }

            saved = self.train_task_approval_store.save_approval(
                self.config.workspace_id,
                approval_id,
                updated,
            )

            self._append_audit(
                event_type="local_node.hubspot_write_failed",
                message="HubSpot write blocked or failed",
                payload={
                    "approval_id": approval_id,
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "reason": reason,
                    "error": error,
                    "hubspot_write_executed": False,
                },
                level="warning",
            )

            return {
                "ok": False,
                "approval_id": approval_id,
                "reason": reason,
                "error": error,
                "item": saved,
                "hubspot_write_executed": False,
                "at": utc_now_iso(),
            }

        if str(approval.get("status") or "") not in {"approved", "draft_created"}:
            return block(
                "approval_not_approved",
                "Approval must be approved before HubSpot write.",
            )

        if approval.get("hubspot_write_executed") is True:
            return {
                "ok": False,
                "approval_id": approval_id,
                "reason": "already_executed",
                "error": "HubSpot write already executed for this approval.",
                "hubspot_contact_result": approval.get("hubspot_contact_result"),
                "hubspot_write_executed": True,
                "at": utc_now_iso(),
            }

        health = self.get_hubspot_connector_health()

        if health.get("auth_status") != "connected":
            return block(
                "hubspot_not_connected",
                "HubSpot connector is not connected.",
            )

        if health.get("connector_health") != "available":
            return block(
                "hubspot_unavailable",
                "HubSpot connector is not available.",
            )

        if health.get("dry_run_only") is True:
            return block(
                "hubspot_dry_run_only",
                "HubSpot connector is still dry-run only.",
            )

        if health.get("external_writes_enabled") is not True:
            return block(
                "hubspot_external_writes_disabled",
                "HubSpot external writes are disabled.",
            )

        email = ""
        field_mapping = crm_payload.get("field_mapping") or {}
        if isinstance(field_mapping, dict):
            email = str(field_mapping.get("email") or "").strip()

        if not email or "@" not in email:
            return block(
                "invalid_contact_payload",
                "Valid contact email is required for HubSpot write.",
            )

        # Phase 6B intentionally stops here. Real HubSpot API write is Phase 6C.
        return block(
            "hubspot_real_api_not_enabled",
            "HubSpot connector gates passed, but real HubSpot API write is not enabled until Phase 6C.",
        )

    def execute_train_task_approval_gmail_draft(
        self,
        *,
        approval_id: str,
        executed_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        approval_id = str(approval_id or "").strip()

        if not approval_id:
            return {
                "ok": False,
                "error": "approval_id is required",
                "at": utc_now_iso(),
            }

        approval = self.train_task_approval_store.get_approval(
            self.config.workspace_id,
            approval_id,
        )

        if not approval:
            return {
                "ok": False,
                "error": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        if str(approval.get("status") or "") != "approved":
            return {
                "ok": False,
                "error": "Approval must be approved before Gmail draft creation",
                "approval_id": approval_id,
                "status": approval.get("status"),
                "at": utc_now_iso(),
            }

        if approval.get("gmail_draft_created") is True:
            return {
                "ok": False,
                "error": "Gmail draft already created for this approval",
                "approval_id": approval_id,
                "draft_result": approval.get("gmail_draft_result"),
                "at": utc_now_iso(),
            }

        gmail_draft = approval.get("gmail_draft") or {}
        workflow_id = str(approval.get("workflow_id") or "")
        workflow_name = str(approval.get("workflow_name") or workflow_id)
        run_id = str(approval.get("run_id") or "")

        self._append_audit(
            event_type="local_node.gmail_draft_creation_started",
            message="Gmail draft creation started",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "to": gmail_draft.get("to"),
                "subject": gmail_draft.get("subject"),
                "sent": False,
            },
        )

        try:
            result = self._create_gmail_draft(
                to=str(gmail_draft.get("to") or ""),
                subject=str(gmail_draft.get("subject") or ""),
                body=str(gmail_draft.get("body") or ""),
                cc=str(gmail_draft.get("cc") or ""),
                bcc=str(gmail_draft.get("bcc") or ""),
                thread_id=str(gmail_draft.get("thread_id") or ""),
            )
        except Exception as exc:
            error = str(exc)

            updated = {
                **approval,
                "gmail_draft_created": False,
                "gmail_draft_failed": True,
                "gmail_draft_error": error,
                "status": "failed",
                "failed_at": utc_now_iso(),
            }

            saved = self.train_task_approval_store.save_approval(
                self.config.workspace_id,
                approval_id,
                updated,
            )

            self._append_audit(
                event_type="local_node.gmail_draft_creation_failed",
                message="Gmail draft creation failed",
                payload={
                    "approval_id": approval_id,
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "error": error,
                    "sent": False,
                },
                level="error",
            )

            return {
                "ok": False,
                "approval_id": approval_id,
                "error": error,
                "item": saved,
                "sent": False,
                "at": utc_now_iso(),
            }

        updated = {
            **approval,
            "gmail_draft_created": True,
            "gmail_draft_failed": False,
            "gmail_draft_result": result,
            "status": "draft_created",
            "executed_by": executed_by,
            "executed_at": utc_now_iso(),
            "external_writes_executed": True,
            "external_write_type": "gmail_draft_create",
            "hubspot_write_executed": False,
            "sent_email": False,
        }

        saved = self.train_task_approval_store.save_approval(
            self.config.workspace_id,
            approval_id,
            updated,
        )

        self._append_audit(
            event_type="local_node.gmail_draft_created",
            message="Gmail draft created",
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "draft_id": result.get("draft_id"),
                "message_id": result.get("message_id"),
                "gmail_url": result.get("gmail_url"),
                "sent": False,
                "hubspot_write_executed": False,
            },
        )

        return {
            "ok": True,
            "approval_id": approval_id,
            "draft_result": result,
            "item": saved,
            "sent": False,
            "hubspot_write_executed": False,
            "at": utc_now_iso(),
        }

    def prepare_pilot_email_send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        requested_by: str = "aion_central_pilot",
    ) -> Dict[str, Any]:
        """Freeze an exact email payload for a separate, explicit send approval."""
        from email.utils import getaddresses

        to = str(to or "").strip()
        subject = str(subject or "").strip()
        body = str(body or "")
        cc = str(cc or "").strip()
        bcc = str(bcc or "").strip()
        recipient_headers = [value for value in (to, cc, bcc) if value]
        recipients = [address for _, address in getaddresses(recipient_headers) if address]
        if not recipients or not to or any("@" not in address for address in recipients):
            return {"ok": False, "reason": "valid_recipient_required", "sent": False, "at": utc_now_iso()}
        if not body.strip():
            return {"ok": False, "reason": "email_body_required", "sent": False, "at": utc_now_iso()}

        payload = {"to": to, "subject": subject or "Message from Aion", "body": body, "cc": cc, "bcc": bcc}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload_hash = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        approval_id = f"approval_pilot_email_{uuid4().hex[:16]}"
        authority = self.pilot_authority_policy.evaluate(self.config.workspace_id, "email_send")
        if authority.get("decision") == "blocked_by_owner" and authority.get("ask_user") is False:
            self._append_audit(
                event_type="local_node.pilot_email_send_blocked_by_owner",
                message="Pilot email send suppressed by the owner's standing authority policy",
                payload={"payload_hash": payload_hash, "to": to, "subject": payload["subject"], "sent": False},
            )
            return {
                "ok": False,
                "reason": "blocked_by_owner",
                "authority": authority,
                "payload_hash": payload_hash,
                "sent": False,
                "at": utc_now_iso(),
            }
        record = {
            "approval_id": approval_id,
            "approval_type": "pilot_email_send",
            "title": f"Send email to {to}",
            "description": "Exact Gmail payload prepared by AION Central Pilot. It may be sent once by explicit approval or valid standing authority.",
            "gmail_message": payload,
            "payload_hash": payload_hash,
            "status": "standing_authority_ready" if authority.get("authorized") else "pending_exact_payload_approval",
            "authority_decision": authority,
            "requested_by": requested_by,
            "created_at": utc_now_iso(),
            "sent_email": False,
            "external_write_type": "gmail_send_message",
        }
        saved = self.train_task_approval_store.save_approval(self.config.workspace_id, approval_id, record)
        self._append_audit(
            event_type="local_node.pilot_email_send_prepared",
            message="Pilot email exact payload prepared",
            payload={"approval_id": approval_id, "payload_hash": payload_hash, "to": to, "subject": payload["subject"], "sent": False},
        )
        return {"ok": True, "approval_id": approval_id, "payload_hash": payload_hash, "message": payload, "item": saved, "authority": authority, "sent": False, "at": utc_now_iso()}

    def execute_pilot_email_send(
        self,
        *,
        approval_id: str,
        payload_hash: str,
        executed_by: str = "aion_central_pilot",
        approval_granted: bool = False,
    ) -> Dict[str, Any]:
        """Send one previously frozen Gmail payload once, after exact approval."""
        approval = self.train_task_approval_store.get_approval(self.config.workspace_id, str(approval_id or "").strip())
        if not approval or approval.get("approval_type") != "pilot_email_send":
            return {"ok": False, "reason": "approval_not_found", "sent": False, "at": utc_now_iso()}
        if approval.get("sent_email") is True or approval.get("status") == "executed":
            return {"ok": False, "reason": "already_sent", "sent": False, "result": approval.get("gmail_send_result"), "at": utc_now_iso()}
        if approval.get("status") not in {"pending_exact_payload_approval", "standing_authority_ready"}:
            return {"ok": False, "reason": "approval_not_pending", "sent": False, "at": utc_now_iso()}
        if str(payload_hash or "") != str(approval.get("payload_hash") or ""):
            return {"ok": False, "reason": "payload_hash_mismatch", "sent": False, "at": utc_now_iso()}

        authority = self.pilot_authority_policy.evaluate(self.config.workspace_id, "email_send")
        if not approval_granted and not authority.get("authorized"):
            return {"ok": False, "reason": "exact_approval_required", "authority": authority, "sent": False, "at": utc_now_iso()}

        health = self.get_gmail_connector_health()
        if str(health.get("auth_status") or "") != "connected":
            return {"ok": False, "reason": "gmail_not_connected", "health": health, "sent": False, "at": utc_now_iso()}

        message = approval.get("gmail_message") or {}
        try:
            result = self._send_gmail_message(
                to=str(message.get("to") or ""), subject=str(message.get("subject") or ""), body=str(message.get("body") or ""),
                cc=str(message.get("cc") or ""), bcc=str(message.get("bcc") or ""),
            )
        except Exception as exc:
            self._append_audit(event_type="local_node.pilot_email_send_failed", message="Pilot Gmail send failed", payload={"approval_id": approval_id, "error": str(exc), "sent": False}, level="error")
            return {"ok": False, "reason": "gmail_send_failed", "error": str(exc), "sent": False, "at": utc_now_iso()}

        completed_at = utc_now_iso()
        receipt_payload = {"approval_id": approval_id, "payload_hash": payload_hash, "message_id": result.get("message_id"), "thread_id": result.get("thread_id"), "sent_at": completed_at}
        receipt_hash = f"sha256:{hashlib.sha256(json.dumps(receipt_payload, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()}"
        updated = {**approval, "status": "executed", "sent_email": True, "executed_by": executed_by, "executed_at": completed_at, "gmail_send_result": result, "receipt_hash": receipt_hash}
        self.train_task_approval_store.save_approval(self.config.workspace_id, approval_id, updated)
        self._append_audit(event_type="local_node.pilot_email_sent", message="Pilot email sent after exact approval", payload={**receipt_payload, "receipt_hash": receipt_hash, "sent": True})
        return {"ok": True, "approval_id": approval_id, "payload_hash": payload_hash, "receipt_hash": receipt_hash, "result": result, "sent": True, "at": completed_at}

    def get_pilot_authority_policy(self) -> Dict[str, Any]:
        return {"ok": True, **self.pilot_authority_policy.get(self.config.workspace_id), "at": utc_now_iso()}

    def update_pilot_authority_policy(self, updates: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        try:
            payload = self.pilot_authority_policy.update(self.config.workspace_id, updates, updated_by)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "at": utc_now_iso()}
        self._append_audit(
            event_type="local_node.pilot_authority_updated",
            message="Pilot standing authority policy updated",
            payload={"updated_by": updated_by, "actions": sorted((updates or {}).keys())},
        )
        return {"ok": True, **payload, "at": utc_now_iso()}

    def resolve_train_task_approval(
        self,
        *,
        approval_id: str,
        approve: bool,
        resolved_by: str = "operations_agents_desktop",
        resolution_note: str = "",
    ) -> Dict[str, Any]:
        approval_id = str(approval_id or "").strip()

        if not approval_id:
            return {
                "ok": False,
                "error": "approval_id is required",
                "at": utc_now_iso(),
            }

        approval = self.train_task_approval_store.get_approval(
            self.config.workspace_id,
            approval_id,
        )

        if not approval:
            return {
                "ok": False,
                "error": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        current_status = str(approval.get("status") or "pending")
        if current_status != "pending":
            return {
                "ok": False,
                "error": f"Approval is already {current_status}",
                "approval_id": approval_id,
                "status": current_status,
                "item": approval,
                "at": utc_now_iso(),
            }

        now = utc_now_iso()
        decision = "approved" if approve else "rejected"
        next_status = decision

        updated = {
            **approval,
            "status": next_status,
            "decision": decision,
            "resolved_by": resolved_by or "operations_agents_desktop",
            "resolved_at": now,
            "resolution_note": resolution_note or "",
            "external_writes_executed": False,
            "phase_3_note": (
                "Approval decision stored only. Phase 3C does not execute Gmail drafts "
                "or HubSpot writes."
            ),
        }

        saved = self.train_task_approval_store.save_approval(
            self.config.workspace_id,
            approval_id,
            updated,
        )

        workflow_id = str(saved.get("workflow_id") or "")
        workflow_name = str(saved.get("workflow_name") or workflow_id)
        run_id = str(saved.get("run_id") or "")

        decision_event = (
            "local_node.train_task_approval_approved"
            if approve
            else "local_node.train_task_approval_rejected"
        )
        flow_event = (
            "local_node.train_task_workflow_resumed_after_approval"
            if approve
            else "local_node.train_task_workflow_stopped_after_rejection"
        )

        self._append_audit(
            event_type=decision_event,
            message=(
                "Train-task approval approved"
                if approve
                else "Train-task approval rejected"
            ),
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "decision": decision,
                "resolved_by": resolved_by,
                "resolution_note": resolution_note or "",
                "external_writes_executed": False,
            },
        )

        self._append_audit(
            event_type=flow_event,
            message=(
                "Train-task workflow marked ready to resume after approval"
                if approve
                else "Train-task workflow stopped after rejection"
            ),
            payload={
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "decision": decision,
                "external_writes_executed": False,
                "phase": "phase_3_decision_only",
            },
        )

        return {
            "ok": True,
            "approval_id": approval_id,
            "decision": decision,
            "status": next_status,
            "item": saved,
            "external_writes_executed": False,
            "at": now,
        }

    def list_train_task_runs(self, limit: int = 50) -> Dict[str, Any]:
        return {
            "ok": True,
            "items": self.train_task_store.list_runs(self.config.workspace_id, limit=limit),
            "at": utc_now_iso(),
        }

    @staticmethod
    def _gmail_message_text(message: Dict[str, Any]) -> str:
        return " ".join(
            [
                str(message.get("from") or ""),
                str(message.get("sender") or ""),
                str(message.get("subject") or ""),
                str(message.get("body") or ""),
                str(message.get("snippet") or ""),
            ]
        ).lower()

    @classmethod
    def _gmail_message_matches_query(
        cls,
        message: Dict[str, Any],
        query: str,
    ) -> bool:
        q = str(query or "is:unread").strip().lower()
        if not q or q == "is:unread":
            return True

        text = cls._gmail_message_text(message)
        subject = str(message.get("subject") or "").lower()
        sender = str(message.get("from") or message.get("sender") or "").lower()

        terms = [part.strip() for part in q.split() if part.strip()]
        meaningful_terms = []

        for term in terms:
            if term == "is:unread":
                continue

            if term.startswith("from:"):
                expected = term.replace("from:", "", 1).strip().strip('"')
                if expected and expected not in sender:
                    return False
                continue

            if term.startswith("subject:"):
                expected = term.replace("subject:", "", 1).strip().strip('"')
                if expected and expected not in subject:
                    return False
                continue

            meaningful_terms.append(term.strip('"'))

        if not meaningful_terms:
            return True

        return all(term in text for term in meaningful_terms)

    def _refresh_gmail_access_token_if_needed(self, *, force: bool = False) -> Dict[str, Any]:
        import json
        import os
        import time
        import urllib.error
        import urllib.parse
        import urllib.request

        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        token_payload = self.connector_registry.load_gmail_token_payload()
        if not token_payload:
            raise RuntimeError("No Gmail token payload found")

        access_token = str(token_payload.get("access_token") or "")
        refresh_token = str(token_payload.get("refresh_token") or "")
        expires_in = int(token_payload.get("expires_in") or 0)
        stored_at = str(token_payload.get("stored_at") or "")
        expires_at = token_payload.get("expires_at")

        now_epoch = int(time.time())

        if not expires_at and not force:
            # Conservative default: if we do not know exact expiry, use current access token.
            # If Google rejects it, caller will fail safely.
            return token_payload

        try:
            expires_at_int = int(expires_at)
        except Exception:
            expires_at_int = 0

        if not force and access_token and expires_at_int and now_epoch < (expires_at_int - 120):
            return token_payload

        if not refresh_token:
            return token_payload

        client_id = str(os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        client_secret = str(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()

        if not client_id or not client_secret:
            raise RuntimeError("Google OAuth client config missing for token refresh")

        body = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                refreshed = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"gmail_oauth_refresh_failed:{exc.code}") from exc

        next_payload = {
            **token_payload,
            **refreshed,
            "refresh_token": refresh_token,
            "expires_at": int(time.time()) + int(refreshed.get("expires_in") or 3600),
        }

        self.connector_registry.save_gmail_token_payload(next_payload)
        return next_payload

    def _gmail_api_get_json(self, url: str, access_token: str) -> Dict[str, Any]:
        import json
        import urllib.request

        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            try:
                body = exc.read().decode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                body = ""
            if body:
                raise RuntimeError(f"{exc}: {body}") from exc
            raise

    def _extract_gmail_header(self, message: Dict[str, Any], name: str) -> str:
        payload = message.get("payload") or {}
        headers = payload.get("headers") or []

        for header in headers:
            if str(header.get("name") or "").lower() == name.lower():
                return str(header.get("value") or "")

        return ""

    def _decode_gmail_body_part(self, part: Dict[str, Any]) -> str:
        import base64

        body = part.get("body") or {}
        data = body.get("data")
        if not data:
            return ""

        try:
            padded = str(data) + "=" * (-len(str(data)) % 4)
            return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            return ""

    def _extract_gmail_message_body(self, message: Dict[str, Any]) -> str:
        payload = message.get("payload") or {}

        direct = self._decode_gmail_body_part(payload)
        if direct:
            return direct

        stack = list(payload.get("parts") or [])
        collected: List[str] = []

        while stack:
            part = stack.pop(0)
            mime_type = str(part.get("mimeType") or "")

            if mime_type in {"text/plain", "text/html"}:
                text = self._decode_gmail_body_part(part)
                if text:
                    collected.append(text)

            nested = part.get("parts") or []
            if nested:
                stack.extend(nested)

        if collected:
            return "\n\n".join(collected)

        return str(message.get("snippet") or "")

    def _gmail_message_to_sample_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
        message_id = str(message.get("id") or "")
        sender = self._extract_gmail_header(message, "From")
        subject = self._extract_gmail_header(message, "Subject")
        body = self._extract_gmail_message_body(message)

        return {
            "id": message_id,
            "thread_id": message.get("threadId"),
            "from": sender,
            "subject": subject,
            "body": body,
            "snippet": message.get("snippet"),
            "source": "gmail_live_readonly",
        }

    def _is_broad_gmail_query(self, query: str) -> bool:
        normalized = " ".join(str(query or "").lower().strip().split())

        broad_queries = {
            "",
            "is:unread",
            "in:inbox",
            "in:inbox is:unread",
            "is:unread in:inbox",
        }

        if normalized in broad_queries:
            return True

        # Allow only if there is at least one meaningful extra constraint.
        extra_indicators = [
            "from:",
            "to:",
            "subject:",
            "label:",
            "category:",
            "newer_than:",
            "older_than:",
            "after:",
            "before:",
            "{",
            "(",
            '"',
        ]

        if any(token in normalized for token in extra_indicators):
            return False

        terms = [
            part
            for part in normalized.replace("(", " ").replace(")", " ").split()
            if part not in {"is:unread", "in:inbox", "in:anywhere"}
        ]

        return len(terms) == 0

    def _get_enabled_gmail_workflows_for_live_poll(self) -> List[Dict[str, Any]]:
        workflows = self.train_task_store.list_workflows(self.config.workspace_id)
        items: List[Dict[str, Any]] = []

        for workflow in workflows:
            if workflow.get("enabled") is not True:
                continue

            trigger = workflow.get("trigger") or {}
            if trigger.get("trigger_type") != "gmail_message_match":
                continue

            items.append(workflow)

        return items

    def _gmail_api_post_json(
        self,
        url: str,
        access_token: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        import json
        import urllib.request

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            try:
                body = exc.read().decode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                body = ""
            if body:
                raise RuntimeError(f"{exc}: {body}") from exc
            raise

    def _create_gmail_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        thread_id: str = "",
    ) -> Dict[str, Any]:
        import base64
        from email.message import EmailMessage

        token_payload = self._refresh_gmail_access_token_if_needed()
        access_token = str(token_payload.get("access_token") or "")

        if not access_token:
            raise RuntimeError("Gmail access token missing")

        to = str(to or "").strip()
        subject = str(subject or "").strip()
        body = str(body or "")

        if not to or "@" not in to:
            raise ValueError("Valid Gmail draft recipient is required")

        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject or "Draft from Aion"

        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        msg.set_content(body)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        payload: Dict[str, Any] = {
            "message": {
                "raw": raw,
            }
        }

        if thread_id:
            payload["message"]["threadId"] = thread_id

        result = self._gmail_api_post_json(
            "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            access_token,
            payload,
        )

        draft_id = result.get("id")
        message = result.get("message") or {}
        message_id = message.get("id")

        return {
            "ok": True,
            "draft_id": draft_id,
            "message_id": message_id,
            "thread_id": message.get("threadId") or thread_id,
            "gmail_url": "https://mail.google.com/mail/u/0/#drafts",
            "to": to,
            "subject": subject,
            "created": True,
            "sent": False,
            "external_write": True,
            "tool_id": "tool.gmail.create_draft.v1",
            "action_type": "gmail_create_draft",
        }

    def _send_gmail_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
    ) -> Dict[str, Any]:
        import base64
        from email.message import EmailMessage

        token_payload = self._refresh_gmail_access_token_if_needed()
        access_token = str(token_payload.get("access_token") or "")
        if not access_token:
            raise RuntimeError("Gmail access token missing")
        if not to or "@" not in to:
            raise ValueError("Valid Gmail recipient is required")
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject or "Message from Aion"
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = self._gmail_api_post_json("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", access_token, {"raw": raw})
        return {"ok": True, "message_id": result.get("id"), "thread_id": result.get("threadId"), "gmail_url": "https://mail.google.com/mail/u/0/#sent", "to": to, "subject": subject, "sent": True, "external_write": True, "tool_id": "tool.gmail.send_message.v1", "action_type": "gmail_send_message"}

    def _create_google_calendar_event(
        self,
        *,
        summary: str,
        description: str,
        starts_at: str,
        ends_at: str,
        calendar_id: str = "primary",
        location: str = "",
    ) -> Dict[str, Any]:
        """Create one approved Calendar event without inviting or notifying guests."""
        import urllib.parse

        token_payload = self._refresh_gmail_access_token_if_needed()
        access_token = str(token_payload.get("access_token") or "")
        if not access_token:
            raise RuntimeError("Google Workspace access token missing")
        if not summary or not starts_at or not ends_at:
            raise ValueError("Calendar event summary, start and end are required")
        payload = {
            "summary": str(summary).strip()[:500],
            "description": str(description or "").strip()[:4000],
            "start": {"dateTime": starts_at},
            "end": {"dateTime": ends_at},
        }
        if str(location or "").strip():
            payload["location"] = str(location).strip()[:500]
        encoded_calendar = urllib.parse.quote(str(calendar_id or "primary"), safe="")
        result = self._gmail_api_post_json(
            f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar}/events?sendUpdates=none",
            access_token,
            payload,
        )
        return {
            "ok": True,
            "created": bool(result.get("id")),
            "event_id": result.get("id"),
            "html_link": result.get("htmlLink"),
            "status": result.get("status"),
            "calendar_id": calendar_id or "primary",
            "attendees_notified": False,
            "external_write": True,
            "action_type": "google_calendar_event_create",
        }

    def _fetch_gmail_unread_messages(
        self,
        *,
        query: str = "in:inbox is:unread",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        import urllib.parse

        token_payload = self._refresh_gmail_access_token_if_needed()
        access_token = str(token_payload.get("access_token") or "")

        if not access_token:
            raise RuntimeError("Gmail access token missing")

        list_url = (
            "https://gmail.googleapis.com/gmail/v1/users/me/messages?"
            + urllib.parse.urlencode(
                {
                    "q": query or "in:inbox is:unread",
                    "maxResults": max(1, min(int(max_results or 10), 25)),
                }
            )
        )

        try:
            listed = self._gmail_api_get_json(list_url, access_token)
        except RuntimeError as exc:
            if "401" not in str(exc):
                raise
            token_payload = self._refresh_gmail_access_token_if_needed(force=True)
            access_token = str(token_payload.get("access_token") or "")
            if not access_token:
                raise RuntimeError("Gmail access token refresh returned no access token") from exc
            listed = self._gmail_api_get_json(list_url, access_token)
        refs = listed.get("messages") or []

        messages: List[Dict[str, Any]] = []
        for ref in refs:
            message_id = ref.get("id")
            if not message_id:
                continue

            get_url = (
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
                + urllib.parse.quote(str(message_id))
                + "?"
                + urllib.parse.urlencode({"format": "full"})
            )

            full_message = self._gmail_api_get_json(get_url, access_token)
            messages.append(self._gmail_message_to_sample_email(full_message))

        return messages

    def fetch_gmail_messages_readonly(
        self,
        *,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Read a deliberately narrow Gmail result set without changing Gmail state."""
        if self._is_broad_gmail_query(query):
            raise ValueError("broad_gmail_query_blocked")
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))
        health = self.connector_registry.gmail_health()
        if health.get("auth_status") != "connected":
            raise PermissionError("gmail_connector_not_connected")
        try:
            messages = self._fetch_gmail_unread_messages(query=query, max_results=max_results)
        except RuntimeError as exc:
            if "gmail_oauth_refresh_failed" in str(exc):
                self.connector_registry.save_gmail_config({
                    "auth_status": "reauthorization_required", "last_poll_at": utc_now_iso(),
                    "last_poll_status": "failed_reauthorization_required",
                    "last_error": "Gmail OAuth permission must be reconnected.",
                })
                raise PermissionError("gmail_reauthorization_required") from exc
            raise
        self._append_audit(
            event_type="local_node.gmail_sales_intake_read",
            message="Readonly Gmail messages fetched for canonical Sales intake",
            payload={"query": query, "message_count": len(messages),
                     "gmail_mutated": False, "reply_sent": False},
        )
        return messages

    def poll_train_task_gmail_now(self) -> Dict[str, Any]:
        """
        Phase 2C live Gmail polling wrapper.

        This does not fetch real Gmail yet unless a future Gmail connector is connected.
        It safely checks connector config, records poll status, and refuses live polling
        while auth is missing.
        """
        if not hasattr(self, "connector_registry") or self.connector_registry is None:
            self.connector_registry = ConnectorRegistryStore(str(self.base_dir))

        poll_id = f"poll_gmail_live_{uuid4().hex[:10]}"
        health = self.connector_registry.gmail_health()
        auth_status = str(health.get("auth_status") or "not_connected")
        polling_enabled = health.get("polling_enabled") is True

        self._append_audit(
            event_type="local_node.gmail_poll_started",
            message="Live Gmail poll requested",
            payload={
                "poll_id": poll_id,
                "mode": "live_connector_check",
                "auth_status": auth_status,
                "polling_enabled": polling_enabled,
                "dry_run_only": True,
            },
        )

        if not polling_enabled:
            error = "Gmail polling is disabled"
            config = self.connector_registry.save_gmail_config(
                {
                    "last_poll_at": utc_now_iso(),
                    "last_poll_status": "skipped_polling_disabled",
                    "last_error": error,
                }
            )

            self._append_audit(
                event_type="local_node.gmail_poll_failed",
                message="Live Gmail poll skipped: polling disabled",
                payload={
                    "poll_id": poll_id,
                    "error": error,
                    "auth_status": auth_status,
                    "polling_enabled": polling_enabled,
                },
                level="warning",
            )

            return {
                "ok": False,
                "poll_id": poll_id,
                "error": error,
                "reason": "polling_disabled",
                "connector": self.connector_registry.gmail_health(),
                "matched": 0,
                "skipped": 0,
                "deduped": 0,
                "runs": [],
                "dry_run": True,
                "at": utc_now_iso(),
            }

        if auth_status != "connected":
            error = "Gmail connector is not connected"
            config = self.connector_registry.save_gmail_config(
                {
                    "last_poll_at": utc_now_iso(),
                    "last_poll_status": "failed_not_connected",
                    "last_error": error,
                }
            )

            self._append_audit(
                event_type="local_node.gmail_poll_failed",
                message="Live Gmail poll failed: connector not connected",
                payload={
                    "poll_id": poll_id,
                    "error": error,
                    "auth_status": auth_status,
                    "polling_enabled": polling_enabled,
                    "dry_run_only": True,
                },
                level="warning",
            )

            return {
                "ok": False,
                "poll_id": poll_id,
                "error": error,
                "reason": "connector_not_connected",
                "connector": self.connector_registry.gmail_health(),
                "matched": 0,
                "skipped": 0,
                "deduped": 0,
                "runs": [],
                "dry_run": True,
                "at": utc_now_iso(),
            }

        try:
            enabled_gmail_workflows = self._get_enabled_gmail_workflows_for_live_poll()
            blocked_workflows = []

            for workflow in enabled_gmail_workflows:
                trigger = workflow.get("trigger") or {}
                query = str(trigger.get("query") or "").strip()

                if self._is_broad_gmail_query(query):
                    blocked_workflows.append(
                        {
                            "workflow_id": workflow.get("workflow_id") or workflow.get("id"),
                            "workflow_name": workflow.get("name"),
                            "query": query or "is:unread",
                            "reason": "broad_query_blocked",
                        }
                    )

            if blocked_workflows:
                self.connector_registry.save_gmail_config(
                    {
                        "last_poll_at": utc_now_iso(),
                        "last_poll_status": "blocked_broad_query",
                        "last_error": "Live Gmail check blocked because one or more enabled workflows use a broad query.",
                        "dry_run_only": True,
                        "external_writes_enabled": False,
                    }
                )

                self._append_audit(
                    event_type="local_node.gmail_poll_broad_query_blocked",
                    message="Live Gmail poll blocked by broad workflow query",
                    payload={
                        "poll_id": poll_id,
                        "blocked_workflows": blocked_workflows,
                        "dry_run_only": True,
                        "external_writes_enabled": False,
                    },
                    level="warning",
                )

                return {
                    "ok": False,
                    "poll_id": poll_id,
                    "reason": "broad_query_blocked",
                    "error": "Live Gmail check blocked. Enabled workflows need a more specific Gmail query than is:unread.",
                    "blocked_workflows": blocked_workflows,
                    "connector": self.connector_registry.gmail_health(),
                    "matched": 0,
                    "skipped": len(blocked_workflows),
                    "deduped": 0,
                    "runs": [],
                    "dry_run": True,
                    "source": "gmail_live_readonly",
                    "at": utc_now_iso(),
                }

            self._append_audit(
                event_type="local_node.gmail_fetch_attempted",
                message="Readonly Gmail fetch attempted",
                payload={
                    "poll_id": poll_id,
                    "auth_status": auth_status,
                    "polling_enabled": polling_enabled,
                    "workflow_count": len(enabled_gmail_workflows),
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
            )

            live_queries = []
            for workflow in enabled_gmail_workflows:
                trigger = workflow.get("trigger") or {}
                query = str(trigger.get("query") or "").strip()
                if query and query not in live_queries:
                    live_queries.append(query)

            messages_by_id = {}
            for query in live_queries:
                for message in self._fetch_gmail_unread_messages(query=query, max_results=10):
                    message_id = str(message.get("id") or "")
                    if message_id:
                        messages_by_id[message_id] = message

            messages = list(messages_by_id.values())

            self._append_audit(
                event_type="local_node.gmail_fetch_completed",
                message="Readonly Gmail fetch completed",
                payload={
                    "poll_id": poll_id,
                    "message_count": len(messages),
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
            )

            result = self.poll_train_task_gmail_dry_run(messages=messages)
            result["poll_id"] = poll_id
            result["source"] = "gmail_live_readonly"

            self.connector_registry.save_gmail_config(
                {
                    "last_poll_at": utc_now_iso(),
                    "last_poll_status": "completed",
                    "last_error": None,
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                }
            )

            result["connector"] = self.connector_registry.gmail_health()

            return result

        except Exception as exc:
            error = str(exc)
            self.connector_registry.save_gmail_config(
                {
                    "last_poll_at": utc_now_iso(),
                    "last_poll_status": "failed_fetch_error",
                    "last_error": error,
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                }
            )

            self._append_audit(
                event_type="local_node.gmail_fetch_failed",
                message="Readonly Gmail fetch failed",
                payload={
                    "poll_id": poll_id,
                    "error": error,
                    "dry_run_only": True,
                    "external_writes_enabled": False,
                },
                level="error",
            )

            self._append_audit(
                event_type="local_node.gmail_poll_failed",
                message="Live Gmail poll failed during readonly fetch",
                payload={
                    "poll_id": poll_id,
                    "error": error,
                    "auth_status": auth_status,
                    "polling_enabled": polling_enabled,
                    "dry_run_only": True,
                },
                level="error",
            )

            return {
                "ok": False,
                "poll_id": poll_id,
                "error": error,
                "reason": "gmail_fetch_failed",
                "connector": self.connector_registry.gmail_health(),
                "matched": 0,
                "skipped": 0,
                "deduped": 0,
                "runs": [],
                "dry_run": True,
                "at": utc_now_iso(),
            }

    def poll_train_task_gmail_dry_run(
        self,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        poll_id = f"poll_gmail_{uuid4().hex[:10]}"
        safe_messages = [item for item in (messages or []) if isinstance(item, dict)]
        workflows = self.train_task_store.list_workflows(self.config.workspace_id)
        enabled_workflows = [
            workflow
            for workflow in workflows
            if workflow.get("enabled") is True
            and ((workflow.get("trigger") or {}).get("trigger_type") or "gmail_message_match")
            == "gmail_message_match"
        ]

        matched = 0
        skipped = 0
        deduped = 0
        runs: List[Dict[str, Any]] = []
        skipped_items: List[Dict[str, Any]] = []

        self._append_audit(
            event_type="local_node.gmail_poll_started",
            message="Gmail dry-run poll started",
            payload={
                "poll_id": poll_id,
                "message_count": len(safe_messages),
                "enabled_workflow_count": len(enabled_workflows),
                "dry_run": True,
            },
        )

        for message in safe_messages:
            message_id = str(message.get("id") or message.get("message_id") or "").strip()
            if not message_id:
                message_id = f"message_{uuid4().hex[:10]}"

            dedupe_key = f"gmail:{message_id}"

            if self.train_task_store.has_seen(dedupe_key):
                deduped += 1
                self._append_audit(
                    event_type="local_node.gmail_message_deduped",
                    message="Gmail dry-run message deduped",
                    payload={
                        "poll_id": poll_id,
                        "message_id": message_id,
                        "dedupe_key": dedupe_key,
                    },
                )
                continue

            message_matched = False

            for workflow in enabled_workflows:
                workflow_id = str(workflow.get("workflow_id") or workflow.get("id") or "")
                trigger = workflow.get("trigger") or {}
                query = str(trigger.get("query") or "is:unread")

                if not self._gmail_message_matches_query(message, query):
                    continue

                message_matched = True
                matched += 1

                self._append_audit(
                    event_type="local_node.gmail_message_matched",
                    message="Gmail dry-run message matched trained task",
                    payload={
                        "poll_id": poll_id,
                        "message_id": message_id,
                        "workflow_id": workflow_id,
                        "query": query,
                    },
                )

                result = self.run_train_task_workflow_test(
                    workflow_id=workflow_id,
                    sample_email={
                        **message,
                        "id": message_id,
                    },
                )

                result["trigger_source"] = "gmail_poll_dry_run"
                result["poll_id"] = poll_id
                result["message_id"] = message_id

                runs.append(result)

                self._append_audit(
                    event_type="local_node.train_task_workflow_triggered_from_gmail",
                    message="Train-task workflow triggered from Gmail dry-run poll",
                    payload={
                        "poll_id": poll_id,
                        "message_id": message_id,
                        "workflow_id": workflow_id,
                        "ok": result.get("ok") is True,
                        "dry_run": True,
                    },
                )

            if message_matched:
                self.train_task_store.mark_seen(
                    dedupe_key,
                    {
                        "poll_id": poll_id,
                        "message_id": message_id,
                        "matched": True,
                        "workflow_ids": [
                            run.get("workflow_id")
                            for run in runs
                            if run.get("message_id") == message_id
                        ],
                    },
                )
            else:
                skipped += 1
                skipped_item = {
                    "message_id": message_id,
                    "reason": "no_enabled_workflow_query_match",
                }
                skipped_items.append(skipped_item)

                self._append_audit(
                    event_type="local_node.gmail_message_skipped",
                    message="Gmail dry-run message skipped",
                    payload={
                        "poll_id": poll_id,
                        **skipped_item,
                    },
                )

        self._append_audit(
            event_type="local_node.gmail_poll_completed",
            message="Gmail dry-run poll completed",
            payload={
                "poll_id": poll_id,
                "matched": matched,
                "skipped": skipped,
                "deduped": deduped,
                "run_count": len(runs),
                "dry_run": True,
            },
        )

        return {
            "ok": True,
            "poll_id": poll_id,
            "matched": matched,
            "skipped": skipped,
            "deduped": deduped,
            "runs": runs,
            "skipped_items": skipped_items,
            "dry_run": True,
            "at": utc_now_iso(),
        }

    def _normalize_workflow_extraction_fields(
        self,
        workflow: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        extraction = workflow.get("extraction") or {}
        fields = extraction.get("fields") or []

        if not isinstance(fields, list):
            return []

        normalized: List[Dict[str, Any]] = []

        for raw in fields:
            if not isinstance(raw, dict):
                continue

            key = str(raw.get("key") or raw.get("name") or "").strip()
            if not key:
                continue

            normalized.append(
                {
                    "key": key,
                    "label": str(raw.get("label") or key).strip(),
                    "description": str(raw.get("description") or "").strip(),
                    "required": bool(raw.get("required", False)),
                    "fallback": raw.get("fallback"),
                    "source": str(raw.get("source") or "trigger_payload").strip(),
                    "type": str(raw.get("type") or "string").strip(),
                }
            )

        return normalized

    def _validate_generic_workflow_definition(
        self,
        workflow: Dict[str, Any],
    ) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        workflow_id = str(workflow.get("workflow_id") or workflow.get("id") or "").strip()
        name = str(workflow.get("name") or "").strip()

        if not workflow_id:
            errors.append(
                {
                    "code": "workflow_id_required",
                    "message": "Workflow id is required.",
                }
            )

        if not name:
            warnings.append(
                {
                    "code": "workflow_name_missing",
                    "message": "Workflow name is missing.",
                }
            )

        trigger = workflow.get("trigger") or {}
        if not isinstance(trigger, dict) or not trigger.get("type"):
            errors.append(
                {
                    "code": "trigger_required",
                    "message": "Workflow trigger is required.",
                }
            )

        steps = workflow.get("steps") or []
        if not isinstance(steps, list) or not steps:
            errors.append(
                {
                    "code": "steps_required",
                    "message": "Workflow must include at least one step.",
                }
            )
            steps = []

        allowed_step_types = {
            "trigger",
            "extract",
            "transform",
            "summarise",
            "summarize",
            "tool_action",
            "approval_checkpoint",
            "notify",
            "stop",
            "end",
        }

        seen_step_ids: set[str] = set()
        output_names: set[str] = {"trigger"}

        risky_step_seen = False
        approval_seen_before_risky = False
        end_seen = False

        tools: List[Dict[str, Any]] = []

        if hasattr(self.external_tool_discovery, "list_external_tools"):
            discovered = self.external_tool_discovery.list_external_tools()
            if isinstance(discovered, dict):
                tools = discovered.get("items") or discovered.get("tools") or []
            elif isinstance(discovered, list):
                tools = discovered
        else:
            if hasattr(self.external_tool_discovery, "list_stackone_tools"):
                tools.extend(self.external_tool_discovery.list_stackone_tools())
            if hasattr(self.external_tool_discovery, "list_mcp_tools"):
                tools.extend(self.external_tool_discovery.list_mcp_tools())

        tool_ids = {
            str(tool.get("tool_id") or "")
            for tool in tools
            if isinstance(tool, dict)
        }

        for index, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                errors.append(
                    {
                        "code": "step_invalid",
                        "message": f"Step {index} must be an object.",
                        "step_index": index,
                    }
                )
                continue

            step_id = str(step.get("step_id") or step.get("id") or f"step_{index}").strip()
            step_type = str(step.get("type") or step.get("step_type") or "").strip()

            if not step_type:
                errors.append(
                    {
                        "code": "step_type_required",
                        "message": f"Step {index} is missing a step type.",
                        "step_index": index,
                        "step_id": step_id,
                    }
                )
                continue

            if step_type not in allowed_step_types:
                errors.append(
                    {
                        "code": "unsupported_step_type",
                        "message": f"Unsupported step type: {step_type}",
                        "step_index": index,
                        "step_id": step_id,
                    }
                )

            if step_id in seen_step_ids:
                errors.append(
                    {
                        "code": "duplicate_step_id",
                        "message": f"Duplicate step id: {step_id}",
                        "step_index": index,
                        "step_id": step_id,
                    }
                )

            seen_step_ids.add(step_id)

            output_name = str(step.get("output") or step.get("output_name") or step_id).strip()
            if output_name:
                output_names.add(output_name)

            if step_type == "tool_action":
                tool_id = str(step.get("tool_id") or "").strip()
                if not tool_id:
                    errors.append(
                        {
                            "code": "tool_id_required",
                            "message": f"Tool action step {step_id} is missing tool_id.",
                            "step_index": index,
                            "step_id": step_id,
                        }
                    )
                elif tool_id not in tool_ids:
                    errors.append(
                        {
                            "code": "tool_not_available",
                            "message": f"Tool is not available in registry: {tool_id}",
                            "step_index": index,
                            "step_id": step_id,
                            "tool_id": tool_id,
                        }
                    )

                permission_mode = str(step.get("permission_mode") or "").strip()
                external_write = bool(step.get("external_write", False))

                if external_write or permission_mode in {"write_after_approval", "approval_required"}:
                    risky_step_seen = True
                    if not approval_seen_before_risky:
                        errors.append(
                            {
                                "code": "approval_gate_required_before_risky_action",
                                "message": f"Risky tool action {step_id} must have an approval checkpoint before it.",
                                "step_index": index,
                                "step_id": step_id,
                                "tool_id": tool_id,
                            }
                        )

            if step_type == "approval_checkpoint":
                approval_seen_before_risky = True

            if step_type in {"stop", "end"}:
                end_seen = True

            input_map = step.get("input_map") or {}
            if isinstance(input_map, dict):
                for target_key, source_ref in input_map.items():
                    if not isinstance(source_ref, str):
                        continue

                    if source_ref.startswith("$steps."):
                        parts = source_ref.split(".")
                        if len(parts) >= 3:
                            referenced_output = parts[1]
                            if referenced_output not in output_names and referenced_output not in seen_step_ids:
                                errors.append(
                                    {
                                        "code": "referenced_output_missing",
                                        "message": f"Step {step_id} references missing output: {source_ref}",
                                        "step_index": index,
                                        "step_id": step_id,
                                        "target_key": target_key,
                                        "source_ref": source_ref,
                                    }
                                )

        if not end_seen:
            errors.append(
                {
                    "code": "end_state_required",
                    "message": "Workflow must include a stop or end step.",
                }
            )

        extraction_fields = self._normalize_workflow_extraction_fields(workflow)
        extraction_keys = {field["key"] for field in extraction_fields}

        for field in extraction_fields:
            if field["required"] and not field["key"]:
                errors.append(
                    {
                        "code": "required_extraction_field_invalid",
                        "message": "Required extraction field is missing a key.",
                    }
                )

        return {
            "ok": not errors,
            "workflow_id": workflow_id,
            "workflow_name": name,
            "errors": errors,
            "warnings": warnings,
            "extraction_fields": extraction_fields,
            "extraction_keys": sorted(extraction_keys),
            "step_count": len(steps),
            "at": utc_now_iso(),
        }

    def validate_train_task_workflow_definition(
        self,
        workflow: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = self._validate_generic_workflow_definition(workflow)

        self._append_audit(
            event_type=(
                "local_node.generic_workflow_validation_passed"
                if result.get("ok")
                else "local_node.generic_workflow_validation_failed"
            ),
            message=(
                "Generic workflow validation passed"
                if result.get("ok")
                else "Generic workflow validation failed"
            ),
            payload={
                "workflow_id": result.get("workflow_id"),
                "workflow_name": result.get("workflow_name"),
                "error_count": len(result.get("errors") or []),
                "warning_count": len(result.get("warnings") or []),
                "step_count": result.get("step_count"),
            },
            level="info" if result.get("ok") else "warning",
        )

        return result

    def _get_nested_value(
        self,
        value: Any,
        path: str,
    ) -> Any:
        current = value

        if not path:
            return current

        for part in path.split("."):
            if part == "":
                continue

            if isinstance(current, dict):
                current = current.get(part)
                continue

            if isinstance(current, list):
                try:
                    current = current[int(part)]
                    continue
                except Exception:
                    return None

            return None

        return current

    def _resolve_generic_input_value(
        self,
        *,
        source_ref: Any,
        trigger_payload: Dict[str, Any],
        step_outputs: Dict[str, Any],
        workspace_context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        workspace_context = workspace_context or {}

        if isinstance(source_ref, dict):
            if "fixed" in source_ref:
                return source_ref.get("fixed")
            if "value" in source_ref:
                return source_ref.get("value")
            if "from" in source_ref:
                return self._resolve_generic_input_value(
                    source_ref=source_ref.get("from"),
                    trigger_payload=trigger_payload,
                    step_outputs=step_outputs,
                    workspace_context=workspace_context,
                )

        if not isinstance(source_ref, str):
            return source_ref

        if source_ref.startswith("$trigger."):
            path = source_ref[len("$trigger.") :]
            return self._get_nested_value(trigger_payload, path)

        if source_ref.startswith("$workspace."):
            path = source_ref[len("$workspace.") :]
            return self._get_nested_value(workspace_context, path)

        if source_ref.startswith("$steps."):
            remainder = source_ref[len("$steps.") :]
            if "." not in remainder:
                return step_outputs.get(remainder)

            output_name, path = remainder.split(".", 1)
            value: Any = step_outputs.get(output_name)
            return self._get_nested_value(value, path)

        return source_ref

    def _execute_generic_extract_step(
        self,
        *,
        workflow: Dict[str, Any],
        trigger_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        fields = self._normalize_workflow_extraction_fields(workflow)
        extracted: Dict[str, Any] = {}
        missing_required: List[str] = []

        for field in fields:
            key = field["key"]
            source = str(field.get("source") or "trigger_payload")

            value = None

            if source == "trigger_payload":
                value = trigger_payload.get(key)
                if value in {None, ""}:
                    # useful aliases for email/message workflows
                    aliases = {
                        "customer_email": ["email", "from_email", "sender_email"],
                        "email": ["customer_email", "from_email", "sender_email"],
                        "message": ["body", "text", "content"],
                        "job_type": ["subject", "enquiry_type", "category"],
                    }
                    for alias in aliases.get(key, []):
                        value = trigger_payload.get(alias)
                        if value not in {None, ""}:
                            break

            if value in {None, ""} and field.get("fallback") is not None:
                value = field.get("fallback")

            if value in {None, ""} and field.get("required"):
                missing_required.append(key)

            extracted[key] = value

        return {
            "ok": not missing_required,
            "step_type": "extract",
            "fields": extracted,
            "missing_required": missing_required,
        }

    def _resolve_generic_input_map(
        self,
        *,
        input_map: Any,
        trigger_payload: Dict[str, Any],
        step_outputs: Dict[str, Any],
        workspace_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        workspace_context = workspace_context or {}
        resolved: Dict[str, Any] = {}
        diagnostics: List[Dict[str, Any]] = []

        if not isinstance(input_map, dict):
            return {
                "ok": True,
                "values": resolved,
                "diagnostics": diagnostics,
            }

        for target_key, source_ref in input_map.items():
            value = self._resolve_generic_input_value(
                source_ref=source_ref,
                trigger_payload=trigger_payload,
                step_outputs=step_outputs,
                workspace_context=workspace_context,
            )

            missing = value is None or value == ""

            diagnostics.append(
                {
                    "target_key": str(target_key),
                    "source_ref": source_ref,
                    "resolved": not missing,
                    "value_preview": None if missing else str(value)[:160],
                }
            )

            resolved[str(target_key)] = value

        return {
            "ok": True,
            "values": resolved,
            "diagnostics": diagnostics,
        }

    def _execute_generic_transform_step(
        self,
        *,
        step: Dict[str, Any],
        trigger_payload: Dict[str, Any],
        step_outputs: Dict[str, Any],
        workspace_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        input_map = step.get("input_map") or {}
        mapping = self._resolve_generic_input_map(
            input_map=input_map,
            trigger_payload=trigger_payload,
            step_outputs=step_outputs,
            workspace_context=workspace_context,
        )
        resolved_inputs: Dict[str, Any] = mapping.get("values") or {}

        summary_parts = []
        for key, value in resolved_inputs.items():
            if value not in {None, ""}:
                summary_parts.append(f"{key}: {value}")

        return {
            "ok": True,
            "step_type": str(step.get("type") or step.get("step_type") or "transform"),
            "inputs": resolved_inputs,
            "mapping_diagnostics": mapping.get("diagnostics") or [],
            "summary": "; ".join(summary_parts) if summary_parts else "No summary inputs available.",
        }

    def _execute_generic_tool_action_step(
        self,
        *,
        workflow: Dict[str, Any],
        step: Dict[str, Any],
        trigger_payload: Dict[str, Any],
        step_outputs: Dict[str, Any],
        run_id: str,
        workspace_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tool_id = str(step.get("tool_id") or "").strip()
        input_map = step.get("input_map") or {}
        mapping = self._resolve_generic_input_map(
            input_map=input_map,
            trigger_payload=trigger_payload,
            step_outputs=step_outputs,
            workspace_context=workspace_context,
        )
        payload: Dict[str, Any] = mapping.get("values") or {}

        fixed_input = step.get("fixed_input") or step.get("fixed_value") or {}
        if isinstance(fixed_input, dict):
            payload.update(fixed_input)

        external_write = bool(step.get("external_write", False))
        permission_mode = str(step.get("permission_mode") or "dry_run_only")

        # Generic executor is simulation/dry-run only in Phase 7B.
        if external_write or permission_mode in {"write_after_approval", "approval_required"}:
            blocked_by_policy = True
        else:
            blocked_by_policy = False

        result = {
            "ok": True,
            "step_type": "tool_action",
            "tool_id": tool_id,
            "payload": payload,
            "mapping_diagnostics": mapping.get("diagnostics") or [],
            "dry_run": True,
            "permission_mode": permission_mode,
            "external_write": external_write,
            "external_write_blocked": blocked_by_policy,
            "blocked_by_policy": blocked_by_policy,
        }

        self._append_audit(
            event_type="local_node.generic_workflow_tool_action_prepared",
            message="Generic workflow tool action prepared",
            payload={
                "workflow_id": workflow.get("workflow_id") or workflow.get("id"),
                "workflow_name": workflow.get("name"),
                "run_id": run_id,
                "tool_id": tool_id,
                "dry_run": True,
                "external_write": external_write,
                "external_write_blocked": blocked_by_policy,
            },
        )

        return result

    def _generic_workflow_store_dir(self) -> Path:
        path = Path(".runtime/local_node/train_tasks/generic_workflows") / self.config.workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _generic_workflow_path(self, workflow_id: str) -> Path:
        safe_id = "".join(
            ch if ch.isalnum() or ch in {"_", "-", "."} else "_"
            for ch in str(workflow_id or "workflow").strip()
        )
        return self._generic_workflow_store_dir() / f"{safe_id}.json"

    def save_generic_train_task_workflow(
        self,
        *,
        workflow: Dict[str, Any],
        publish: bool = False,
        saved_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        workflow = dict(workflow or {})
        workflow_id = str(workflow.get("workflow_id") or workflow.get("id") or "").strip()
        workflow_name = str(workflow.get("name") or workflow_id or "Unnamed workflow").strip()

        validation = self._validate_generic_workflow_definition(workflow)

        if not workflow_id:
            return {
                "ok": False,
                "reason": "workflow_id_required",
                "error": "Workflow id is required before save.",
                "validation": validation,
                "at": utc_now_iso(),
            }

        if publish and not validation.get("ok"):
            self._append_audit(
                event_type="local_node.generic_workflow_publish_blocked",
                message="Generic workflow publish blocked by validation",
                payload={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "error_count": len(validation.get("errors") or []),
                    "saved_by": saved_by,
                },
                level="warning",
            )

            return {
                "ok": False,
                "reason": "workflow_validation_failed",
                "error": "Workflow failed validation and cannot be published/enabled.",
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "published": False,
                "enabled": False,
                "validation": validation,
                "at": utc_now_iso(),
            }

        now = utc_now_iso()

        record = {
            "schema_version": "aion.generic_workflow.v1",
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "workflow": workflow,
            "validation": validation,
            "status": "published" if publish else "draft",
            "enabled": bool(publish and validation.get("ok")),
            "published": bool(publish and validation.get("ok")),
            "saved_by": saved_by,
            "saved_at": now,
            "updated_at": now,
        }

        existing_path = self._generic_workflow_path(workflow_id)
        if existing_path.exists():
            try:
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
                record["created_at"] = existing.get("created_at") or now
            except Exception:
                record["created_at"] = now
        else:
            record["created_at"] = now

        existing_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        self._append_audit(
            event_type=(
                "local_node.generic_workflow_published"
                if record["published"]
                else "local_node.generic_workflow_saved_draft"
            ),
            message=(
                "Generic workflow published"
                if record["published"]
                else "Generic workflow saved as draft"
            ),
            payload={
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "status": record["status"],
                "enabled": record["enabled"],
                "published": record["published"],
                "validation_ok": validation.get("ok") is True,
                "error_count": len(validation.get("errors") or []),
                "saved_by": saved_by,
            },
        )

        return {
            "ok": True,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": record["status"],
            "enabled": record["enabled"],
            "published": record["published"],
            "path": str(existing_path),
            "validation": validation,
            "item": record,
            "at": now,
        }

    def load_generic_train_task_workflow(
        self,
        *,
        workflow_id: str,
    ) -> Dict[str, Any]:
        workflow_id = str(workflow_id or "").strip()

        if not workflow_id:
            return {
                "ok": False,
                "reason": "workflow_id_required",
                "error": "workflow_id is required.",
                "at": utc_now_iso(),
            }

        path = self._generic_workflow_path(workflow_id)

        if not path.exists():
            return {
                "ok": False,
                "reason": "workflow_not_found",
                "error": f"Generic workflow not found: {workflow_id}",
                "workflow_id": workflow_id,
                "path": str(path),
                "at": utc_now_iso(),
            }

        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "ok": False,
                "reason": "workflow_load_failed",
                "error": str(exc),
                "workflow_id": workflow_id,
                "path": str(path),
                "at": utc_now_iso(),
            }

        return {
            "ok": True,
            "workflow_id": workflow_id,
            "path": str(path),
            "item": item,
            "at": utc_now_iso(),
        }

    def run_published_generic_train_task_workflow(
        self,
        *,
        workflow_id: str,
        trigger_payload: Optional[Dict[str, Any]] = None,
        workspace_context: Optional[Dict[str, Any]] = None,
        executed_by: str = "operations_agents_desktop",
    ) -> Dict[str, Any]:
        workflow_id = str(workflow_id or "").strip()
        trigger_payload = trigger_payload or {}
        workspace_context = workspace_context or {}

        loaded = self.load_generic_train_task_workflow(workflow_id=workflow_id)

        if not loaded.get("ok"):
            self._append_audit(
                event_type="local_node.generic_workflow_run_by_id_failed",
                message="Generic workflow run-by-id failed",
                payload={
                    "workflow_id": workflow_id,
                    "reason": loaded.get("reason"),
                    "error": loaded.get("error"),
                    "executed_by": executed_by,
                },
                level="warning",
            )
            return loaded

        item = loaded.get("item") or {}
        workflow = item.get("workflow") or {}

        enabled = item.get("enabled") is True
        published = item.get("published") is True
        status = str(item.get("status") or "")

        if not enabled or not published or status != "published":
            result = {
                "ok": False,
                "reason": "workflow_not_published_or_enabled",
                "error": "Generic workflow must be published and enabled before it can run by id.",
                "workflow_id": workflow_id,
                "status": status,
                "enabled": enabled,
                "published": published,
                "at": utc_now_iso(),
            }

            self._append_audit(
                event_type="local_node.generic_workflow_run_by_id_blocked",
                message="Generic workflow run-by-id blocked because workflow is not published/enabled",
                payload={
                    "workflow_id": workflow_id,
                    "status": status,
                    "enabled": enabled,
                    "published": published,
                    "executed_by": executed_by,
                },
                level="warning",
            )

            return result

        validation = self._validate_generic_workflow_definition(workflow)

        if not validation.get("ok"):
            result = {
                "ok": False,
                "reason": "workflow_validation_failed",
                "error": "Published workflow failed validation at execution time.",
                "workflow_id": workflow_id,
                "validation": validation,
                "at": utc_now_iso(),
            }

            self._append_audit(
                event_type="local_node.generic_workflow_run_by_id_blocked",
                message="Generic workflow run-by-id blocked by validation",
                payload={
                    "workflow_id": workflow_id,
                    "error_count": len(validation.get("errors") or []),
                    "executed_by": executed_by,
                },
                level="warning",
            )

            return result

        self._append_audit(
            event_type="local_node.generic_workflow_run_by_id_started",
            message="Published generic workflow run-by-id started",
            payload={
                "workflow_id": workflow_id,
                "workflow_name": item.get("workflow_name") or workflow.get("name"),
                "status": status,
                "enabled": enabled,
                "published": published,
                "executed_by": executed_by,
                "dry_run": True,
            },
        )

        result = self.run_generic_train_task_workflow_test(
            workflow=workflow,
            trigger_payload=trigger_payload,
            workspace_context=workspace_context,
        )

        result["loaded_workflow_id"] = workflow_id
        result["loaded_workflow_status"] = status
        result["executed_by"] = executed_by
        result["run_mode"] = "published_generic_workflow_by_id"

        self._append_audit(
            event_type=(
                "local_node.generic_workflow_run_by_id_completed"
                if result.get("ok")
                else "local_node.generic_workflow_run_by_id_failed"
            ),
            message=(
                "Published generic workflow run-by-id completed"
                if result.get("ok")
                else "Published generic workflow run-by-id failed"
            ),
            payload={
                "workflow_id": workflow_id,
                "workflow_name": item.get("workflow_name") or workflow.get("name"),
                "run_id": result.get("run_id"),
                "status": result.get("status"),
                "ok": result.get("ok") is True,
                "executed_by": executed_by,
                "dry_run": True,
            },
            level="info" if result.get("ok") else "warning",
        )

        return result

    def list_generic_train_task_workflows(self) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []

        store_dir = self._generic_workflow_store_dir()

        for path in sorted(store_dir.glob("*.json")):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                items.append(item)
            except Exception as exc:
                items.append(
                    {
                        "workflow_id": path.stem,
                        "ok": False,
                        "error": str(exc),
                        "path": str(path),
                    }
                )

        return {
            "ok": True,
            "items": items,
            "count": len(items),
            "at": utc_now_iso(),
        }

    def run_generic_train_task_workflow_test(
        self,
        *,
        workflow: Dict[str, Any],
        trigger_payload: Optional[Dict[str, Any]] = None,
        workspace_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trigger_payload = trigger_payload or {}
        workspace_context = workspace_context or {}

        validation = self._validate_generic_workflow_definition(workflow)
        workflow_id = str(workflow.get("workflow_id") or workflow.get("id") or "generic_workflow")
        workflow_name = str(workflow.get("name") or workflow_id)
        run_id = f"run_{workflow_id}_{uuid4().hex[:10]}"

        self._append_audit(
            event_type="local_node.generic_workflow_test_run_started",
            message="Generic workflow test run started",
            payload={
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "valid": validation.get("ok") is True,
                "dry_run": True,
            },
        )

        if not validation.get("ok"):
            result = {
                "ok": False,
                "reason": "workflow_validation_failed",
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "validation": validation,
                "steps": [],
                "dry_run": True,
                "at": utc_now_iso(),
            }

            self._append_audit(
                event_type="local_node.generic_workflow_test_run_failed",
                message="Generic workflow test run failed validation",
                payload={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "reason": "workflow_validation_failed",
                    "error_count": len(validation.get("errors") or []),
                },
                level="warning",
            )

            return result

        steps = workflow.get("steps") or []
        replay_steps: List[Dict[str, Any]] = []
        step_outputs: Dict[str, Any] = {
            "trigger": trigger_payload,
        }

        status = "completed"
        failure_reason = ""

        for index, step in enumerate(steps, 1):
            step_id = str(step.get("step_id") or step.get("id") or f"step_{index}")
            step_type = str(step.get("type") or step.get("step_type") or "")
            output_name = str(step.get("output") or step.get("output_name") or step_id)

            if step_type == "trigger":
                output = {
                    "ok": True,
                    "step_type": "trigger",
                    "trigger": workflow.get("trigger") or {},
                    "payload": trigger_payload,
                }

            elif step_type == "extract":
                output = self._execute_generic_extract_step(
                    workflow=workflow,
                    trigger_payload=trigger_payload,
                )

                if not output.get("ok"):
                    status = "failed"
                    failure_reason = "missing_required_extraction_fields"

            elif step_type in {"transform", "summarise", "summarize"}:
                output = self._execute_generic_transform_step(
                    step=step,
                    trigger_payload=trigger_payload,
                    step_outputs=step_outputs,
                    workspace_context=workspace_context,
                )

            elif step_type == "tool_action":
                output = self._execute_generic_tool_action_step(
                    workflow=workflow,
                    step=step,
                    trigger_payload=trigger_payload,
                    step_outputs=step_outputs,
                    run_id=run_id,
                    workspace_context=workspace_context,
                )

            elif step_type == "approval_checkpoint":
                output = {
                    "ok": True,
                    "step_type": "approval_checkpoint",
                    "status": "waiting_approval",
                    "requires_approval": True,
                    "dry_run": True,
                    "stops_execution": True,
                    "resume_required": True,
                }
                status = "waiting_approval"

            elif step_type == "notify":
                output = {
                    "ok": True,
                    "step_type": "notify",
                    "dry_run": True,
                    "message": str(step.get("message") or "Notification prepared."),
                }

            elif step_type in {"stop", "end"}:
                output = {
                    "ok": True,
                    "step_type": step_type,
                    "status": "completed" if status != "failed" else "failed",
                }
                if status not in {"failed", "waiting_approval"}:
                    status = "completed"

            else:
                output = {
                    "ok": False,
                    "step_type": step_type,
                    "error": f"Unsupported step type: {step_type}",
                }
                status = "failed"
                failure_reason = "unsupported_step_type"

            replay_step = {
                "step": index,
                "step_id": step_id,
                "type": step_type,
                "output_name": output_name,
                "ok": output.get("ok") is True,
                "output": output,
            }

            replay_steps.append(replay_step)
            step_outputs[output_name] = output.get("fields") if step_type == "extract" else output
            step_outputs[step_id] = step_outputs[output_name]

            self._append_audit(
                event_type="local_node.generic_workflow_step_completed",
                message="Generic workflow step completed",
                payload={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow_name,
                    "run_id": run_id,
                    "step": index,
                    "step_id": step_id,
                    "step_type": step_type,
                    "ok": output.get("ok") is True,
                },
                level="info" if output.get("ok") is True else "warning",
            )

            if step_type == "approval_checkpoint" and output.get("stops_execution") is True:
                self._append_audit(
                    event_type="local_node.generic_workflow_paused_for_approval",
                    message="Generic workflow paused at approval checkpoint",
                    payload={
                        "workflow_id": workflow_id,
                        "workflow_name": workflow_name,
                        "run_id": run_id,
                        "step": index,
                        "step_id": step_id,
                        "status": "waiting_approval",
                        "resume_required": True,
                    },
                )
                break

            if status == "failed":
                break

        stopped_at_step = None
        if status == "waiting_approval" and replay_steps:
            stopped_at_step = replay_steps[-1]

        result = {
            "ok": status not in {"failed"},
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "run_id": run_id,
            "status": status,
            "failure_reason": failure_reason,
            "stopped_at_step": stopped_at_step,
            "resume_required": status == "waiting_approval",
            "steps": replay_steps,
            "step_outputs": step_outputs,
            "dry_run": True,
            "validation": validation,
            "at": utc_now_iso(),
        }

        # Persist lightweight generic run history.
        try:
            run_dir = Path(".runtime/local_node/train_tasks/generic_runs") / self.config.workspace_id
            run_dir.mkdir(parents=True, exist_ok=True)
            run_path = run_dir / f"{run_id}.json"
            run_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            result["history_save_error"] = str(exc)

        self._append_audit(
            event_type=(
                "local_node.generic_workflow_test_run_completed"
                if result.get("ok")
                else "local_node.generic_workflow_test_run_failed"
            ),
            message=(
                "Generic workflow test run completed"
                if result.get("ok")
                else "Generic workflow test run failed"
            ),
            payload={
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "status": status,
                "step_count": len(replay_steps),
                "failure_reason": failure_reason,
                "dry_run": True,
            },
            level="info" if result.get("ok") else "warning",
        )

        return result

    def run_train_task_workflow_test(
        self,
        workflow_id: str,
        sample_email: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        workflow = self.train_task_store.get_workflow(
            self.config.workspace_id,
            workflow_id,
        )

        if not workflow:
            result = {
                "ok": False,
                "workflow_id": workflow_id,
                "error": "Train-task workflow not found",
                "steps": [],
                "extracted_customer": None,
                "hubspot_action": None,
                "email_draft": None,
                "approval": None,
                "at": utc_now_iso(),
            }

            self._append_audit(
                event_type="local_node.train_task_workflow_test_run_failed",
                message="Train-task workflow test failed: workflow not found",
                payload={
                    "workflow_id": workflow_id,
                    "ok": False,
                    "error": result["error"],
                },
            )

            return result

        self._append_audit(
            event_type="local_node.train_task_workflow_test_run_started",
            message="Train-task workflow test run started",
            payload={
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name") or workflow_id,
                "enabled": workflow.get("enabled") is True,
                "trigger_type": (workflow.get("trigger") or {}).get("trigger_type"),
                "dry_run": True,
            },
        )

        try:
            sample_email = sample_email or {
                "id": "email_test_001",
                "from": "Jane Customer <jane@example.com>",
                "subject": "New enquiry about installation",
                "body": (
                    "Hi, my name is Jane Customer. "
                    "My email is jane@example.com and my phone is 07123 456789. "
                    "I need help with a new installation."
                ),
            }

            trigger = workflow.get("trigger") or {}
            hubspot = workflow.get("hubspot") or {}
            email_draft = workflow.get("email_draft") or {}
            approval = workflow.get("approval") or {}

            body = str(sample_email.get("body") or "")
            subject = str(sample_email.get("subject") or "")
            sender = str(sample_email.get("from") or "")

            extracted_customer = {
                "name": "Jane Customer",
                "email": "jane@example.com",
                "phone": "07123 456789",
                "company": "",
                "enquiry_type": subject or "New enquiry about installation",
            }

            # Phase 1 safe extractor stub.
            # Later this should use the workflow extraction schema + local/LLM extractor.
            if "jane@example.com" not in body and "jane@example.com" not in sender:
                extracted_customer["email"] = ""

            business_name = "Costa Conexion"
            customer_name = extracted_customer.get("name") or "there"
            enquiry_type = extracted_customer.get("enquiry_type") or "your enquiry"

            field_mapping = hubspot.get("field_mapping") or {
                "email": "email",
                "name": "firstname",
                "phone": "phone",
                "company": "company",
                "enquiry_type": "message",
            }

            hubspot_action = self._decorate_tool_output(
                {
                    "step_type": hubspot.get("step_type") or "hubspot_create_or_update_contact",
                    "dry_run": hubspot.get("dry_run", True) is not False,
                    "match_field": hubspot.get("match_field") or "email",
                    "would_create_or_update_contact": bool(extracted_customer.get("email")),
                    "field_mapping": {
                        field_mapping.get("email", "email"): extracted_customer.get("email", ""),
                        field_mapping.get("name", "firstname"): extracted_customer.get("name", ""),
                        field_mapping.get("phone", "phone"): extracted_customer.get("phone", ""),
                        field_mapping.get("company", "company"): extracted_customer.get("company", ""),
                        field_mapping.get("enquiry_type", "message"): extracted_customer.get("enquiry_type", ""),
                    },
                },
                action_type=hubspot.get("step_type") or "hubspot_create_or_update_contact",
                dry_run=hubspot.get("dry_run", True) is not False,
            )

            subject_template = (
                email_draft.get("subject_template")
                or "Welcome — thanks for your enquiry"
            )

            body_template = (
                email_draft.get("body_template")
                or (
                    "Hi {{name}},\n\n"
                    "Thanks for getting in touch. We’ve received your enquiry about {{enquiry_type}} "
                    "and will come back to you shortly.\n\n"
                    "Best,\n"
                    "{{business_name}}"
                )
            )

            rendered_body = (
                body_template
                .replace("{{name}}", customer_name)
                .replace("{{enquiry_type}}", enquiry_type)
                .replace("{{business_name}}", business_name)
                .replace("{{email}}", extracted_customer.get("email", ""))
                .replace("{{phone}}", extracted_customer.get("phone", ""))
                .replace("{{company}}", extracted_customer.get("company", ""))
            )

            prepared_email_draft = self._decorate_tool_output(
                {
                    "step_type": email_draft.get("step_type") or "gmail_draft_welcome_email",
                    "dry_run": True,
                    "to": extracted_customer.get("email", ""),
                    "subject": subject_template,
                    "body": rendered_body,
                },
                action_type="gmail_draft_preview",
                dry_run=True,
            )

            approval_checkpoint = self._decorate_tool_output(
                {
                    "step_type": approval.get("step_type") or "approval_checkpoint",
                    "approval_mode": approval.get("approval_mode") or "ask_before_external_action",
                    "require_human": approval.get("require_human", True) is not False,
                    "title": approval.get("title") or "Review new customer automation",
                    "status": "waiting_approval",
                },
                action_type="approval_checkpoint",
                dry_run=True,
            )

            steps = [
                {
                    "step": 1,
                    "title": "Gmail trigger matched",
                    "ok": True,
                    "output": {
                        "email_id": sample_email.get("id") or "email_test_001",
                        "query": trigger.get("query") or "is:unread",
                    },
                },
                {
                    "step": 2,
                    "title": "Extract customer details",
                    "ok": True,
                    "output": extracted_customer,
                },
                {
                    "step": 3,
                    "title": "Prepare HubSpot contact action",
                    "ok": True,
                    "output": hubspot_action,
                },
                {
                    "step": 4,
                    "title": "Prepare welcome email draft",
                    "ok": True,
                    "output": prepared_email_draft,
                },
                {
                    "step": 5,
                    "title": "Human approval checkpoint",
                    "ok": True,
                    "output": approval_checkpoint,
                },
            ]

            result = {
                "ok": True,
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name") or workflow_id,
                "workflow": workflow,
                "steps": steps,
                "extracted_customer": extracted_customer,
                "hubspot_action": hubspot_action,
                "email_draft": prepared_email_draft,
                "approval": approval_checkpoint,
                "at": utc_now_iso(),
            }

            run_id = f"run_{workflow_id}_{uuid4().hex[:10]}"
            self.train_task_store.save_run(
                self.config.workspace_id,
                run_id,
                result,
            )

            trigger_source = str(result.get("trigger_source") or "test_run")
            train_task_approval = self._create_train_task_approval_from_replay(
                workflow=workflow,
                result=result,
                run_id=run_id,
                trigger_source=trigger_source,
            )
            result["approval_item"] = train_task_approval

            # Re-save run with approval reference included.
            self.train_task_store.save_run(
                self.config.workspace_id,
                run_id,
                result,
            )

            for index, step in enumerate(steps):
                step_number = step.get("step") or index + 1
                step_title = step.get("title") or f"Step {step_number}"
                step_output = step.get("output") or {}

                if step_number == 1:
                    event_type = "local_node.train_task_trigger_matched"
                    message = "Train-task trigger matched"
                elif step_number == 2:
                    event_type = "local_node.train_task_extraction_completed"
                    message = "Train-task extraction completed"
                elif step_number == 3:
                    event_type = "local_node.train_task_hubspot_action_prepared"
                    message = "Train-task HubSpot action prepared"
                elif step_number == 4:
                    event_type = "local_node.train_task_email_draft_prepared"
                    message = "Train-task email draft prepared"
                elif step_number == 5:
                    event_type = "local_node.train_task_approval_checkpoint_prepared"
                    message = "Train-task approval checkpoint prepared"
                else:
                    event_type = "local_node.train_task_step_completed"
                    message = f"Train-task step completed: {step_title}"

                self._append_audit(
                    event_type=event_type,
                    message=message,
                    payload={
                        "workflow_id": workflow_id,
                        "workflow_name": workflow.get("name") or workflow_id,
                        "run_id": run_id,
                        "step": step_number,
                        "title": step_title,
                        "ok": step.get("ok") is True,
                        "output": step_output,
                    },
                )

                self._audit_tool_result(
                    workflow_id=workflow_id,
                    workflow_name=workflow.get("name") or workflow_id,
                    run_id=run_id,
                    step_number=step_number,
                    step_title=step_title,
                    output=step_output,
                )

            self._append_audit(
                event_type="local_node.train_task_workflow_test_run_completed",
                message="Train-task workflow test run completed",
                payload={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.get("name") or workflow_id,
                    "run_id": run_id,
                    "ok": True,
                    "step_count": len(steps),
                    "approval_status": approval_checkpoint.get("status"),
                    "dry_run": True,
                },
            )

            return result

        except Exception as error:
            self._append_audit(
                event_type="local_node.train_task_workflow_test_run_failed",
                message="Train-task workflow test run failed",
                payload={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.get("name") or workflow_id,
                    "ok": False,
                    "error": str(error),
                },
            )

            return {
                "ok": False,
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name") or workflow_id,
                "workflow": workflow,
                "error": str(error),
                "steps": [],
                "extracted_customer": None,
                "hubspot_action": None,
                "email_draft": None,
                "approval": None,
                "at": utc_now_iso(),
            }

    def run_customer_onboarding_train_task_test(
        self,
        *,
        sample_email: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 1 Train-a-Task dry-run.

        This simulates:
        Gmail trigger -> customer extraction -> HubSpot dry-run -> Gmail draft dry-run
        -> approval checkpoint.

        It intentionally does NOT create a real approval request yet because
        LocalApprovalStore does not expose create_request().
        """
        import re
        from uuid import uuid4

        sample_email = sample_email or {}

        email_id = str(sample_email.get("id") or f"email_test_{uuid4().hex[:8]}")
        email_from = str(sample_email.get("from") or "").strip()
        subject = str(sample_email.get("subject") or "").strip()
        body = str(sample_email.get("body") or "").strip()

        combined = "\n".join([email_from, subject, body]).strip()

        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            combined,
        )

        phone_match = re.search(
            r"(?:\+?\d[\d\s().-]{7,}\d)",
            combined,
        )

        name_match = re.search(
            r"(?:my name is|i am|i'm)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
            combined,
            flags=re.IGNORECASE,
        )

        if not name_match and email_from:
            display_name = email_from.split("<", 1)[0].strip().strip('"')
            if display_name and "@" not in display_name:
                extracted_name = display_name
            else:
                extracted_name = ""
        else:
            extracted_name = name_match.group(1).strip() if name_match else ""

        extracted_email = email_match.group(0).strip() if email_match else ""
        extracted_phone = phone_match.group(0).strip() if phone_match else ""

        extracted_customer = {
            "name": extracted_name,
            "email": extracted_email,
            "phone": extracted_phone,
            "company": "",
            "enquiry_type": subject or "Customer enquiry",
        }

        hubspot_action = {
            "step_type": "hubspot_create_or_update_contact",
            "dry_run": True,
            "account_id": "default",
            "match_field": "email",
            "would_create_or_update_contact": bool(extracted_email),
            "field_mapping": {
                "email": extracted_email,
                "firstname": extracted_name,
                "phone": extracted_phone,
                "company": "",
                "message": subject or body[:160],
            },
        }

        first_name = extracted_name or "there"
        business_name = "Costa Conexion"

        email_draft = {
            "step_type": "gmail_draft_welcome_email",
            "dry_run": True,
            "account_id": "default",
            "to": extracted_email,
            "subject": "Welcome — thanks for your enquiry",
            "body": (
                f"Hi {first_name},\n\n"
                f"Thanks for getting in touch. We’ve received your enquiry about "
                f"{subject or 'your request'} and will come back to you shortly.\n\n"
                f"Best,\n{business_name}"
            ),
        }

        approval_checkpoint = {
            "step_type": "approval_checkpoint",
            "approval_mode": "ask_before_external_action",
            "require_human": True,
            "status": "simulated_waiting_approval",
            "title": "Review new customer automation",
            "note": "Dry-run only. No HubSpot contact or Gmail draft was created.",
        }

        missing_required = []
        if not extracted_email:
            missing_required.append("email")

        result = {
            "ok": len(missing_required) == 0,
            "mode": "dry_run",
            "workflow_id": "workflow_gmail_to_hubspot_welcome_v1",
            "name": "Gmail lead to HubSpot and welcome draft",
            "department_key": "operations",
            "operator_id": "operator_customer_onboarding_v1",
            "input": {
                "sample_email": {
                    "id": email_id,
                    "from": email_from,
                    "subject": subject,
                    "body": body,
                }
            },
            "steps": [
                {
                    "step": 1,
                    "label": "Gmail trigger matched",
                    "ok": True,
                    "output": {
                        "email_id": email_id,
                        "query": "is:unread",
                        "matched": True,
                    },
                },
                {
                    "step": 2,
                    "label": "Extract customer details",
                    "ok": len(missing_required) == 0,
                    "output": extracted_customer,
                    "missing_required": missing_required,
                },
                {
                    "step": 3,
                    "label": "Prepare HubSpot contact action",
                    "ok": bool(extracted_email),
                    "output": hubspot_action,
                },
                {
                    "step": 4,
                    "label": "Prepare welcome email draft",
                    "ok": bool(extracted_email),
                    "output": email_draft,
                },
                {
                    "step": 5,
                    "label": "Human approval checkpoint",
                    "ok": True,
                    "output": approval_checkpoint,
                },
            ],
            "extracted_customer": extracted_customer,
            "hubspot_action": hubspot_action,
            "email_draft": email_draft,
            "approval": approval_checkpoint,
            "summary": (
                "Dry-run completed. Aion extracted the customer, prepared the "
                "HubSpot action, prepared the welcome email draft, and stopped at "
                "a simulated approval checkpoint."
                if not missing_required
                else f"Dry-run completed but missing required fields: {', '.join(missing_required)}."
            ),
            "at": utc_now_iso(),
        }

        self._append_audit(
            event_type="local_node.train_task_test_run",
            message="Customer onboarding train-task dry-run completed",
            payload={
                "workflow_id": result["workflow_id"],
                "operator_id": result["operator_id"],
                "department_key": result["department_key"],
                "sample_email_id": email_id,
                "extracted_email": extracted_email,
                "missing_required": missing_required,
                "dry_run": True,
            },
            level="info" if result["ok"] else "warning",
        )

        return result

    def _seed_default_agent_bundle(self) -> None:
        bundle = seed_marketing_operator_bundle(
            workspace_id=self.config.workspace_id,
            workflow_definition_repository=self.workflow_definition_repository,
            agent_definition_repository=self.agent_definition_repository,
            trigger_definition_repository=self.trigger_definition_repository,
        )

        workflow = bundle.get("workflow")
        agent = bundle.get("agent")
        trigger = bundle.get("trigger")

        workflow_id = getattr(workflow, "workflow_id", None) or getattr(workflow, "id", None)
        agent_id = getattr(agent, "id", None) or getattr(agent, "agent_id", None)
        trigger_id = getattr(trigger, "trigger_id", None) or getattr(trigger, "id", None)

        workflow_path = None
        agent_path = None
        trigger_path = None

        try:
            if workflow_id:
                workflow_path = str(
                    self.workflow_definition_repository._workflow_path(  # type: ignore[attr-defined]
                        self.config.workspace_id,
                        workflow_id,
                    )
                )
        except Exception:
            workflow_path = None

        try:
            if agent_id:
                agent_path = str(
                    self.agent_definition_repository._path(  # type: ignore[attr-defined]
                        self.config.workspace_id,
                        agent_id,
                    )
                )
        except Exception:
            agent_path = None

        try:
            if trigger_id:
                trigger_path = str(
                    self.trigger_definition_repository._path(  # type: ignore[attr-defined]
                        self.config.workspace_id,
                        trigger_id,
                    )
                )
        except Exception:
            trigger_path = None

        workflow_exists = False
        agent_exists = False
        trigger_exists = False

        try:
            workflow_exists = (
                bool(workflow_id)
                and self.workflow_definition_repository.get(
                    self.config.workspace_id,
                    str(workflow_id),
                )
                is not None
            )
        except Exception:
            workflow_exists = False

        try:
            agent_exists = (
                bool(agent_id)
                and self.agent_definition_repository.find_one(
                    self.config.workspace_id,
                    str(agent_id),
                )
                is not None
            )
        except Exception:
            agent_exists = False

        try:
            trigger_exists = (
                bool(trigger_id)
                and self.trigger_definition_repository.find_one(
                    self.config.workspace_id,
                    str(trigger_id),
                )
                is not None
            )
        except Exception:
            trigger_exists = False

        self._append_audit(
            event_type="local_node.agent_seed_succeeded",
            message="Default marketing operator bundle seeded",
            payload={
                "base_dir": self.base_dir,
                "workspace_id": self.config.workspace_id,
                "workflow_id": workflow_id,
                "agent_id": agent_id,
                "trigger_id": trigger_id,
                "workflow_exists": workflow_exists,
                "agent_exists": agent_exists,
                "trigger_exists": trigger_exists,
                "workflow_path": workflow_path,
                "agent_path": agent_path,
                "trigger_path": trigger_path,
            },
            level="info",
        )

        if not workflow_exists or not agent_exists or not trigger_exists:
            raise RuntimeError(
                "Seed bundle did not persist correctly: "
                f"workflow_exists={workflow_exists}, "
                f"agent_exists={agent_exists}, "
                f"trigger_exists={trigger_exists}"
            )

    def _append_audit(
        self,
        *,
        event_type: str,
        message: str,
        payload: Dict[str, Any] | None = None,
        level: str = "info",
    ) -> None:
        self.audit_store.append_event(
            event_type=event_type,
            message=message,
            payload=payload or {},
            level=level,
        )

    def _refresh_node_snapshot(self, status: str) -> None:
        self.node_state_store.save_node_snapshot(
            {
                "node_id": self.config.node_id,
                "workspace_id": self.config.workspace_id,
                "deployment_mode": self.deployment_mode,
                "status": status,
                "updated_at": utc_now_iso(),
            }
        )

    def _ensure_canonical_business_containers(self) -> None:
        service = self.business_container_service
        if service is None:
            return

        ensure_fn = getattr(service, "ensure_canonical_containers", None)
        if not callable(ensure_fn):
            return

        try:
            ensure_fn(self.config.workspace_id)
        except Exception:
            pass

    def _call_first_service_method(
        self,
        method_names: List[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        service = self.business_container_service
        if service is None:
            return None

        for method_name in method_names:
            fn = getattr(service, method_name, None)
            if not callable(fn):
                continue

            try:
                return fn(*args, **kwargs)
            except TypeError:
                continue
            except Exception:
                continue

        return None

    def _call_first_service_method_without_kwargs(
        self,
        method_names: List[str],
        *args: Any,
    ) -> Any:
        service = self.business_container_service
        if service is None:
            return None

        for method_name in method_names:
            fn = getattr(service, method_name, None)
            if not callable(fn):
                continue

            try:
                return fn(*args)
            except Exception:
                continue

        return None

    @staticmethod
    def _extract_summary_payload(payload: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None

        if isinstance(payload.get("summary"), dict):
            return payload["summary"]

        if isinstance(payload.get("projection"), dict):
            return payload["projection"]

        if isinstance(payload.get("data"), dict):
            return payload["data"]

        return payload or None

    @staticmethod
    def _extract_dict_payload(payload: Any) -> Optional[Dict[str, Any]]:
        if isinstance(payload, dict):
            return payload
        return None

    @staticmethod
    def _first_defined(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _as_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if isinstance(value, str):
            parts = (
                value.replace("•", "\n")
                .replace("·", "\n")
                .replace("|", "\n")
                .replace(",", "\n")
                .splitlines()
            )
            return [part.strip() for part in parts if part.strip()]

        return []

    @staticmethod
    def _compact_dict(value: Dict[str, Any]) -> Dict[str, Any]:
        return {key: entry for key, entry in value.items() if entry is not None}

    def _extract_brand_foundation_payload(self, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        for key in (
            "item",
            "brand_foundation",
            "brandFoundation",
            "brandFoundationState",
            "brand_foundation_snapshot",
            "payload",
            "data",
        ):
            nested = payload.get(key)
            if isinstance(nested, dict):
                return nested

        return payload

    def _read_brand_foundation_snapshot(self) -> Dict[str, Any]:
        self._ensure_canonical_business_containers()

        payload = self._safe_business_read(
            "get_brand_foundation_payload",
            self.config.workspace_id,
            default={},
        )

        return self._normalize_brand_foundation_snapshot(payload)

    def _normalize_brand_foundation_snapshot(
        self,
        value: Any,
        *,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = self._extract_brand_foundation_payload(value)
        override = overrides or {}

        brand_map = (
            raw.get("brandMap")
            or raw.get("brand_map")
            or raw.get("brandIntelligenceMap")
            or raw.get("brand_intelligence_map")
            or raw.get("map")
            or {}
        )

        if not isinstance(brand_map, dict):
            brand_map = {}

        brand_overview = self._as_dict(brand_map.get("brandOverview") or brand_map.get("brand_overview") or {})
        brand_goals = self._as_dict(brand_map.get("brandGoals") or brand_map.get("brand_goals") or {})
        brand_purpose = self._as_dict(brand_map.get("brandPurpose") or brand_map.get("brand_purpose") or {})
        brand_vision = self._as_dict(brand_map.get("brandVision") or brand_map.get("brand_vision") or {})
        brand_mission = self._as_dict(brand_map.get("brandMission") or brand_map.get("brand_mission") or {})
        brand_values = self._as_dict(brand_map.get("brandValues") or brand_map.get("brand_values") or {})
        brand_positioning = self._as_dict(brand_map.get("brandPositioning") or brand_map.get("brand_positioning") or brand_map.get("positioning") or {})
        brand_personality = self._as_dict(brand_map.get("brandPersonality") or brand_map.get("brand_personality") or {})
        brand_voice = self._as_dict(brand_map.get("brandVoice") or brand_map.get("brand_voice") or brand_map.get("voice") or {})
        tone_of_voice = self._as_dict(brand_map.get("toneOfVoice") or brand_map.get("tone_of_voice") or {})
        brand_story = self._as_dict(brand_map.get("brandStory") or brand_map.get("brand_story") or {})
        tagline = self._as_dict(brand_map.get("tagline") or {})
        audience = self._as_dict(brand_map.get("audience") or {})
        audience_segments = self._as_dict(brand_map.get("audienceSegments") or brand_map.get("audience_segments") or {})
        customer_personas = self._as_dict(brand_map.get("customerPersonas") or brand_map.get("customer_personas") or {})
        customer_journey = self._as_dict(brand_map.get("customerJourney") or brand_map.get("customer_journey") or {})
        customer_pain_points = self._as_dict(brand_map.get("customerPainPoints") or brand_map.get("customer_pain_points") or {})
        competitor_analysis = self._as_dict(brand_map.get("competitorAnalysis") or brand_map.get("competitor_analysis") or {})
        differentiation = self._as_dict(brand_map.get("differentiation") or {})
        strategy = self._as_dict(brand_map.get("strategy") or {})
        offer_map = self._as_dict(brand_map.get("offer") or {})
        messaging = self._as_dict(brand_map.get("messaging") or {})
        channels_map = self._as_dict(brand_map.get("channels") or {})
        platform_strategy = self._as_dict(brand_map.get("platformStrategy") or brand_map.get("platform_strategy") or {})
        creative_direction = self._as_dict(brand_map.get("creativeDirection") or brand_map.get("creative_direction") or {})
        visual_identity = self._as_dict(brand_map.get("visualIdentity") or brand_map.get("visual_identity") or {})
        governance = self._as_dict(brand_map.get("governance") or {})
        rules = self._as_dict(brand_map.get("rules") or brand_map.get("constraints") or {})
        campaign = self._as_dict(brand_map.get("campaign") or brand_map.get("campaignContext") or brand_map.get("campaign_context") or {})

        objective = self._first_defined(
            override.get("objective"),
            raw.get("objective"),
            strategy.get("objective"),
            strategy.get("primaryObjective"),
            campaign.get("objective"),
            brand_goals.get("primaryGoal"),
            brand_goals.get("goal"),
            "",
        )

        funnel_goal = self._first_defined(
            override.get("funnel_goal"),
            override.get("funnelGoal"),
            raw.get("funnel_goal"),
            raw.get("funnelGoal"),
            strategy.get("funnel_goal"),
            strategy.get("funnelGoal"),
            campaign.get("funnel_goal"),
            campaign.get("funnelGoal"),
            "",
        )

        target_audience = self._first_defined(
            override.get("target_audience"),
            override.get("targetAudience"),
            raw.get("target_audience"),
            raw.get("targetAudience"),
            audience.get("primaryAudience"),
            audience.get("targetAudience"),
            audience.get("target_audience"),
            audience.get("primary"),
            "",
        )

        persona = self._first_defined(
            override.get("persona"),
            raw.get("persona"),
            audience.get("primaryPersona"),
            audience.get("persona"),
            audience.get("buyer_persona"),
            audience.get("buyerPersona"),
            "",
        )

        offer = self._first_defined(
            override.get("offer"),
            raw.get("offer"),
            offer_map.get("primaryOffer"),
            offer_map.get("offer"),
            campaign.get("offer"),
            "",
        )

        channels = self._string_list(
            self._first_defined(
                override.get("channels"),
                raw.get("channels"),
                channels_map.get("activeChannels"),
                platform_strategy.get("activeChannels"),
                platform_strategy.get("channels"),
                campaign.get("channels"),
                [],
            )
        )

        hashtags = self._string_list(
            self._first_defined(
                override.get("hashtags"),
                raw.get("hashtags"),
                messaging.get("hashtags"),
                platform_strategy.get("hashtags"),
                campaign.get("hashtags"),
                [],
            )
        )

        keywords = self._string_list(
            self._first_defined(
                override.get("keywords"),
                raw.get("keywords"),
                messaging.get("keywords"),
                platform_strategy.get("keywords"),
                campaign.get("keywords"),
                [],
            )
        )

        hard_rules = self._string_list(
            self._first_defined(
                override.get("hard_rules"),
                override.get("hardRules"),
                raw.get("hard_rules"),
                raw.get("hardRules"),
                governance.get("hardRules"),
                governance.get("hard_rules"),
                rules.get("hard_rules"),
                rules.get("hardRules"),
                [],
            )
        )

        guidance_notes = self._string_list(
            self._first_defined(
                override.get("guidance_notes"),
                override.get("guidanceNotes"),
                raw.get("guidance_notes"),
                raw.get("guidanceNotes"),
                messaging.get("guidanceNotes"),
                messaging.get("guidance_notes"),
                rules.get("guidance_notes"),
                rules.get("guidanceNotes"),
                [],
            )
        )

        campaign_notes = self._string_list(
            self._first_defined(
                override.get("campaign_notes"),
                override.get("campaignNotes"),
                raw.get("campaign_notes"),
                raw.get("campaignNotes"),
                strategy.get("campaignNotes"),
                strategy.get("campaign_notes"),
                campaign.get("notes"),
                campaign.get("campaign_notes"),
                campaign.get("campaignNotes"),
                [],
            )
        )

        brand_overview = {
            **brand_overview,
            "whatYouDo": brand_overview.get("whatYouDo") or brand_overview.get("what_you_do") or "",
            "uniqueValueProposition": brand_overview.get("uniqueValueProposition")
            or brand_overview.get("unique_value_proposition")
            or brand_positioning.get("uniqueValueProposition")
            or "",
        }

        brand_goals = {
            **brand_goals,
            "primaryGoal": brand_goals.get("primaryGoal") or brand_goals.get("goal") or objective or "",
        }

        brand_purpose = {
            **brand_purpose,
            "purpose": brand_purpose.get("purpose") or "",
        }

        brand_vision = {
            **brand_vision,
            "vision": brand_vision.get("vision") or "",
        }

        brand_mission = {
            **brand_mission,
            "mission": brand_mission.get("mission") or "",
        }

        brand_values = {
            **brand_values,
            "values": self._string_list(brand_values.get("values") or []),
        }

        brand_positioning = {
            **brand_positioning,
            "positioning": brand_positioning.get("positioning") or "",
            "differentiation": brand_positioning.get("differentiation")
            or differentiation.get("summary")
            or "",
            "objective": objective or "",
            "offer": offer or "",
        }

        brand_voice = {
            **brand_voice,
            "voice": brand_voice.get("voice") or "",
            "tone": brand_voice.get("tone") or "",
            "communicationStyle": brand_voice.get("communicationStyle")
            or brand_voice.get("communication_style")
            or tone_of_voice.get("communicationStyle")
            or "",
            "doRules": self._string_list(
                brand_voice.get("doRules")
                or brand_voice.get("do_rules")
                or tone_of_voice.get("doRules")
                or []
            ),
            "doNotRules": self._string_list(
                brand_voice.get("doNotRules")
                or brand_voice.get("do_not_rules")
                or tone_of_voice.get("doNotRules")
                or []
            ),
            "personalityTraits": self._string_list(
                brand_voice.get("personalityTraits")
                or brand_voice.get("personality_traits")
                or []
            ),
        }

        audience = {
            **audience,
            "primaryAudience": target_audience or "",
            "targetAudience": target_audience or "",
            "target_audience": target_audience or "",
            "primaryPersona": persona or "",
            "persona": persona or "",
            "customerType": audience.get("customerType") or audience.get("customer_type") or "",
        }

        customer_pain_points = {
            **customer_pain_points,
            "painPoints": self._string_list(
                customer_pain_points.get("painPoints")
                or customer_pain_points.get("pain_points")
                or audience.get("painPoints")
                or []
            ),
            "problemsSolved": self._string_list(
                customer_pain_points.get("problemsSolved")
                or customer_pain_points.get("problems_solved")
                or []
            ),
        }

        strategy = {
            **strategy,
            "objective": objective or "",
            "funnelGoal": funnel_goal or "",
            "funnel_goal": funnel_goal or "",
            "campaignNotes": campaign_notes,
            "campaign_notes": campaign_notes,
        }

        offer_map = {
            **offer_map,
            "primaryOffer": offer or "",
            "offer": offer or "",
        }

        messaging = {
            **messaging,
            "hashtags": hashtags,
            "keywords": keywords,
            "guidanceNotes": guidance_notes,
            "guidance_notes": guidance_notes,
        }

        channels_map = {
            **channels_map,
            "activeChannels": channels,
            "active_channels": channels,
        }

        platform_strategy = {
            **platform_strategy,
            "activeChannels": platform_strategy.get("activeChannels") or channels,
            "channels": channels,
            "hashtags": hashtags,
            "keywords": keywords,
        }

        rules = {
            **rules,
            "hard_rules": hard_rules,
            "hardRules": hard_rules,
            "guidance_notes": guidance_notes,
            "guidanceNotes": guidance_notes,
        }

        governance = {
            **governance,
            "hardRules": hard_rules,
            "hard_rules": hard_rules,
        }

        campaign = {
            **campaign,
            "objective": objective or "",
            "funnel_goal": funnel_goal or "",
            "funnelGoal": funnel_goal or "",
            "offer": offer or "",
            "notes": campaign_notes,
            "campaign_notes": campaign_notes,
            "campaignNotes": campaign_notes,
        }

        normalized_brand_map = {
            **brand_map,
            "brandOverview": brand_overview,
            "brandGoals": brand_goals,
            "brandPurpose": brand_purpose,
            "brandVision": brand_vision,
            "brandMission": brand_mission,
            "brandValues": brand_values,
            "brandPositioning": brand_positioning,
            "brandPersonality": brand_personality,
            "brandVoice": brand_voice,
            "toneOfVoice": tone_of_voice,
            "brandStory": brand_story,
            "tagline": tagline,
            "audience": audience,
            "audienceSegments": audience_segments,
            "customerPersonas": customer_personas,
            "customerJourney": customer_journey,
            "customerPainPoints": customer_pain_points,
            "competitorAnalysis": competitor_analysis,
            "differentiation": differentiation,
            "strategy": strategy,
            "offer": offer_map,
            "messaging": messaging,
            "channels": channels_map,
            "platformStrategy": platform_strategy,
            "platform_strategy": platform_strategy,
            "creativeDirection": creative_direction,
            "creative_direction": creative_direction,
            "visualIdentity": visual_identity,
            "visual_identity": visual_identity,
            "governance": governance,
            "rules": rules,
            "campaign": campaign,
        }

        updated_at = self._first_defined(
            override.get("updated_at"),
            override.get("updatedAt"),
            raw.get("updated_at"),
            raw.get("updatedAt"),
            utc_now_iso(),
        )

        return {
            "objective": objective or "",
            "funnelGoal": funnel_goal or "",
            "funnel_goal": funnel_goal or "",
            "targetAudience": target_audience or "",
            "target_audience": target_audience or "",
            "persona": persona or "",
            "offer": offer or "",
            "channels": channels,
            "hashtags": hashtags,
            "keywords": keywords,
            "hardRules": hard_rules,
            "hard_rules": hard_rules,
            "guidanceNotes": guidance_notes,
            "guidance_notes": guidance_notes,
            "campaignNotes": campaign_notes,
            "campaign_notes": campaign_notes,
            "brandMap": normalized_brand_map,
            "brand_map": normalized_brand_map,
            "brandIntelligenceMap": normalized_brand_map,
            "brand_intelligence_map": normalized_brand_map,
            "updatedAt": updated_at,
            "updated_at": updated_at,
        }

    def _list_recent_audit_items(self, limit: int = 8) -> List[Any]:
        limit = max(1, min(int(limit or 8), 1000))

        db_path = Path(self.base_dir) / "audit.sqlite3"

        if db_path.exists():
            try:
                import json
                import sqlite3

                with sqlite3.connect(str(db_path)) as conn:
                    rows = conn.execute(
                        """
                        SELECT payload_json
                        FROM audit_events
                        ORDER BY rowid DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()

                items: List[Dict[str, Any]] = []

                for row in rows:
                    try:
                        value = json.loads(row[0])
                        if isinstance(value, dict):
                            items.append(value)
                    except Exception:
                        continue

                return items
            except Exception:
                pass

        if hasattr(self.audit_store, "list_recent"):
            try:
                items = list(self.audit_store.list_recent(limit=limit))
                return list(reversed(items))
            except Exception:
                return []

        if hasattr(self.audit_store, "list_all"):
            try:
                return list(reversed(list(self.audit_store.list_all())[-limit:]))
            except Exception:
                return []

        return []

    @staticmethod
    def _serialize_items(items: List[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in items:
            if hasattr(item, "to_dict"):
                try:
                    out.append(item.to_dict())
                    continue
                except Exception:
                    pass
            if hasattr(item, "model_dump"):
                try:
                    out.append(item.model_dump(mode="json"))
                    continue
                except Exception:
                    pass
            if isinstance(item, dict):
                out.append(item)
        return out

    @staticmethod
    def _item_status(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("status") or "")
        return str(getattr(item, "status", "") or "")

    @classmethod
    def _queue_counts(cls, queue_items: List[Any]) -> Dict[str, int]:
        return {
            "queued": sum(1 for item in queue_items if cls._item_status(item) == "queued"),
            "running": sum(1 for item in queue_items if cls._item_status(item) == "running"),
            "waiting_approval": sum(
                1 for item in queue_items if cls._item_status(item) == "waiting_approval"
            ),
            "completed": sum(1 for item in queue_items if cls._item_status(item) == "completed"),
            "failed": sum(1 for item in queue_items if cls._item_status(item) == "failed"),
            "cancelled": sum(1 for item in queue_items if cls._item_status(item) == "cancelled"),
        }

    @classmethod
    def _approval_counts(cls, approvals: List[Any]) -> Dict[str, int]:
        return {
            "pending": sum(1 for item in approvals if cls._item_status(item) == "pending"),
            "approved": sum(1 for item in approvals if cls._item_status(item) == "approved"),
            "rejected": sum(1 for item in approvals if cls._item_status(item) == "rejected"),
        }

    @staticmethod
    def _normalize_creative_assets(value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []

        out: List[Dict[str, Any]] = []

        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue

            asset_id = str(item.get("id") or f"asset_{index + 1}")
            asset_type = str(
                item.get("type")
                or item.get("asset_type")
                or item.get("intent")
                or "reference"
            )

            out.append(
                {
                    "id": asset_id,
                    "type": asset_type,
                    "label": item.get("label") or item.get("name") or asset_id,
                    "url": item.get("url") or item.get("asset_url") or "",
                    "file_path": item.get("file_path") or item.get("path") or "",
                    "notes": item.get("notes") or item.get("usage_notes") or "",
                    "mime_type": item.get("mime_type") or item.get("content_type"),
                    "size_bytes": item.get("size_bytes") or item.get("size"),
                    "created_at": item.get("created_at") or utc_now_iso(),
                }
            )

        return out

    @staticmethod
    def _normalize_creative_direction(value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {
                "asset_intent": "product_offer",
                "product_name": "",
                "offer_price": "",
                "offer_details": "",
                "usage_notes": "",
                "style_direction": "",
                "creative_direction": "",
            }

        return {
            "asset_intent": value.get("asset_intent")
            or value.get("assetIntent")
            or value.get("type")
            or "product_offer",
            "product_name": value.get("product_name")
            or value.get("productName")
            or value.get("subject")
            or "",
            "offer_price": value.get("offer_price")
            or value.get("offerPrice")
            or value.get("price")
            or "",
            "offer_details": value.get("offer_details")
            or value.get("offerDetails")
            or "",
            "usage_notes": value.get("usage_notes")
            or value.get("usageNotes")
            or value.get("image_usage_notes")
            or value.get("imageUsageNotes")
            or "",
            "style_direction": value.get("style_direction")
            or value.get("styleDirection")
            or "",
            "creative_direction": value.get("creative_direction")
            or value.get("creativeDirection")
            or value.get("direction")
            or "",
        }

    def _build_fallback_marketing_summary(
        self,
        marketing_runs: List[Any],
        pending_approvals: List[Any],
        resolved_approvals: List[Any],
    ) -> Dict[str, Any]:
        def get_value(item: Any, key: str, default: Any = None) -> Any:
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        def normalize_run(item: Any) -> Dict[str, Any]:
            input_payload = get_value(item, "input_payload", {}) or {}
            context = get_value(item, "context", {}) or {}
            result_payload = get_value(item, "result_payload", {}) or {}

            marketing_strategy = context.get("marketing_strategy") or input_payload.get(
                "marketing_strategy", {}
            )
            foundation = context.get("brand_foundation_snapshot") or input_payload.get(
                "brand_foundation_snapshot", {}
            )
            department_notes = context.get("department_notes") or input_payload.get(
                "department_notes", {}
            )

            creative_assets = self._normalize_creative_assets(
                input_payload.get("creative_assets")
                or context.get("creative_assets")
                or marketing_strategy.get("creative_assets")
                or []
            )

            creative_direction = self._normalize_creative_direction(
                input_payload.get("creative_direction")
                or context.get("creative_direction")
                or marketing_strategy.get("creative_direction")
                or {}
            )

            draft_caption = (
                result_payload.get("draft_caption", {}) or {}
            ).get("draft_caption") or context.get("draft_caption")

            draft_carousel_payload = result_payload.get("draft_carousel", {}) or {}
            draft_carousel = draft_carousel_payload.get("draft_carousel") or context.get(
                "draft_carousel"
            ) or []

            brand_map = foundation.get("brandMap") or foundation.get("brand_map") or {}

            return {
                "id": get_value(item, "id"),
                "workflow_id": get_value(item, "workflow_id"),
                "operator_id": get_value(item, "agent_id"),
                "department_key": get_value(item, "department_key"),
                "status": get_value(item, "status"),
                "run_id": get_value(item, "id"),
                "brief": input_payload.get("brief") or context.get("brief"),
                "objective": marketing_strategy.get("objective")
                or foundation.get("objective"),
                "funnel_goal": marketing_strategy.get("funnel_goal")
                or foundation.get("funnel_goal"),
                "target_audience": marketing_strategy.get("target_audience")
                or foundation.get("target_audience"),
                "persona": marketing_strategy.get("persona") or foundation.get("persona"),
                "offer": marketing_strategy.get("offer") or foundation.get("offer"),
                "channels": marketing_strategy.get("channels")
                or foundation.get("channels")
                or [],
                "hashtags": marketing_strategy.get("hashtags")
                or foundation.get("hashtags")
                or [],
                "keywords": marketing_strategy.get("keywords")
                or foundation.get("keywords")
                or [],
                "hard_rules": marketing_strategy.get("hard_rules")
                or department_notes.get("hard_rules")
                or foundation.get("hard_rules")
                or [],
                "guidance_notes": marketing_strategy.get("guidance_notes")
                or department_notes.get("guidance_notes")
                or foundation.get("guidance_notes")
                or [],
                "campaign_notes": marketing_strategy.get("campaign_notes")
                or department_notes.get("campaign_notes")
                or foundation.get("campaign_notes")
                or [],
                "brand_map": brand_map,
                "brandMap": brand_map,
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "draft_caption": draft_caption,
                "draft_carousel": draft_carousel,
                "connector_context": context.get("connector_context"),
                "result": result_payload,
                "created_at": get_value(item, "created_at"),
                "updated_at": get_value(item, "updated_at"),
                "started_at": get_value(item, "started_at"),
                "completed_at": get_value(item, "completed_at"),
                "failure_reason": get_value(item, "error_message"),
                "approval_request_id": get_value(item, "approval_request_id"),
                "current_step_id": get_value(item, "current_step_id"),
                "step_runs": get_value(item, "step_runs", []) or [],
            }

        return {
            "runs": [normalize_run(item) for item in marketing_runs],
            "pending_approvals": self._serialize_items(pending_approvals),
            "resolved_approvals": self._serialize_items(resolved_approvals),
            "counts": {
                "runs": len(marketing_runs),
                "pending_approvals": len(pending_approvals),
                "resolved_approvals": len(resolved_approvals),
            },
            "generated_at": utc_now_iso(),
        }

    def _build_fallback_department_summary(
        self,
        *,
        queue_items: List[Any],
        approvals: List[Any],
    ) -> List[Dict[str, Any]]:
        department_keys = ["marketing", "sales", "finance", "operations", "support"]
        labels = {
            "marketing": "Marketing",
            "sales": "Sales",
            "finance": "Finance",
            "operations": "Operations",
            "support": "Support",
        }

        def get_value(item: Any, key: str, default: Any = None) -> Any:
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        out: List[Dict[str, Any]] = []
        for key in department_keys:
            dept_items = [item for item in queue_items if get_value(item, "department_key") == key]
            dept_approvals = [item for item in approvals if get_value(item, "department_key") == key]

            queued = sum(1 for item in dept_items if self._item_status(item) == "queued")
            running = sum(1 for item in dept_items if self._item_status(item) == "running")
            completed = sum(1 for item in dept_items if self._item_status(item) == "completed")
            pending_approvals = sum(
                1 for item in dept_approvals if self._item_status(item) == "pending"
            )

            if running > 0:
                status = "running"
            elif pending_approvals > 0:
                status = "pending"
            elif queued > 0:
                status = "queued"
            else:
                status = "completed" if completed > 0 else "idle"

            out.append(
                {
                    "key": key,
                    "label": labels.get(key, key.title()),
                    "status": status,
                    "queued": queued,
                    "running": running,
                    "completed": completed,
                    "pending_approvals": pending_approvals,
                    "summary": f"{queued} queued · {running} running · {completed} completed",
                }
            )

        return out

    def _build_fallback_alerts(
        self,
        *,
        scheduler: Dict[str, Any],
        approvals: List[Any],
        queue_items: List[Any],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        if not scheduler.get("is_running"):
            alerts.append(
                {
                    "title": "Scheduler stopped",
                    "detail": "Local scheduler is not currently running.",
                    "level": "pending",
                    "scope": "runtime",
                }
            )

        pending_approvals = sum(1 for item in approvals if self._item_status(item) == "pending")
        if pending_approvals > 0:
            alerts.append(
                {
                    "title": "Pending approvals require review",
                    "detail": f"{pending_approvals} approval item(s) waiting locally.",
                    "level": "pending",
                    "scope": "approvals",
                }
            )

        failed_runs = sum(1 for item in queue_items if self._item_status(item) == "failed")
        if failed_runs > 0:
            alerts.append(
                {
                    "title": "Failed local runs detected",
                    "detail": f"{failed_runs} failed run(s) found in local queue state.",
                    "level": "failed",
                    "scope": "queue",
                }
            )

        return alerts

    def _build_fallback_dashboard_summary(
        self,
        *,
        control: Dict[str, Any],
        health: Dict[str, Any],
        scheduler: Dict[str, Any],
        queue_items: List[Any],
        approvals: List[Any],
        audit_items: List[Any],
    ) -> Dict[str, Any]:
        return {
            "workspace": {
                "workspace_id": self.config.workspace_id,
                "node_id": self.config.node_id,
                "deployment_mode": self.deployment_mode,
                "sync_mode": "local_primary",
            },
            "node": {
                "status": control.get("status", "unknown"),
                "started_at": health.get("started_at"),
            },
            "health": {
                "lifecycle_state": (
                    "healthy"
                    if control.get("status") == "running"
                    else control.get("status", "unknown")
                ),
                "last_heartbeat_at": health.get("last_heartbeat_at"),
                "last_error": health.get("last_error"),
            },
            "scheduler": scheduler,
            "queue": self._queue_counts(queue_items),
            "approvals": self._approval_counts(approvals),
            "audit_event_count": len(audit_items),
            "recent_audit": self._serialize_items(audit_items),
            "departments": self._build_fallback_department_summary(
                queue_items=queue_items,
                approvals=approvals,
            ),
            "alerts": self._build_fallback_alerts(
                scheduler=scheduler,
                approvals=approvals,
                queue_items=queue_items,
            ),
            "generated_at": utc_now_iso(),
        }

    def _build_or_fetch_summary(
        self,
        *,
        build_method_names: List[str],
        fetch_method_names: List[str],
        fallback_summary: Dict[str, Any],
        build_args: tuple[Any, ...] = (),
        build_kwargs: Optional[Dict[str, Any]] = None,
        fetch_args: tuple[Any, ...] = (),
    ) -> Dict[str, Any]:
        build_kwargs = build_kwargs or {}

        built = self._call_first_service_method(
            build_method_names,
            *build_args,
            **build_kwargs,
        )
        summary = self._extract_summary_payload(built)
        if isinstance(summary, dict) and summary:
            summary.setdefault("generated_at", utc_now_iso())
            return summary

        fetched = self._call_first_service_method_without_kwargs(
            fetch_method_names,
            *fetch_args,
        )
        summary = self._extract_summary_payload(fetched)
        if isinstance(summary, dict) and summary:
            summary.setdefault("generated_at", utc_now_iso())
            return summary

        fallback_summary.setdefault("generated_at", utc_now_iso())
        return fallback_summary

    def _safe_business_read(self, method_name: str, *args: Any, default: Any = None) -> Any:
        service = self.business_container_service
        if service is None:
            return default

        fn = getattr(service, method_name, None)
        if not callable(fn):
            return default

        try:
            result = fn(*args)
            return result if result is not None else default
        except Exception:
            return default

    @staticmethod
    def _trim_for_prompt(value: Any, *, max_chars: int = 12000) -> str:
        import json

        try:
            text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except Exception:
            text = str(value)

        if len(text) <= max_chars:
            return text

        return text[:max_chars] + "\n\n...[trimmed]"

    def _build_aion_business_context_prompt(
        self,
        *,
        prompt: str,
        provider: str,
        active_tab: str,
        context_mode: str,
        target_path: Optional[str],
        selected_live_run_id: Optional[str],
        selected_seat_id: Optional[str],
        selected_inspector_target: Optional[Dict[str, Any]],
        marketing_form: Dict[str, Any],
        brand_foundation_state: Dict[str, Any],
        dashboard_summary: Dict[str, Any],
        boardroom_snapshot: Dict[str, Any],
        operations_flow_snapshot: Dict[str, Any],
        live_agents_snapshot: Dict[str, Any],
        runs: List[Dict[str, Any]],
        approvals: List[Dict[str, Any]],
        scheduler: Dict[str, Any],
        status: Dict[str, Any],
    ) -> str:
        brand_snapshot = self._normalize_brand_foundation_snapshot(
            brand_foundation_state
            or self._safe_business_read(
                "get_brand_foundation_payload",
                self.config.workspace_id,
                default={},
            )
        )

        boardroom_center = self._as_dict(
            boardroom_snapshot.get("center")
            or boardroom_snapshot.get("summary", {}).get("center")
            or {}
        )

        boardroom_pulse = self._as_dict(
            boardroom_snapshot.get("pulse")
            or boardroom_snapshot.get("summary", {}).get("pulse")
            or {}
        )

        sales_pulse = self._as_dict(boardroom_pulse.get("sales") or {})
        cash_pulse = self._as_dict(boardroom_pulse.get("cash") or {})
        finance_pulse = self._as_dict(boardroom_pulse.get("finance") or {})
        ops_pulse = self._as_dict(boardroom_pulse.get("ops") or {})

        dashboard_queue = self._as_dict(dashboard_summary.get("queue") or {})
        dashboard_approvals = self._as_dict(dashboard_summary.get("approvals") or {})

        metric_snapshot = {
            "workspace_id": self.config.workspace_id,
            "node_id": self.config.node_id,
            "revenue": self._first_defined(
                boardroom_center.get("revenue"),
                sales_pulse.get("revenue"),
                dashboard_summary.get("revenue"),
                None,
            ),
            "cash": self._first_defined(
                boardroom_center.get("cash"),
                cash_pulse.get("onHand"),
                cash_pulse.get("on_hand"),
                dashboard_summary.get("cash"),
                None,
            ),
            "pipeline": self._first_defined(
                boardroom_center.get("pipeline"),
                ops_pulse.get("backlog"),
                None,
            ),
            "profit": self._first_defined(
                boardroom_center.get("profit"),
                dashboard_summary.get("profit"),
                None,
            ),
            "orders": sales_pulse.get("orders"),
            "conversion_rate": self._first_defined(
                sales_pulse.get("conversionRate"),
                sales_pulse.get("conversion_rate"),
                None,
            ),
            "gross_margin_pct": self._first_defined(
                finance_pulse.get("grossMarginPct"),
                finance_pulse.get("gross_margin_pct"),
                None,
            ),
            "queued_runs": dashboard_queue.get("queued"),
            "running_runs": dashboard_queue.get("running"),
            "waiting_approval_runs": dashboard_queue.get("waiting_approval"),
            "completed_runs": dashboard_queue.get("completed"),
            "failed_runs": dashboard_queue.get("failed"),
            "pending_approvals": dashboard_approvals.get("pending"),
            "approved_approvals": dashboard_approvals.get("approved"),
            "rejected_approvals": dashboard_approvals.get("rejected"),
        }

        workspace_context = {
            "metric_snapshot": metric_snapshot,
            "dashboard_summary": dashboard_summary,
            "boardroom_snapshot": boardroom_snapshot,
            "brand_foundation": brand_snapshot,
            "marketing_form": marketing_form,
            "operations_flow_snapshot": operations_flow_snapshot,
            "live_agents_snapshot": live_agents_snapshot,
            "scheduler": scheduler,
            "status": status,
            "recent_runs": runs[:10],
            "recent_approvals": approvals[:10],
        }

        return (
            "You are answering inside Aion Business Desktop.\n\n"
            "CRITICAL RULES:\n"
            "1. Answer the user's exact question first.\n"
            "2. If the user asks for a metric such as revenue, cash, profit, pipeline, orders, approvals, runs, scheduler, or node status, "
            "use metric_snapshot first.\n"
            "3. Do NOT write marketing posts unless the user explicitly asks for a post, advert, caption, campaign, or social content.\n"
            "4. Do NOT invent values. If a value is missing, say it is not available in the current workspace context.\n"
            "5. Keep the answer short and practical.\n"
            "6. Aion is the business context/orchestration layer. The selected LLM is only the reasoning engine.\n\n"
            f"USER QUESTION:\n{prompt}\n\n"
            "PRIMARY METRIC SNAPSHOT:\n"
            f"{self._trim_for_prompt(metric_snapshot, max_chars=4000)}\n\n"
            "FULL WORKSPACE CONTEXT:\n"
            f"{self._trim_for_prompt(workspace_context, max_chars=5000)}"
        )

    def _call_ollama_chat(self, *, prompt: str, model: str = "gemma4:e2b") -> str:
        import json
        import urllib.request

        url = "http://127.0.0.1:11434/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))

        return (
            data.get("response")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

    def _call_openai_chat(self, *, prompt: str) -> str:
        import json
        import os
        import urllib.request

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a clear, practical assistant running behind Aion Business Desktop.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))

        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def _call_claude_chat(self, *, prompt: str) -> str:
        import json
        import os
        import urllib.request

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()

        payload = {
            "model": model,
            "max_tokens": 1600,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = data.get("content") or []
        parts: List[str] = []

        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))

        return "\n".join(parts).strip()

    def _call_selected_ai_provider(
        self,
        *,
        provider: str,
        prompt: str,
    ) -> str:
        clean_provider = str(provider or "gemma4").strip().lower()

        if clean_provider in {
            "aion",
            "gemma",
            "gemma4",
            "gemma4:e2b",
            "local",
            "local_ai",
            "ollama",
        }:
            return self._call_ollama_chat(prompt=prompt, model="gemma4:e2b")

        if clean_provider in {"openai", "gpt", "chatgpt"}:
            return self._call_openai_chat(prompt=prompt)

        if clean_provider in {"claude", "anthropic"}:
            return self._call_claude_chat(prompt=prompt)

        return self._call_ollama_chat(prompt=prompt, model="gemma4:e2b")

    @staticmethod
    def _find_nested_value(payload: Any, key_names: set[str]) -> Any:
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key).strip().lower()
                if normalized_key in key_names and value not in (None, "", [], {}):
                    return value

            for value in payload.values():
                found = LocalNodeRuntime._find_nested_value(value, key_names)
                if found not in (None, "", [], {}):
                    return found

        if isinstance(payload, list):
            for item in payload:
                found = LocalNodeRuntime._find_nested_value(item, key_names)
                if found not in (None, "", [], {}):
                    return found

        return None

    def _build_aion_business_facts(
        self,
        *,
        dashboard_summary: Optional[Dict[str, Any]] = None,
        boardroom_snapshot: Optional[Dict[str, Any]] = None,
        brand_foundation_state: Optional[Dict[str, Any]] = None,
        runs: Optional[List[Dict[str, Any]]] = None,
        approvals: Optional[List[Dict[str, Any]]] = None,
        scheduler: Optional[Dict[str, Any]] = None,
        status: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dashboard_summary = dashboard_summary or {}
        boardroom_snapshot = boardroom_snapshot or {}
        brand_foundation_state = brand_foundation_state or {}
        runs = runs or []
        approvals = approvals or []
        scheduler = scheduler or {}
        status = status or {}

        center = self._as_dict(boardroom_snapshot.get("center"))
        pulse = self._as_dict(boardroom_snapshot.get("pulse"))
        sales = self._as_dict(pulse.get("sales"))
        cash_block = self._as_dict(pulse.get("cash"))

        revenue = (
            center.get("revenue")
            or sales.get("revenue")
            or dashboard_summary.get("revenue")
            or dashboard_summary.get("turnover")
        )

        cash = (
            center.get("cash")
            or cash_block.get("onHand")
            or cash_block.get("on_hand")
            or dashboard_summary.get("cash")
        )

        profit = (
            center.get("profit")
            or dashboard_summary.get("profit")
        )

        pipeline = (
            center.get("pipeline")
            or dashboard_summary.get("pipeline")
        )

        pending_approvals = [
            item for item in approvals
            if str(item.get("status") or "").lower() == "pending"
        ]

        failed_runs = [
            item for item in runs
            if str(item.get("status") or "").lower() == "failed"
        ]

        waiting_runs = [
            item for item in runs
            if str(item.get("status") or "").lower() in {"waiting_approval", "pending", "queued"}
        ]

        brand_map = (
            brand_foundation_state.get("brandMap")
            or brand_foundation_state.get("brand_map")
            or {}
        )

        brand_overview = self._as_dict(brand_map.get("brandOverview"))
        brand_goals = self._as_dict(brand_map.get("brandGoals"))
        audience = self._as_dict(brand_map.get("audience"))

        return {
            "workspace_id": self.config.workspace_id,
            "node_id": self.config.node_id,
            "revenue": revenue,
            "cash": cash,
            "profit": profit,
            "pipeline": pipeline,
            "business_name": (
                brand_overview.get("brandName")
                or brand_overview.get("name")
                or self.config.workspace_id
            ),
            "objective": (
                brand_foundation_state.get("objective")
                or brand_goals.get("primaryGoal")
                or brand_goals.get("objective")
            ),
            "target_audience": (
                brand_foundation_state.get("targetAudience")
                or brand_foundation_state.get("target_audience")
                or audience.get("primaryAudience")
            ),
            "offer": brand_foundation_state.get("offer"),
            "pending_approvals": len(pending_approvals),
            "failed_runs": len(failed_runs),
            "waiting_runs": len(waiting_runs),
            "scheduler_running": scheduler.get("is_running"),
            "node_status": (
                status.get("control", {}).get("status")
                if isinstance(status.get("control"), dict)
                else None
            ),
        }

    def _build_aion_business_context_prompt(
        self,
        *,
        prompt: str,
        provider: str,
        active_tab: Optional[str] = None,
        context_mode: Optional[str] = None,
        target_path: Optional[str] = None,
        selected_live_run_id: Optional[str] = None,
        selected_seat_id: Optional[str] = None,
        selected_inspector_target: Optional[Dict[str, Any]] = None,
        marketing_form: Optional[Dict[str, Any]] = None,
        brand_foundation_state: Optional[Dict[str, Any]] = None,
        dashboard_summary: Optional[Dict[str, Any]] = None,
        boardroom_snapshot: Optional[Dict[str, Any]] = None,
        operations_flow_snapshot: Optional[Dict[str, Any]] = None,
        live_agents_snapshot: Optional[Dict[str, Any]] = None,
        runs: Optional[List[Dict[str, Any]]] = None,
        approvals: Optional[List[Dict[str, Any]]] = None,
        scheduler: Optional[Dict[str, Any]] = None,
        status: Optional[Dict[str, Any]] = None,
    ) -> str:
        import json

        facts = self._build_aion_business_facts(
            dashboard_summary=dashboard_summary,
            boardroom_snapshot=boardroom_snapshot,
            brand_foundation_state=brand_foundation_state,
            runs=runs,
            approvals=approvals,
            scheduler=scheduler,
            status=status,
        )

        context = {
            "facts": facts,
            "active_tab": active_tab,
            "context_mode": context_mode,
            "target_path": target_path,
            "selected_live_run_id": selected_live_run_id,
            "selected_seat_id": selected_seat_id,
            "selected_inspector_target": selected_inspector_target,
            "dashboard_summary": dashboard_summary or {},
            "boardroom_snapshot": boardroom_snapshot or {},
            "brand_foundation_state": brand_foundation_state or {},
            "marketing_form": marketing_form or {},
            "operations_flow_snapshot": operations_flow_snapshot or {},
            "live_agents_snapshot": live_agents_snapshot or {},
            "runs": (runs or [])[:40],
            "approvals": (approvals or [])[:40],
            "scheduler": scheduler or {},
            "status": status or {},
        }

        return (
            "You are the reasoning engine used by Aion Business Desktop.\n"
            "Aion is the business context and orchestration layer. You are only the language/reasoning engine.\n\n"
            "Rules:\n"
            "- Answer from the supplied business context first.\n"
            "- Do not invent missing business numbers.\n"
            "- If a value exists in facts, use it directly.\n"
            "- If a value is missing, say it is not loaded yet and say which container/payload likely needs populating.\n"
            "- Keep the answer practical and concise.\n\n"
            f"Selected provider: {provider}\n\n"
            "BUSINESS CONTEXT JSON:\n"
            f"{json.dumps(context, ensure_ascii=False, default=str, indent=2)}\n\n"
            "USER QUESTION:\n"
            f"{prompt}"
        )

    def _call_selected_ai_provider(
        self,
        *,
        provider: str,
        prompt: str,
    ) -> str:
        clean_provider = str(provider or "gemma4").strip().lower()

        # Aion is not a model. Aion means:
        # business-context/orchestration layer + selected local/cloud reasoning engine.
        # So if provider is accidentally set to "aion", route to the free local engine.
        if clean_provider in {"aion", "aion_business", "aion_chat"}:
            clean_provider = "gemma4"

        if clean_provider in {"gemma", "gemma4", "local", "ollama"}:
            try:
                from backend.modules.aion.runtime.services.local_llm_service import (
                    LocalLLMService,
                )

                service = LocalLLMService()
                result = service.generate(prompt=prompt)

                if hasattr(result, "response"):
                    return str(getattr(result, "response") or "").strip()

                if isinstance(result, dict):
                    return str(
                        result.get("text")
                        or result.get("output")
                        or result.get("response")
                        or result.get("message")
                        or ""
                    ).strip()

                return str(result or "").strip()
            except Exception as exc:
                raise RuntimeError(
                    f"Local AI provider failed: {type(exc).__name__}: {exc}"
                ) from exc

        if clean_provider in {"openai", "gpt", "chatgpt"}:
            return self._call_openai_chat(prompt=prompt)

        if clean_provider in {"claude", "anthropic"}:
            return self._call_claude_chat(prompt=prompt)

        # Unknown provider: use local free model by default.
        try:
            from backend.modules.aion.runtime.services.local_llm_service import (
                LocalLLMService,
            )

            service = LocalLLMService()
            result = service.generate(prompt=prompt)

            if isinstance(result, dict):
                return str(
                    result.get("text")
                    or result.get("output")
                    or result.get("response")
                    or result.get("message")
                    or ""
                ).strip()

            return str(result or "").strip()
        except Exception as exc:
            raise RuntimeError(
                f"Local AI provider failed: {type(exc).__name__}: {exc}"
            ) from exc

    def ask_desktop_assistant(
        self,
        *,
        provider: str = "gemma4",
        prompt: str,
        active_tab: Optional[str] = None,
        context_mode: Optional[str] = None,
        target_path: Optional[str] = None,
        selected_live_run_id: Optional[str] = None,
        selected_seat_id: Optional[str] = None,
        selected_inspector_target: Optional[Dict[str, Any]] = None,
        marketing_form: Optional[Dict[str, Any]] = None,
        brand_foundation_state: Optional[Dict[str, Any]] = None,
        dashboard_summary: Optional[Dict[str, Any]] = None,
        boardroom_snapshot: Optional[Dict[str, Any]] = None,
        operations_flow_snapshot: Optional[Dict[str, Any]] = None,
        live_agents_snapshot: Optional[Dict[str, Any]] = None,
        runs: Optional[List[Dict[str, Any]]] = None,
        approvals: Optional[List[Dict[str, Any]]] = None,
        scheduler: Optional[Dict[str, Any]] = None,
        status: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        clean_prompt = str(prompt or "").strip()
        clean_provider = str(provider or "gemma4").strip().lower() or "gemma4"
        clean_active_tab = str(active_tab or "desktop").strip()
        clean_context_mode = str(context_mode or clean_active_tab).strip()

        if not clean_prompt:
            return {
                "ok": False,
                "text": "Ask me something first.",
                "provider": clean_provider,
                "active_tab": clean_active_tab,
                "context_mode": clean_context_mode,
                "mode": str(extra.get("mode") or clean_context_mode or "").strip().lower(),
                "used_business_context": False,
                "workspace_id": self.config.workspace_id,
                "at": utc_now_iso(),
            }

        marketing_form = marketing_form or {}
        brand_foundation_state = brand_foundation_state or {}
        dashboard_summary = dashboard_summary or {}
        boardroom_snapshot = boardroom_snapshot or {}
        operations_flow_snapshot = operations_flow_snapshot or {}
        live_agents_snapshot = live_agents_snapshot or {}
        runs = runs or []
        approvals = approvals or []
        scheduler = scheduler or {}
        status = status or {}

        mode = str(extra.get("mode") or clean_context_mode or "").strip().lower()

        use_business_context = mode in {
            "aion",
            "aion_chat",
            "business_workspace",
            "desktop",
            "dashboard",
            "boardroom",
            "brand_foundation",
            "marketing_stream",
            "live_agents",
            "operations_flow",
            "local_node",
        }

        brand_snapshot = self._normalize_brand_foundation_snapshot(
            brand_foundation_state
            or self._safe_business_read(
                "get_brand_foundation_payload",
                self.config.workspace_id,
                default={},
            )
        )

        aion_facts = self._build_aion_business_facts(
            dashboard_summary=dashboard_summary,
            boardroom_snapshot=boardroom_snapshot,
            brand_foundation_state=brand_snapshot,
            runs=runs,
            approvals=approvals,
            scheduler=scheduler,
            status=status,
        )

        prompt_lower = clean_prompt.lower()

        def _has_any(*words: str) -> bool:
            return any(word in prompt_lower for word in words)

        def _is_present(value: Any) -> bool:
            return value not in (None, "", [], {})

        def _fact_response(
            *,
            text: str,
            ok: bool = True,
            extra_payload: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            payload: Dict[str, Any] = {
                "ok": ok,
                "text": text,
                "provider": clean_provider,
                "active_tab": clean_active_tab,
                "context_mode": clean_context_mode,
                "mode": mode,
                "used_business_context": use_business_context,
                "target_path": target_path,
                "workspace_id": self.config.workspace_id,
                "facts": aion_facts,
                "at": utc_now_iso(),
            }

            if extra_payload:
                payload.update(extra_payload)

            try:
                self._append_audit(
                    event_type="local_node.desktop_assistant_fact_answered",
                    message="Desktop assistant answered directly from Aion facts",
                    payload={
                        "provider": clean_provider,
                        "active_tab": clean_active_tab,
                        "context_mode": clean_context_mode,
                        "mode": mode,
                        "target_path": target_path,
                        "prompt_preview": clean_prompt[:240],
                    },
                    level="info",
                )
            except Exception:
                pass

            return payload

        # Direct factual Aion answers.
        # These must NOT call Gemma/OpenAI/Claude because the values already live in
        # the business workspace context.
        if use_business_context:
            if _has_any("revenue", "turnover"):
                revenue = aion_facts.get("revenue")
                if _is_present(revenue):
                    return _fact_response(
                        text=(
                            f"The current revenue shown in the business workspace is {revenue}.\n\n"
                            "This is coming from the current Aion business/boardroom context, not a general AI estimate."
                        )
                    )

                return _fact_response(
                    text=(
                        "I cannot see a current revenue value in the loaded business context yet.\n\n"
                        "Check whether the boardroom/dashboard payload contains `revenue`, or whether the finance/sales container has been populated."
                    )
                )

            if _has_any("cash", "cash on hand", "bank balance", "runway"):
                cash = aion_facts.get("cash")
                if _is_present(cash):
                    return _fact_response(
                        text=(
                            f"The current cash shown in the business workspace is {cash}.\n\n"
                            "This is coming from the current Aion business/boardroom context."
                        )
                    )

                return _fact_response(
                    text="I cannot see a current cash value in the loaded business context yet."
                )

            if _has_any("profit", "margin"):
                profit = aion_facts.get("profit")
                gross_margin_pct = aion_facts.get("gross_margin_pct")

                if _is_present(profit) and _is_present(gross_margin_pct):
                    return _fact_response(
                        text=(
                            f"The current profit shown in the business workspace is {profit}.\n\n"
                            f"The gross margin shown is {gross_margin_pct}%."
                        )
                    )

                if _is_present(profit):
                    return _fact_response(
                        text=f"The current profit shown in the business workspace is {profit}."
                    )

                if _is_present(gross_margin_pct):
                    return _fact_response(
                        text=f"The current gross margin shown in the business workspace is {gross_margin_pct}%."
                    )

                return _fact_response(
                    text="I cannot see a current profit or margin value in the loaded business context yet."
                )

            if _has_any("pipeline"):
                pipeline = aion_facts.get("pipeline")
                if _is_present(pipeline):
                    return _fact_response(
                        text=f"The current pipeline shown in the business workspace is {pipeline}."
                    )

                return _fact_response(
                    text="I cannot see a current pipeline value in the loaded business context yet."
                )

            if _has_any("orders", "sales"):
                orders = aion_facts.get("orders")
                revenue = aion_facts.get("revenue")

                if _is_present(orders) and _is_present(revenue):
                    return _fact_response(
                        text=(
                            f"The business workspace currently shows {orders} order(s), "
                            f"with revenue shown as {revenue}."
                        )
                    )

                if _is_present(orders):
                    return _fact_response(
                        text=f"The business workspace currently shows {orders} order(s)."
                    )

                if _is_present(revenue):
                    return _fact_response(
                        text=f"The current sales/revenue shown in the business workspace is {revenue}."
                    )

                return _fact_response(
                    text="I cannot see current order or sales values in the loaded business context yet."
                )

            if _has_any("approval", "approvals"):
                pending = aion_facts.get("pending_approvals")
                approved = aion_facts.get("approved_approvals")
                rejected = aion_facts.get("rejected_approvals")

                if any(_is_present(v) for v in [pending, approved, rejected]):
                    return _fact_response(
                        text=(
                            "Current approvals in the business workspace:\n\n"
                            f"- Pending: {pending if _is_present(pending) else 0}\n"
                            f"- Approved: {approved if _is_present(approved) else 0}\n"
                            f"- Rejected: {rejected if _is_present(rejected) else 0}"
                        )
                    )

                return _fact_response(
                    text="I cannot see the current approval counts in the loaded business context yet."
                )

            if _has_any("queue", "runs", "run status", "failed", "waiting"):
                queued = aion_facts.get("queued_runs")
                running = aion_facts.get("running_runs")
                waiting = aion_facts.get("waiting_approval_runs")
                completed = aion_facts.get("completed_runs")
                failed = aion_facts.get("failed_runs")

                if any(_is_present(v) for v in [queued, running, waiting, completed, failed]):
                    return _fact_response(
                        text=(
                            "Current run/queue state:\n\n"
                            f"- Queued: {queued if _is_present(queued) else 0}\n"
                            f"- Running: {running if _is_present(running) else 0}\n"
                            f"- Waiting approval: {waiting if _is_present(waiting) else 0}\n"
                            f"- Completed: {completed if _is_present(completed) else 0}\n"
                            f"- Failed: {failed if _is_present(failed) else 0}"
                        )
                    )

                return _fact_response(
                    text="I cannot see the current queue/run counts in the loaded business context yet."
                )

            if _has_any("business state", "current state", "state of the business", "explain the business"):
                revenue = aion_facts.get("revenue")
                cash = aion_facts.get("cash")
                profit = aion_facts.get("profit")
                pipeline = aion_facts.get("pipeline")
                pending = aion_facts.get("pending_approvals")
                failed = aion_facts.get("failed_runs")
                running = aion_facts.get("running_runs")

                lines = ["Current business state from the Aion workspace:"]

                if _is_present(revenue):
                    lines.append(f"- Revenue: {revenue}")
                if _is_present(cash):
                    lines.append(f"- Cash: {cash}")
                if _is_present(profit):
                    lines.append(f"- Profit: {profit}")
                if _is_present(pipeline):
                    lines.append(f"- Pipeline: {pipeline}")
                if _is_present(running):
                    lines.append(f"- Running work: {running}")
                if _is_present(pending):
                    lines.append(f"- Pending approvals: {pending}")
                if _is_present(failed):
                    lines.append(f"- Failed runs: {failed}")

                if len(lines) == 1:
                    lines.append(
                        "- The business containers are loaded, but the key finance/queue metrics are not populated in the current context yet."
                    )

                lines.append("")
                lines.append(
                    "Next best action: clear pending approvals first, then inspect failed runs, then update the boardroom/dashboard finance values if they are missing."
                )

                return _fact_response(text="\n".join(lines))

            if _has_any("scheduler", "backend", "node", "local node", "runtime"):
                scheduler_running = aion_facts.get("scheduler_running")
                node_status = aion_facts.get("node_status")

                text_lines = ["Current local runtime state:"]

                if _is_present(node_status):
                    text_lines.append(f"- Node status: {node_status}")
                else:
                    text_lines.append("- Node status: not available in current context")

                if scheduler_running is not None:
                    text_lines.append(f"- Scheduler running: {scheduler_running}")
                else:
                    text_lines.append("- Scheduler running: not available in current context")

                text_lines.append("")
                text_lines.append(
                    "Check order: `/api/local-node/health`, scheduler status, queue status, then recent audit events."
                )

                return _fact_response(text="\n".join(text_lines))

        if use_business_context:
            final_prompt = self._build_aion_business_context_prompt(
                prompt=clean_prompt,
                provider=clean_provider,
                active_tab=clean_active_tab,
                context_mode=clean_context_mode,
                target_path=target_path,
                selected_live_run_id=selected_live_run_id,
                selected_seat_id=selected_seat_id,
                selected_inspector_target=selected_inspector_target,
                marketing_form=marketing_form,
                brand_foundation_state=brand_snapshot,
                dashboard_summary=dashboard_summary,
                boardroom_snapshot=boardroom_snapshot,
                operations_flow_snapshot=operations_flow_snapshot,
                live_agents_snapshot=live_agents_snapshot,
                runs=runs[:8],
                approvals=approvals[:8],
                scheduler=scheduler,
                status=status,
            )
        else:
            final_prompt = clean_prompt

        try:
            text = self._call_selected_ai_provider(
                provider=clean_provider,
                prompt=final_prompt,
            )

            if not text:
                text = "No model response returned."

            ok = True
            error_text = None

        except Exception as exc:
            ok = False
            error_text = f"{type(exc).__name__}: {exc}"
            text = (
                "The selected AI provider failed.\n\n"
                f"Provider: {clean_provider}\n"
                f"Error: {error_text}\n\n"
                "Check that Ollama is running for Gemma, or switch to OpenAI/Claude for heavier reasoning."
            )

        self._append_audit(
            event_type="local_node.desktop_assistant_asked",
            message="Desktop assistant prompt routed",
            payload={
                "provider": clean_provider,
                "active_tab": clean_active_tab,
                "context_mode": clean_context_mode,
                "mode": mode,
                "used_business_context": use_business_context,
                "target_path": target_path,
                "selected_live_run_id": selected_live_run_id,
                "selected_seat_id": selected_seat_id,
                "prompt_preview": clean_prompt[:240],
                "prompt_chars": len(final_prompt),
                "ok": ok,
                "error": error_text,
            },
            level="info" if ok else "error",
        )

        return {
            "ok": ok,
            "text": text,
            "provider": clean_provider,
            "active_tab": clean_active_tab,
            "context_mode": clean_context_mode,
            "mode": mode,
            "used_business_context": use_business_context,
            "target_path": target_path,
            "workspace_id": self.config.workspace_id,
            "facts": aion_facts,
            "at": utc_now_iso(),
        }

    def recovery_payload(self) -> Dict[str, Any]:
        self._ensure_canonical_business_containers()

        dashboard_summary_payload = self._safe_business_read(
            "get_dashboard_summary_projection",
            self.config.workspace_id,
            default={"summary": {}},
        )

        marketing_summary_payload = self._safe_business_read(
            "get_marketing_stream_summary",
            self.config.workspace_id,
            default={"summary": {}},
        )

        boardroom_payload = self._safe_business_read(
            "get_boardroom_payload",
            self.config.workspace_id,
            default={},
        )

        topology_payload = self._safe_business_read(
            "get_topology_payload",
            self.config.workspace_id,
            default={},
        )

        raw_brand_foundation = self._safe_business_read(
            "get_brand_foundation_payload",
            self.config.workspace_id,
            default={},
        )

        bindings_payload = self._safe_business_read(
            "get_binding_contract_payload",
            self.config.workspace_id,
            default={"items": []},
        )

        dashboard_summary = self._extract_summary_payload(dashboard_summary_payload) or {}
        marketing_summary = self._extract_summary_payload(marketing_summary_payload) or {}
        boardroom = self._extract_dict_payload(boardroom_payload) or {}
        topology = self._extract_dict_payload(topology_payload) or {}
        bindings = self._extract_dict_payload(bindings_payload) or {"items": []}

        brand_foundation = self._normalize_brand_foundation_snapshot(
            raw_brand_foundation,
        )

        return {
            "ok": True,
            "workspace_id": self.config.workspace_id,
            "node_id": self.config.node_id,

            "dashboard_summary": dashboard_summary,
            "dashboardSummary": dashboard_summary,

            "marketing_summary": marketing_summary,
            "marketingSummary": marketing_summary,

            "boardroom": boardroom,
            "boardroom_payload": boardroom,
            "boardroomPayload": boardroom,

            "topology": topology,

            "brand_foundation": brand_foundation,
            "brand_foundation_snapshot": brand_foundation,
            "brandFoundationState": brand_foundation,

            "brandMap": brand_foundation.get("brandMap") or {},
            "brand_map": brand_foundation.get("brand_map") or {},

            "container_bindings": bindings,
            "containerBindings": bindings,

            "at": utc_now_iso(),
        }

    def start(self) -> Dict[str, Any]:
        self.control.set_running()
        self.health.record_heartbeat(status="running")
        self.runner_host._refresh_metrics()
        self._refresh_node_snapshot("running")
        self._ensure_canonical_business_containers()

        self._append_audit(
            event_type="local_node.started",
            message="Local node runtime started",
            payload={
                "node_id": self.config.node_id,
                "workspace_id": self.config.workspace_id,
                "deployment_mode": self.deployment_mode,
            },
        )
        return self.status()

    def launch_marketing_suggestion(
        self,
        *,
        brief: str,
        objective: str | None = None,
        funnel_goal: str | None = None,
        target_audience: str | None = None,
        persona: str | None = None,
        offer: str | None = None,
        channels: List[str] | None = None,
        hashtags: List[str] | None = None,
        keywords: List[str] | None = None,
        hard_rules: List[str] | None = None,
        guidance_notes: List[str] | None = None,
        campaign_notes: List[str] | None = None,
        creative_assets: List[Dict[str, Any]] | None = None,
        creative_direction: Dict[str, Any] | None = None,
        brand_foundation: Dict[str, Any] | None = None,
        brand_foundation_state: Dict[str, Any] | None = None,
        brand_map: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._ensure_canonical_business_containers()

        normalized_creative_assets = self._normalize_creative_assets(
            creative_assets or []
        )
        normalized_creative_direction = self._normalize_creative_direction(
            creative_direction or {}
        )

        explicit_brand_payload = (
            brand_foundation_state
            or brand_foundation
            or {"brandMap": brand_map}
            if brand_map
            else None
        )

        stored_brand_payload = self._safe_business_read(
            "get_brand_foundation_payload",
            self.config.workspace_id,
            default={},
        )

        brand_foundation_snapshot = self._normalize_brand_foundation_snapshot(
            explicit_brand_payload or stored_brand_payload,
            overrides={
                "objective": objective,
                "funnel_goal": funnel_goal,
                "target_audience": target_audience,
                "persona": persona,
                "offer": offer,
                "channels": channels or [],
                "hashtags": hashtags or [],
                "keywords": keywords or [],
                "hard_rules": hard_rules or [],
                "guidance_notes": guidance_notes or [],
                "campaign_notes": campaign_notes or [],
                "updated_at": utc_now_iso(),
            },
        )

        brand_map_payload = brand_foundation_snapshot.get("brand_map") or {}

        payload = {
            "brief": brief,
            "creative_assets": normalized_creative_assets,
            "creative_direction": normalized_creative_direction,
            "marketing_strategy": {
                "objective": brand_foundation_snapshot.get("objective") or objective,
                "funnel_goal": brand_foundation_snapshot.get("funnel_goal") or funnel_goal,
                "target_audience": brand_foundation_snapshot.get("target_audience") or target_audience,
                "persona": brand_foundation_snapshot.get("persona") or persona,
                "offer": brand_foundation_snapshot.get("offer") or offer,
                "channels": brand_foundation_snapshot.get("channels") or channels or [],
                "hashtags": brand_foundation_snapshot.get("hashtags") or hashtags or [],
                "keywords": brand_foundation_snapshot.get("keywords") or keywords or [],
                "hard_rules": brand_foundation_snapshot.get("hard_rules") or hard_rules or [],
                "guidance_notes": brand_foundation_snapshot.get("guidance_notes") or guidance_notes or [],
                "campaign_notes": brand_foundation_snapshot.get("campaign_notes") or campaign_notes or [],
                "brand_map": brand_map_payload,
                "brandMap": brand_map_payload,
                "brand_foundation": brand_foundation_snapshot,
                "brandFoundationState": brand_foundation_snapshot,
                "platform_strategy": brand_map_payload.get("platform_strategy")
                or brand_map_payload.get("platformStrategy")
                or {},
                "creative_direction_layer": brand_map_payload.get("creative_direction")
                or brand_map_payload.get("creativeDirection")
                or {},
                "visual_identity": brand_map_payload.get("visual_identity")
                or brand_map_payload.get("visualIdentity")
                or {},
                "audience": brand_map_payload.get("audience") or {},
                "brand_overview": brand_map_payload.get("brandOverview") or {},
                "brand_goals": brand_map_payload.get("brandGoals") or {},
                "brand_purpose": brand_map_payload.get("brandPurpose") or {},
                "brand_vision": brand_map_payload.get("brandVision") or {},
                "brand_mission": brand_map_payload.get("brandMission") or {},
                "brand_values": brand_map_payload.get("brandValues") or {},
                "brand_positioning": brand_map_payload.get("brandPositioning") or {},
                "brand_personality": brand_map_payload.get("brandPersonality") or {},
                "brand_voice": brand_map_payload.get("brandVoice") or {},
                "tone_of_voice": brand_map_payload.get("toneOfVoice") or {},
                "brand_story": brand_map_payload.get("brandStory") or {},
                "tagline": brand_map_payload.get("tagline") or {},
                "audience_segments": brand_map_payload.get("audienceSegments") or {},
                "customer_personas": brand_map_payload.get("customerPersonas") or {},
                "customer_journey": brand_map_payload.get("customerJourney") or {},
                "customer_pain_points": brand_map_payload.get("customerPainPoints") or {},
                "competitor_analysis": brand_map_payload.get("competitorAnalysis") or {},
                "differentiation": brand_map_payload.get("differentiation") or {},
                "messaging": brand_map_payload.get("messaging") or {},
                "governance": brand_map_payload.get("governance") or {},
                "rules": brand_map_payload.get("rules") or {},
                "campaign": brand_map_payload.get("campaign") or {},
                "creative_assets": normalized_creative_assets,
                "creative_direction": normalized_creative_direction,
            },
            "brand_foundation_snapshot": brand_foundation_snapshot,
            "brandFoundationState": brand_foundation_snapshot,
            "brand_map": brand_map_payload,
            "brandMap": brand_map_payload,
            "department_notes": {
                "hard_rules": brand_foundation_snapshot.get("hard_rules") or hard_rules or [],
                "guidance_notes": brand_foundation_snapshot.get("guidance_notes") or guidance_notes or [],
                "campaign_notes": brand_foundation_snapshot.get("campaign_notes") or campaign_notes or [],
            },
            "require_approval": True,
        }

        self._call_first_service_method(
            [
                "record_marketing_intent",
                "save_marketing_intent",
                "update_marketing_container",
                "update_brand_foundation_container",
                "apply_marketing_context",
            ],
            workspace_id=self.config.workspace_id,
            payload=payload,
        )

        try:
            run = self.manual_trigger_service.launch_workflow(
                workspace_id=self.config.workspace_id,
                workflow_id="workflow_marketing_content_draft_v1",
                launched_by="local_node_marketing",
                agent_id="agent_marketing_operator_v1",
                payload=payload,
            )

            run_payload = (
                run.model_dump(mode="json")
                if hasattr(run, "model_dump")
                else run.to_dict()
                if hasattr(run, "to_dict")
                else {"id": getattr(run, "id", None)}
            )

            self._append_audit(
                event_type="local_node.marketing_workflow_launched",
                message="Marketing workflow launched on real runtime",
                payload={
                    "workflow_definition_id": "workflow_marketing_content_draft_v1",
                    "agent_definition_id": "agent_marketing_operator_v1",
                    "run_id": run_payload.get("id"),
                    "creative_asset_count": len(normalized_creative_assets),
                    "creative_direction": normalized_creative_direction,
                    "brand_foundation_has_brand_map": bool(brand_map_payload),
                },
            )

            return {"ok": True, "item": run_payload, "at": utc_now_iso()}
        except Exception as exc:
            self._append_audit(
                event_type="local_node.marketing_workflow_launch_failed",
                message="Marketing workflow launch failed",
                payload={"error": f"{type(exc).__name__}: {exc}"},
                level="error",
            )
            return {
                "ok": False,
                "detail": f"{type(exc).__name__}: {exc}",
                "at": utc_now_iso(),
            }

    def manual_launch_workflow(
        self,
        *,
        workflow_definition_id: str,
        agent_definition_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            run = self.manual_trigger_service.launch_workflow(
                workspace_id=self.config.workspace_id,
                workflow_id=workflow_definition_id,
                launched_by="local_node",
                agent_id=agent_definition_id,
                payload=context or {},
            )

            run_payload = (
                run.model_dump(mode="json")
                if hasattr(run, "model_dump")
                else run.to_dict()
                if hasattr(run, "to_dict")
                else {"id": getattr(run, "id", None)}
            )

            self._append_audit(
                event_type="local_node.workflow_manual_launch",
                message="Workflow manually launched",
                payload={
                    "workflow_definition_id": workflow_definition_id,
                    "agent_definition_id": agent_definition_id,
                    "run_id": run_payload.get("id"),
                },
            )
            return {"ok": True, "item": run_payload, "at": utc_now_iso()}
        except Exception as exc:
            self._append_audit(
                event_type="local_node.workflow_manual_launch_failed",
                message="Workflow manual launch failed",
                payload={
                    "workflow_definition_id": workflow_definition_id,
                    "agent_definition_id": agent_definition_id,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                level="error",
            )
            return {
                "ok": False,
                "detail": f"{type(exc).__name__}: {exc}",
                "at": utc_now_iso(),
            }

    def run_due_triggers(self) -> Dict[str, Any]:
        now = utc_now_iso()

        try:
            fired = self.trigger_service.fire_due_triggers(
                workspace_id=self.config.workspace_id,
                now=now,
            )

            did_work = bool(fired)
            result = {
                "ok": True,
                "did_work": did_work,
                "status": "triggered" if did_work else "idle",
                "fired_count": len(fired),
                "items": fired,
                "at": now,
            }

            if did_work:
                self._append_audit(
                    event_type="local_node.trigger_tick",
                    message="Due triggers fired",
                    payload={
                        "fired_count": len(fired),
                        "trigger_ids": [item.get("trigger_id") for item in fired],
                    },
                )

            return result
        except Exception as exc:
            self._append_audit(
                event_type="local_node.trigger_tick_failed",
                message="Due trigger scan failed",
                payload={"error": f"{type(exc).__name__}: {exc}"},
                level="error",
            )
            return {
                "ok": False,
                "did_work": False,
                "status": "error",
                "detail": f"{type(exc).__name__}: {exc}",
                "at": now,
            }

    def marketing_stream_summary(self) -> Dict[str, Any]:
        self._ensure_canonical_business_containers()

        workflow_runs = list(self.workflow_run_repository.list_all(self.config.workspace_id))
        approval_requests = list(
            self.approval_request_repository.list_all(self.config.workspace_id)
        )

        marketing_runs = [
            item for item in workflow_runs if (getattr(item, "department_key", None) or "") == "marketing"
        ]
        marketing_runs = sorted(
            marketing_runs,
            key=lambda item: getattr(item, "updated_at", None)
            or getattr(item, "created_at", None)
            or "",
            reverse=True,
        )

        pending_approvals = [
            item
            for item in approval_requests
            if (getattr(item, "department_key", None) or "") == "marketing"
            and getattr(item, "status", None) == "pending"
        ]
        resolved_approvals = [
            item
            for item in approval_requests
            if (getattr(item, "department_key", None) or "") == "marketing"
            and getattr(item, "status", None) != "pending"
        ]

        fallback_summary = self._build_fallback_marketing_summary(
            marketing_runs=marketing_runs,
            pending_approvals=pending_approvals,
            resolved_approvals=resolved_approvals,
        )

        summary = self._build_or_fetch_summary(
            build_method_names=[
                "build_marketing_stream_summary",
                "build_marketing_summary_projection",
                "project_marketing_stream_summary",
            ],
            fetch_method_names=[
                "get_marketing_stream_summary",
                "get_marketing_summary_projection",
            ],
            fallback_summary=fallback_summary,
            build_kwargs={
                "workspace_id": self.config.workspace_id,
                "workflow_runs": self._serialize_items(marketing_runs),
                "approvals": self._serialize_items(pending_approvals + resolved_approvals),
                "fallback_summary": fallback_summary,
            },
            fetch_args=(self.config.workspace_id,),
        )

        return {
            "ok": True,
            "summary": summary,
            "at": utc_now_iso(),
        }

    def stop(self) -> Dict[str, Any]:
        self.scheduler.stop()
        self.control.set_stopped()
        self.health.record_heartbeat(status="stopped")
        self._refresh_node_snapshot("stopped")

        self._append_audit(
            event_type="local_node.stopped",
            message="Local node runtime stopped",
            payload={
                "node_id": self.config.node_id,
                "workspace_id": self.config.workspace_id,
            },
        )
        return self.status()

    def pause(self) -> Dict[str, Any]:
        self.control.pause()
        self.health.record_heartbeat(status="paused")
        self._refresh_node_snapshot("paused")

        self._append_audit(
            event_type="local_node.paused",
            message="Local node runtime paused",
            payload={"node_id": self.config.node_id},
        )
        return self.status()

    def resume(self) -> Dict[str, Any]:
        self.control.resume()
        self.health.record_heartbeat(status="running")
        self._refresh_node_snapshot("running")

        self._append_audit(
            event_type="local_node.resumed",
            message="Local node runtime resumed",
            payload={"node_id": self.config.node_id},
        )
        return self.status()

    def heartbeat(self) -> Dict[str, Any]:
        control_status = self.control.get_status().get("status", "unknown")
        self.health.record_heartbeat(status=control_status)
        self._refresh_node_snapshot(control_status)
        return self.status()

    def scheduler_start(self) -> Dict[str, Any]:
        return self.scheduler.start()

    def scheduler_stop(self) -> Dict[str, Any]:
        return self.scheduler.stop()

    def scheduler_tick(self) -> Dict[str, Any]:
        return self.scheduler.tick()

    def scheduler_status(self) -> Dict[str, Any]:
        return self.scheduler.status()

    def status(self) -> Dict[str, Any]:
        recovery = self.recovery_payload()

        return {
            "ok": True,
            "config": {
                "node_id": self.config.node_id,
                "workspace_id": self.config.workspace_id,
                "deployment_mode": self.deployment_mode,
            },
            "control": self.control.get_status(),
            "health": self.health.get_status(),
            "state": self.node_state_store.get_full_state(),
            "runner": self.runner_host.get_status(),
            "scheduler": self.scheduler.status().get("scheduler", {}),
            "sync": {
                "cursors": self.sync_cursor_store.list_all(),
            },
            "business_truth": {
                "workspace_id": self.config.workspace_id,
                "canonical_containers_ready": bool(recovery),
                "dashboard_summary_ready": bool(recovery.get("dashboard_summary")),
                "marketing_summary_ready": bool(recovery.get("marketing_summary")),
                "boardroom_ready": bool(recovery.get("boardroom")),
                "topology_ready": bool(recovery.get("topology")),
                "brand_foundation_ready": bool(recovery.get("brand_foundation")),
                "brand_map_ready": bool(
                    (recovery.get("brand_foundation") or {}).get("brand_map")
                ),
                "container_bindings_ready": bool(
                    (recovery.get("container_bindings") or {}).get("items")
                ),
            },
            "agents": {
                "definitions": len(
                    self.agent_definition_repository.list_all(self.config.workspace_id)
                ),
                "workflow_definitions": len(
                    self.workflow_definition_repository.list_all(self.config.workspace_id)
                ),
                "triggers": len(
                    self.trigger_definition_repository.list_all(self.config.workspace_id)
                ),
                "workflow_runs": len(
                    self.workflow_run_repository.list_all(self.config.workspace_id)
                ),
                "approval_requests": len(
                    self.approval_request_repository.list_all(self.config.workspace_id)
                ),
            },
            "at": utc_now_iso(),
        }

    def enqueue_workflow(
        self,
        *,
        workflow_id: str,
        operator_id: str,
        department_key: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        item = self.control.create_queue_item(
            workflow_id=workflow_id,
            operator_id=operator_id,
            department_key=department_key,
            payload=payload,
        )
        self.queue_store.enqueue(item)
        self.runner_host._refresh_metrics()

        self._append_audit(
            event_type="local_node.workflow_enqueued",
            message="Workflow enqueued on local node",
            payload={
                "queue_item_id": item.id,
                "workflow_id": workflow_id,
                "operator_id": operator_id,
                "department_key": department_key,
            },
        )

        return {
            "ok": True,
            "item": item.to_dict(),
            "at": utc_now_iso(),
        }

    def run_next(self) -> Dict[str, Any]:
        if self.control.get_status().get("status") != "running":
            return {
                "ok": False,
                "status": "blocked",
                "detail": "Local node is not running",
                "at": utc_now_iso(),
            }

        self.health.record_heartbeat(status="running")
        self._refresh_node_snapshot("running")
        return self.runner_host.drain_once()

    def cancel_run(self, queue_item_id: str, *, reason: str = "cancelled") -> Dict[str, Any]:
        result = self.runner_host.cancel_item(queue_item_id, reason=reason)
        self.health.record_heartbeat(
            status=self.control.get_status().get("status", "unknown")
        )
        return {
            "ok": result.ok,
            "queue_item_id": result.queue_item_id,
            "run_id": result.run_id,
            "status": result.status,
            "detail": result.detail,
            "at": utc_now_iso(),
        }

    def resume_approval(self, queue_item_id: str) -> Dict[str, Any]:
        result = self.runner_host.resume_approved_item(queue_item_id)
        self.health.record_heartbeat(
            status=self.control.get_status().get("status", "unknown")
        )
        return {
            "ok": result.ok,
            "queue_item_id": result.queue_item_id,
            "run_id": result.run_id,
            "status": result.status,
            "detail": result.detail,
            "at": utc_now_iso(),
        }

    def dashboard_summary(self) -> Dict[str, Any]:
        self._ensure_canonical_business_containers()

        control = self.control.get_status()
        health = self.health.get_status()
        scheduler = self.scheduler.status().get("scheduler", {})
        queue_items = self.queue_store.list_all()
        approvals = self.approval_store.list_all()
        audit_items = self._list_recent_audit_items(limit=8)

        fallback_summary = self._build_fallback_dashboard_summary(
            control=control,
            health=health,
            scheduler=scheduler,
            queue_items=queue_items,
            approvals=approvals,
            audit_items=audit_items,
        )

        summary = self._build_or_fetch_summary(
            build_method_names=[
                "build_dashboard_summary",
                "build_dashboard_summary_projection",
                "project_dashboard_summary",
            ],
            fetch_method_names=[
                "get_dashboard_summary_projection",
            ],
            fallback_summary=fallback_summary,
            build_kwargs={
                "workspace_id": self.config.workspace_id,
                "control": control,
                "health": health,
                "scheduler": scheduler,
                "queue_items": self._serialize_items(queue_items),
                "approvals": self._serialize_items(approvals),
                "audit_items": self._serialize_items(audit_items),
                "fallback_summary": fallback_summary,
            },
            fetch_args=(self.config.workspace_id,),
        )

        return {
            "ok": True,
            "summary": summary,
            "at": utc_now_iso(),
        }

    def build_sync_push_request(self) -> Dict[str, Any]:
        payload = self.sync_endpoints.build_push_request()
        return payload.to_dict()

    def mark_sync_push_success(self, *, ack_token: str | None = None) -> Dict[str, Any]:
        now = utc_now_iso()
        self.sync_endpoints.mark_push_success(pushed_at=now, ack_token=ack_token)
        self._append_audit(
            event_type="local_node.sync_push_success",
            message="Local node sync push marked successful",
            payload={"ack_token": ack_token},
        )
        return {"ok": True, "pushed_at": now, "ack_token": ack_token}

    def mark_sync_pull_success(self, *, ack_token: str | None = None) -> Dict[str, Any]:
        now = utc_now_iso()
        self.sync_endpoints.mark_pull_success(pulled_at=now, ack_token=ack_token)
        self._append_audit(
            event_type="local_node.sync_pull_success",
            message="Local node sync pull marked successful",
            payload={"ack_token": ack_token},
        )
        return {"ok": True, "pulled_at": now, "ack_token": ack_token}

    def mark_sync_error(self, error: str) -> Dict[str, Any]:
        self.sync_endpoints.mark_sync_error(error)
        self._append_audit(
            event_type="local_node.sync_error",
            message="Local node sync error recorded",
            payload={"error": error},
            level="error",
        )
        return {"ok": True, "error": error, "at": utc_now_iso()}

    def apply_remote_commands(
        self,
        commands: List[Dict[str, Any]] | List[CloudSyncRemoteCommand],
    ) -> Dict[str, Any]:
        normalized: List[CloudSyncRemoteCommand] = []

        for raw in commands:
            if isinstance(raw, CloudSyncRemoteCommand):
                normalized.append(raw)
            else:
                normalized.append(
                    CloudSyncRemoteCommand(
                        id=str(raw.get("id") or ""),
                        command_type=str(raw.get("command_type") or ""),
                        target_id=raw.get("target_id"),
                        payload=raw.get("payload") or {},
                        issued_at=str(raw.get("issued_at") or utc_now_iso()),
                    )
                )

        storage_results = self.sync_endpoints.apply_remote_commands(normalized)
        execution_results: List[Dict[str, Any]] = []

        for command in normalized:
            command_type = command.command_type
            target_id = command.target_id
            payload = command.payload or {}

            if command_type == "pause":
                execution_results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "result": self.pause(),
                    }
                )
                continue

            if command_type == "resume":
                execution_results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "result": self.resume(),
                    }
                )
                continue

            if command_type == "cancel_run" and target_id:
                execution_results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "target_id": target_id,
                        "result": self.cancel_run(
                            target_id,
                            reason=str(
                                payload.get("reason") or "cancelled_by_remote_command"
                            ),
                        ),
                    }
                )
                continue

            if command_type == "resume_approval" and target_id:
                execution_results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "target_id": target_id,
                        "result": self.resume_approval(target_id),
                    }
                )
                continue

        return {
            "ok": True,
            "storage_results": storage_results,
            "execution_results": execution_results,
            "at": utc_now_iso(),
        }

    def list_workflow_runs(
        self,
        *,
        department_key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        raw_items = list(self.workflow_run_repository.list_all(self.config.workspace_id))

        def get_value(item: Any, key: str) -> Any:
            if isinstance(item, dict):
                return item.get(key)
            return getattr(item, key, None)

        if department_key:
            raw_items = [
                item
                for item in raw_items
                if (get_value(item, "department_key") or "") == department_key
            ]

        raw_items.sort(
            key=lambda item: (
                get_value(item, "updated_at")
                or get_value(item, "created_at")
                or ""
            ),
            reverse=True,
        )

        if limit is not None and limit > 0:
            raw_items = raw_items[:limit]

        items: List[Dict[str, Any]] = []
        for item in raw_items:
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                items.append(item.to_dict())
            elif isinstance(item, dict):
                items.append(item)

        return {"ok": True, "items": items, "at": utc_now_iso()}

    def list_runtime_approvals(
        self,
        *,
        department_key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        raw_items = list(self.approval_request_repository.list_all(self.config.workspace_id))

        def get_value(item: Any, key: str) -> Any:
            if isinstance(item, dict):
                return item.get(key)
            return getattr(item, key, None)

        if department_key:
            raw_items = [
                item
                for item in raw_items
                if (get_value(item, "department_key") or "") == department_key
            ]

        raw_items.sort(
            key=lambda item: (
                get_value(item, "requested_at")
                or get_value(item, "updated_at")
                or get_value(item, "created_at")
                or ""
            ),
            reverse=True,
        )

        if limit is not None and limit > 0:
            raw_items = raw_items[:limit]

        items: List[Dict[str, Any]] = []
        for item in raw_items:
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                items.append(item.to_dict())
            elif isinstance(item, dict):
                items.append(item)

        return {"ok": True, "items": items, "at": utc_now_iso()}

    def resolve_runtime_approval(
        self,
        approval_id: str,
        *,
        approve: bool,
        resolved_by: str,
        resolution_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        repository = self.approval_request_repository
        resolve_fn = getattr(repository, "resolve", None)

        if not callable(resolve_fn):
            return {
                "ok": False,
                "detail": "Approval request repository does not implement resolve()",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        resolved = resolve_fn(
            self.config.workspace_id,
            approval_id,
            approve=approve,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
            resolved_at=utc_now_iso(),
        )

        if resolved is None:
            return {
                "ok": False,
                "detail": "Approval not found",
                "approval_id": approval_id,
                "at": utc_now_iso(),
            }

        payload = (
            resolved.model_dump(mode="json")
            if hasattr(resolved, "model_dump")
            else resolved.to_dict()
            if hasattr(resolved, "to_dict")
            else {"id": approval_id}
        )

        run_payload = None
        workflow_run_id = getattr(resolved, "workflow_run_id", None)

        if workflow_run_id:
            run = self.workflow_run_repository.find_one(
                self.config.workspace_id,
                workflow_run_id,
            )

            if run is not None:
                workflow = self.workflow_definition_repository.get(
                    self.config.workspace_id,
                    run.workflow_id,
                )

                if workflow is not None:
                    resumed_run = self.workflow_execution_runtime.resume_run_after_approval(
                        workflow,
                        run.id,
                    )
                    run_payload = (
                        resumed_run.model_dump(mode="json")
                        if hasattr(resumed_run, "model_dump")
                        else resumed_run.to_dict()
                        if hasattr(resumed_run, "to_dict")
                        else {"id": getattr(resumed_run, "id", None)}
                    )

        self._append_audit(
            event_type="local_node.approval_resolved",
            message="Runtime approval resolved",
            payload={
                "approval_id": approval_id,
                "approve": approve,
                "resolved_by": resolved_by,
                "workflow_run_id": workflow_run_id,
                "run_resumed": run_payload is not None,
            },
        )

        return {
            "ok": True,
            "item": payload,
            "run": run_payload,
            "at": utc_now_iso(),
        }

    def list_queue_items(self) -> Dict[str, Any]:
        items = [item.to_dict() for item in self.queue_store.list_all()]
        return {"ok": True, "items": items}

    def list_approvals(self) -> Dict[str, Any]:
        items = [item.to_dict() for item in self.approval_store.list_all()]
        return {"ok": True, "items": items}

    def list_audit_events(self, limit: int = 100) -> Dict[str, Any]:
        items = self._serialize_items(self._list_recent_audit_items(limit=limit))

        items = sorted(
            items,
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )

        return {
            "ok": True,
            "items": items[:limit],
        }

    def list_triggers(self) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for item in self.trigger_definition_repository.list_all(self.config.workspace_id):
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                items.append(item.to_dict())
            elif isinstance(item, dict):
                items.append(item)
        return {"ok": True, "items": items, "at": utc_now_iso()}

    def list_agent_definitions(self) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for item in self.agent_definition_repository.list_all(self.config.workspace_id):
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                items.append(item.to_dict())
            elif isinstance(item, dict):
                items.append(item)
        return {"ok": True, "items": items, "at": utc_now_iso()}

    def list_workflow_definitions(self) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for item in self.workflow_definition_repository.list_all(self.config.workspace_id):
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(mode="json"))
            elif hasattr(item, "to_dict"):
                items.append(item.to_dict())
            elif isinstance(item, dict):
                items.append(item)
        return {"ok": True, "items": items, "at": utc_now_iso()}
