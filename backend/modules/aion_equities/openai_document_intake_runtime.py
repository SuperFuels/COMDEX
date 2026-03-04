# /workspaces/COMDEX/backend/modules/aion_equities/openai_document_intake_runtime.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.modules.aion_equities.openai_company_profile_mapper import (
    OpenAICompanyProfileMapper,
)
from backend.modules.aion_equities.openai_document_analysis_runtime import (
    OpenAIDocumentAnalysisRuntime,
)


class OpenAIDocumentIntakeRuntime:
    """
    End-to-end document intake bridge.

    Responsibilities:
    - call OpenAI document analysis runtime
    - normalize the analysis result
    - map normalized analysis into persistence-ready AION intake objects
    - return one consolidated intake artifact

    This is the first document-in -> structured-artifact-out bridge for
    company intelligence intake.
    """

    def __init__(
        self,
        *,
        document_analysis_runtime: OpenAIDocumentAnalysisRuntime,
        company_profile_mapper: OpenAICompanyProfileMapper,
    ):
        self.document_analysis_runtime = document_analysis_runtime
        self.company_profile_mapper = company_profile_mapper

    def run_document_intake(
        self,
        *,
        company_ref: str,
        document_ref: str,
        document_text: str,
        document_type: str = "board_pack",
        thesis_ref: Optional[str] = None,
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
        generated_by: str = "aion_equities.openai_document_intake_runtime",
    ) -> Dict[str, Any]:
        analysis_out = self.document_analysis_runtime.analyze_document(
            company_ref=company_ref,
            document_ref=document_ref,
            document_text=document_text,
            document_type=document_type,
            thesis_ref=thesis_ref,
            current_business_status=deepcopy(current_business_status or {}),
            company_intelligence_pack=deepcopy(company_intelligence_pack or {}),
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        mapped_objects = self.company_profile_mapper.map_analysis_to_company_profile(
            company_ref=company_ref,
            document_ref=document_ref,
            analysis_response=deepcopy(analysis_out),
            thesis_ref=thesis_ref,
            generated_by=generated_by,
        )

        return {
            "company_ref": str(company_ref),
            "document_ref": str(document_ref),
            "document_type": str(document_type),
            "thesis_ref": thesis_ref,
            "analysis_packet": deepcopy(analysis_out["analysis_packet"]),
            "analysis_response": deepcopy(analysis_out["analysis_response"]),
            "normalized_analysis": deepcopy(analysis_out["normalized_analysis"]),
            "mapped_objects": deepcopy(mapped_objects),
        }

    # compatibility alias
    def intake_document(self, **kwargs: Any) -> Dict[str, Any]:
        return self.run_document_intake(**kwargs)


__all__ = [
    "OpenAIDocumentIntakeRuntime",
]