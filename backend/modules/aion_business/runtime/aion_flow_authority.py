"""Canonical workspace and organisation authority for AION Flow.

Browser-supplied role labels are deliberately ignored.  A person may use a
workflow operation only when the active workspace exists and the canonical
organisation authority container grants the corresponding capability.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.modules.aion_business.runtime.organization_authority_service import (
    OrganizationAuthorityService,
)
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


class AionFlowWorkspaceAuthority:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository | None = None,
        organisations: OrganizationAuthorityService | None = None,
    ) -> None:
        self.workspaces = workspaces or WorkspaceRepository()
        self.organisations = organisations or OrganizationAuthorityService()

    def authorize(
        self,
        actor: Mapping[str, Any],
        capability: str,
        *,
        graph: Mapping[str, Any] | None = None,
        expected_workspace_id: str | None = None,
        expected_organisation_id: str | None = None,
    ) -> dict[str, Any]:
        workspace_id = str(actor.get("workspace_id") or "").strip()
        person_id = str(actor.get("person_id") or actor.get("actor_id") or "").strip()
        claimed_organisation_id = str(actor.get("organisation_id") or actor.get("organization_id") or "").strip()
        graph = graph or {}

        if not workspace_id:
            return self._deny(person_id, capability, "workspace_id_required")
        if not person_id:
            return self._deny(person_id, capability, "person_id_required", workspace_id)

        try:
            workspace = self.workspaces.load(workspace_id)
        except FileNotFoundError:
            return self._deny(person_id, capability, "workspace_not_found", workspace_id)
        if workspace.status != "active":
            return self._deny(person_id, capability, "workspace_not_active", workspace_id)

        # The current canonical organisation boundary is the workspace.  A future
        # group layer may bind several workspaces, but a browser cannot invent it.
        organisation_id = workspace.id
        if claimed_organisation_id and claimed_organisation_id != organisation_id:
            return self._deny(person_id, capability, "organisation_workspace_mismatch", workspace_id)
        if expected_workspace_id and expected_workspace_id != workspace_id:
            return self._deny(person_id, capability, "workflow_workspace_mismatch", workspace_id)
        if expected_organisation_id and expected_organisation_id != organisation_id:
            return self._deny(person_id, capability, "workflow_organisation_mismatch", workspace_id)

        graph_workspace = str(graph.get("workspace_id") or "").strip()
        graph_organisation = str(graph.get("organisation_id") or graph.get("organization_id") or "").strip()
        if graph_workspace and graph_workspace != workspace_id:
            return self._deny(person_id, capability, "graph_workspace_mismatch", workspace_id)
        if graph_organisation and graph_organisation != organisation_id:
            return self._deny(person_id, capability, "graph_organisation_mismatch", workspace_id)

        decision = self.organisations.access_decision(
            workspace_id,
            person_id=person_id,
            capability=capability,
            department_id=str(graph.get("department_id") or "").strip() or None,
        )
        return {
            **decision,
            "workspace_id": workspace_id,
            "organisation_id": organisation_id,
            "claimed_role_ignored": bool(actor.get("role")),
            "authority_source": "workspace_repository+organization_authority.v1",
        }

    @staticmethod
    def _deny(
        person_id: str,
        capability: str,
        reason: str,
        workspace_id: str = "",
    ) -> dict[str, Any]:
        return {
            "allowed": False,
            "person_id": person_id,
            "capability": capability,
            "reason": reason,
            "workspace_id": workspace_id,
            "organisation_id": workspace_id,
            "claimed_role_ignored": True,
            "authority_source": "workspace_repository+organization_authority.v1",
        }
