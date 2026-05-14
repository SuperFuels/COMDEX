from __future__ import annotations

from typing import Any, Dict, List

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillExecutionError,
    SkillValidationError,
)


class ProduceReportSkill(BaseSkill):
    """
    v1 structured report builder.

    This skill does not read containers directly.
    It turns an existing structured summary or analysis payload into a
    normalized report object that downstream workflows can store, review,
    or pass into provider/model layers later.

    Expected input_payload:
    {
        "report_type": "campaign_context_report",
        "title": "Broadband campaign context review",
        "source_data": {...}
    }

    Optional:
    {
        "highlights": [...],
        "recommendations": [...],
        "metadata": {...}
    }
    """

    @property
    def skill_id(self) -> str:
        return "produce_report"

    def validate_request(self, request: SkillRunRequest) -> None:
        super().validate_request(request)

        report_type = request.input_payload.get("report_type")
        if not report_type or not isinstance(report_type, str):
            raise SkillValidationError("missing_report_type")

        title = request.input_payload.get("title")
        if not title or not isinstance(title, str):
            raise SkillValidationError("missing_title")

        source_data = request.input_payload.get("source_data")
        if source_data is None or not isinstance(source_data, dict):
            raise SkillValidationError("missing_source_data")

        highlights = request.input_payload.get("highlights")
        if highlights is not None and not isinstance(highlights, list):
            raise SkillValidationError("highlights_must_be_list")

        recommendations = request.input_payload.get("recommendations")
        if recommendations is not None and not isinstance(recommendations, list):
            raise SkillValidationError("recommendations_must_be_list")

        metadata = request.input_payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise SkillValidationError("metadata_must_be_object")

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        try:
            report_type = str(request.input_payload["report_type"])
            title = str(request.input_payload["title"])
            source_data = dict(request.input_payload["source_data"])
            highlights = list(request.input_payload.get("highlights", []))
            recommendations = list(request.input_payload.get("recommendations", []))
            metadata = dict(request.input_payload.get("metadata", {}))

            report = self._build_report(
                report_type=report_type,
                title=title,
                objective=request.objective,
                source_data=source_data,
                highlights=highlights,
                recommendations=recommendations,
                metadata=metadata,
            )

            return SkillRunResult(
                ok=True,
                skill_id=self.skill_id,
                output_payload={
                    "report": report,
                    "report_type": report_type,
                    "title": title,
                },
                artifacts=[],
                warnings=[],
                error_code=None,
                trace={
                    "report_type": report_type,
                    "title": title,
                    "source_keys": sorted(source_data.keys()),
                },
                side_effects_applied=False,
            )

        except Exception as exc:
            raise SkillExecutionError(f"report_build_failed:{exc}") from exc

    def _build_report(
        self,
        *,
        report_type: str,
        title: str,
        objective: str,
        source_data: Dict[str, Any],
        highlights: List[Any],
        recommendations: List[Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized_highlights = self._normalize_list_items(highlights)
        normalized_recommendations = self._normalize_list_items(recommendations)

        if not normalized_highlights:
            normalized_highlights = self._derive_highlights(source_data)

        return {
            "report_type": report_type,
            "title": title,
            "objective": objective,
            "summary": self._build_summary(source_data),
            "highlights": normalized_highlights,
            "recommendations": normalized_recommendations,
            "source_data": source_data,
            "metadata": metadata,
        }

    @staticmethod
    def _normalize_list_items(items: List[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                out.append(item)
            else:
                out.append({"text": str(item)})
        return out

    @staticmethod
    def _build_summary(source_data: Dict[str, Any]) -> str:
        keys = sorted(source_data.keys())
        if not keys:
            return "No source data provided."
        return f"Report generated from structured source data with keys: {', '.join(keys)}."

    @staticmethod
    def _derive_highlights(source_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        highlights: List[Dict[str, Any]] = []

        for key in sorted(source_data.keys()):
            value = source_data[key]

            if isinstance(value, (str, int, float, bool)):
                highlights.append({"key": key, "value": value})
            elif isinstance(value, list):
                highlights.append({"key": key, "count": len(value)})
            elif isinstance(value, dict):
                highlights.append({"key": key, "fields": sorted(value.keys())})
            else:
                highlights.append({"key": key, "value_type": type(value).__name__})

        return highlights[:10]