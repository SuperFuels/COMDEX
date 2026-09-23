from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.modules.aion_business.contracts.business_identity import BusinessType


@dataclass(frozen=True, slots=True)
class BusinessTemplate:
    id: str
    business_type: BusinessType
    name: str
    description: str
    default_departments: List[str]
    default_functions: Dict[str, List[str]]
    recommended_channels: List[str]
    recommended_revenue_streams: List[str]


class BusinessTemplateRegistry:
    """
    Minimal business template registry for first-pass topology generation.

    v1 goal:
    - provide a clean template lookup for one real business archetype
    - support future onboarding defaults
    - seed first generated boardroom / operations flow structure
    """

    def __init__(self) -> None:
        self._templates = {
            "service_business_default": BusinessTemplate(
                id="service_business_default",
                business_type="service_business",
                name="Service Business Default",
                description=(
                    "Marketing -> Sales -> Operations -> Finance -> Support operating pattern "
                    "for local and regional service businesses."
                ),
                default_departments=[
                    "ceo",
                    "marketing",
                    "sales",
                    "operations",
                    "finance",
                    "support",
                ],
                default_functions={
                    "marketing": [
                        "lead_generation",
                        "local_visibility",
                        "campaigns",
                    ],
                    "sales": [
                        "lead_response",
                        "quotation",
                        "booking_conversion",
                    ],
                    "operations": [
                        "service_delivery",
                        "scheduling",
                        "job_completion",
                    ],
                    "finance": [
                        "invoicing",
                        "collections",
                        "cash_tracking",
                    ],
                    "support": [
                        "customer_followup",
                        "issue_resolution",
                        "review_capture",
                    ],
                },
                recommended_channels=[
                    "website",
                    "phone",
                    "whatsapp",
                    "directory",
                    "facebook",
                ],
                recommended_revenue_streams=[
                    "service_sales",
                    "callout_fee",
                    "project_work",
                ],
            ),
        }

    def list_templates(self) -> List[BusinessTemplate]:
        return list(self._templates.values())

    def get_template(self, template_id: str) -> Optional[BusinessTemplate]:
        return self._templates.get(template_id)

    def get_default_for_business_type(
        self,
        business_type: BusinessType,
    ) -> Optional[BusinessTemplate]:
        for template in self._templates.values():
            if template.business_type == business_type:
                return template
        return None