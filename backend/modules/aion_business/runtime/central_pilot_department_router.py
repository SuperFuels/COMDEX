"""Central Pilot routing from approved Boardroom packages to specialist queues."""

from __future__ import annotations

import re

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentPackage,
    DepartmentPilotWorkEnvelope,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_profiles import (
    get_department_pilot_profile,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.department_pilot_runtime import (
    DepartmentPilotRuntime,
)


class DepartmentPilotDesignRequiredError(ValueError):
    def __init__(self, department_id: str, design_topics: list[str]) -> None:
        self.department_id = department_id
        self.design_topics = design_topics
        super().__init__(f"department_pilot_design_required:{department_id}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


class CentralPilotDepartmentRouter:
    def __init__(
        self,
        repository: DepartmentPilotRepository | None = None,
        runtime: DepartmentPilotRuntime | None = None,
    ) -> None:
        self.repository = repository or DepartmentPilotRepository()
        self.runtime = runtime or DepartmentPilotRuntime(self.repository)

    def route_approved_package(
        self,
        package: BoardroomAssignmentPackage,
        *,
        routed_at: str,
        routed_by: str = "central_pilot",
    ) -> list[DepartmentPilotWorkEnvelope]:
        if package.status != "approved" or not package.approval or not package.approval.approved:
            raise ValueError("central_pilot_requires_approved_boardroom_package")

        profile = get_department_pilot_profile(package.department_id)
        if profile is None:
            raise ValueError(f"unknown_department_pilot:{package.department_id}")
        if profile.get("activation_state") != "enabled":
            raise DepartmentPilotDesignRequiredError(
                package.department_id, list(profile.get("design_topics") or [])
            )

        routed: list[DepartmentPilotWorkEnvelope] = []
        for action in package.actions:
            task_id = "-".join(
                part
                for part in (
                    package.department_id,
                    _slug(package.package_id),
                    _slug(action.action_id),
                )
                if part
            )
            path = self.repository.task_path(
                package.workspace_id, package.department_id, task_id
            )
            if path.exists():
                existing = self.repository.load(
                    package.workspace_id, package.department_id, task_id
                )
                if (
                    existing.package.package_hash != package.package_hash
                    or existing.task.action_id != action.action_id
                ):
                    raise ValueError(f"central_pilot_task_id_collision:{task_id}")
                routed.append(existing)
                continue

            provenance = create_provenance(
                created_by=routed_by,
                created_at=routed_at,
                source_system="aion_central_pilot",
                source_record_id=package.package_id,
                source_hash=package.package_hash,
                correlation_id=package.boardroom_session_id,
            )
            routed.append(
                self.runtime.enqueue_approved_action(
                    package=package,
                    action_id=action.action_id,
                    task_id=task_id,
                    pilot_id=str(profile["pilot_id"]),
                    assigned_at=routed_at,
                    provenance=provenance,
                    created_event_id=f"{task_id}-created",
                )
            )
        return routed
