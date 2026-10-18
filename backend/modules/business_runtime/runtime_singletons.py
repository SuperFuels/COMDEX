from __future__ import annotations

from typing import Optional

from backend.modules.business_runtime.approval_runtime import ApprovalRuntime
from backend.modules.business_runtime.operator_registry import OperatorRegistry
from backend.modules.business_runtime.workflow_repository import WorkflowRepository
from backend.modules.business_runtime.workflow_runtime import WorkflowRuntime


_workflow_repository: Optional[WorkflowRepository] = None
_operator_registry: Optional[OperatorRegistry] = None
_approval_runtime: Optional[ApprovalRuntime] = None
_workflow_runtime: Optional[WorkflowRuntime] = None


def get_workflow_repository() -> WorkflowRepository:
    global _workflow_repository
    if _workflow_repository is None:
        _workflow_repository = WorkflowRepository()
    return _workflow_repository


def get_operator_registry() -> OperatorRegistry:
    global _operator_registry
    if _operator_registry is None:
        _operator_registry = OperatorRegistry()
    return _operator_registry


def get_approval_runtime() -> ApprovalRuntime:
    global _approval_runtime
    if _approval_runtime is None:
        _approval_runtime = ApprovalRuntime()
    return _approval_runtime


def get_workflow_runtime() -> WorkflowRuntime:
    global _workflow_runtime
    if _workflow_runtime is None:
        _workflow_runtime = WorkflowRuntime(
            get_workflow_repository(),
            get_operator_registry(),
            get_approval_runtime(),
        )
    return _workflow_runtime


def reset_runtime_singletons() -> None:
    global _workflow_repository
    global _operator_registry
    global _approval_runtime
    global _workflow_runtime

    _workflow_repository = None
    _operator_registry = None
    _approval_runtime = None
    _workflow_runtime = None