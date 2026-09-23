from __future__ import annotations

from typing import Any, Dict


class RoleActionPlanner:
    """
    Deterministic v1 planner.
    Converts role context + user request into a bounded task plan.
    """

    def plan(
        self,
        *,
        workspace: Any,
        role: Any,
        role_context: Dict[str, Any],
        user_request: str,
    ) -> Dict[str, Any]:
        text = (user_request or "").strip().lower()
        binding_ids = role_context.get("resolved_container_binding_ids", []) or []
        business_type = getattr(workspace, "business_type", "general")

        if "competitor" in text:
            return {
                "task_type": "competitor_review",
                "objective": f"Review competitor positioning and messaging for this {business_type} business",
                "priority": "high",
                "required_bindings": binding_ids,
                "required_skills": [
                    "read_container",
                    "summarize_docs",
                    "produce_report",
                ],
            }

        if "email" in text or "campaign" in text:
            return {
                "task_type": "campaign_review",
                "objective": f"Review current campaign context and propose improved email direction for this {business_type} business",
                "priority": "high",
                "required_bindings": binding_ids,
                "required_skills": [
                    "read_container",
                    "summarize_docs",
                    "produce_report",
                ],
            }

        if "social" in text or "post" in text:
            return {
                "task_type": "social_content_batch",
                "objective": f"Prepare social content direction for this {business_type} business",
                "priority": "medium",
                "required_bindings": binding_ids,
                "required_skills": [
                    "read_container",
                    "summarize_docs",
                    "draft_content",
                ],
            }

        return {
            "task_type": "general_role_support",
            "objective": f"Support {role.role_type} priorities for this {business_type} business",
            "priority": "medium",
            "required_bindings": binding_ids,
            "required_skills": [
                "read_container",
                "summarize_docs",
                "produce_report",
            ],
        }