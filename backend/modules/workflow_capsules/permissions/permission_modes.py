from __future__ import annotations

from enum import Enum


class PermissionMode(str, Enum):
    REVIEW = "review"
    DRAFT_AUTO = "draft_auto"
    TRUSTED_WORKFLOW = "trusted_workflow"
    AUTO_WITH_EXCEPTIONS = "auto_with_exceptions"
    FULL_AUTO = "full_auto"
    MANUAL_ONLY = "manual_only"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class PermissionDecision(str, Enum):
    AUTO_RUN = "auto_run"
    DRAFT_ONLY = "draft_only"
    REQUEST_APPROVAL = "request_approval"
    BLOCK = "block"
