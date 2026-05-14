from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)

router = APIRouter(
    prefix="/api/aion/business/brand-foundation",
    tags=["aion-business-brand-foundation"],
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def get_business_container_service() -> BusinessContainerService:
    return BusinessContainerService()


class BrandFoundationPayload(BaseModel):
    # Flat compatibility fields
    objective: Optional[str] = None
    funnelGoal: Optional[str] = None
    funnel_goal: Optional[str] = None
    targetAudience: Optional[str] = None
    target_audience: Optional[str] = None
    persona: Optional[str] = None
    offer: Optional[str] = None

    channels: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    hardRules: List[str] = Field(default_factory=list)
    hard_rules: List[str] = Field(default_factory=list)

    guidanceNotes: List[str] = Field(default_factory=list)
    guidance_notes: List[str] = Field(default_factory=list)

    campaignNotes: List[str] = Field(default_factory=list)
    campaign_notes: List[str] = Field(default_factory=list)

    # New layered brand foundation map
    brandMap: Dict[str, Any] = Field(default_factory=dict)
    brand_map: Dict[str, Any] = Field(default_factory=dict)

    brandIntelligenceMap: Dict[str, Any] = Field(default_factory=dict)
    brand_intelligence_map: Dict[str, Any] = Field(default_factory=dict)

    # Optional metadata
    updatedAt: Optional[str] = None
    updated_at: Optional[str] = None


class BrandFoundationResponse(BaseModel):
    ok: bool = True
    workspace_id: str
    item: Dict[str, Any]


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]

    if isinstance(value, str):
        return [
            part.strip()
            for part in value.replace("•", "\n")
            .replace("·", "\n")
            .replace("|", "\n")
            .replace(",", "\n")
            .splitlines()
            if part.strip()
        ]

    return []


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict) and value:
            return value
    return {}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_payload(payload: BrandFoundationPayload) -> Dict[str, Any]:
    raw = payload.model_dump(exclude_none=True)

    funnel_goal = _first_value(raw.get("funnelGoal"), raw.get("funnel_goal"), "")
    target_audience = _first_value(
        raw.get("targetAudience"),
        raw.get("target_audience"),
        "",
    )

    hard_rules = _as_list(
        _first_value(raw.get("hardRules"), raw.get("hard_rules"), []),
    )
    guidance_notes = _as_list(
        _first_value(raw.get("guidanceNotes"), raw.get("guidance_notes"), []),
    )
    campaign_notes = _as_list(
        _first_value(raw.get("campaignNotes"), raw.get("campaign_notes"), []),
    )

    channels = _as_list(raw.get("channels", []))
    hashtags = _as_list(raw.get("hashtags", []))
    keywords = _as_list(raw.get("keywords", []))

    brand_map = _first_dict(
        raw.get("brandMap"),
        raw.get("brand_map"),
        raw.get("brandIntelligenceMap"),
        raw.get("brand_intelligence_map"),
    )

    # Preserve newer layered map structure from the desktop UI.
    # Also backfill key sections from flat fields so old/new payloads both work.
    brand_map = {
        **brand_map,
        "brandOverview": {
            **_as_dict(brand_map.get("brandOverview")),
        },
        "brandGoals": {
            **_as_dict(brand_map.get("brandGoals")),
        },
        "brandPurpose": {
            **_as_dict(brand_map.get("brandPurpose")),
        },
        "brandVision": {
            **_as_dict(brand_map.get("brandVision")),
        },
        "brandMission": {
            **_as_dict(brand_map.get("brandMission")),
        },
        "brandValues": {
            **_as_dict(brand_map.get("brandValues")),
        },
        "brandPositioning": {
            **_as_dict(brand_map.get("brandPositioning")),
        },
        "brandPersonality": {
            **_as_dict(brand_map.get("brandPersonality")),
        },
        "brandVoice": {
            **_as_dict(brand_map.get("brandVoice")),
        },
        "toneOfVoice": {
            **_as_dict(brand_map.get("toneOfVoice")),
        },
        "brandStory": {
            **_as_dict(brand_map.get("brandStory")),
        },
        "tagline": {
            **_as_dict(brand_map.get("tagline")),
        },
        "audience": {
            **_as_dict(brand_map.get("audience")),
            "primaryAudience": _first_value(
                _as_dict(brand_map.get("audience")).get("primaryAudience"),
                target_audience,
            ),
            "primaryPersona": _first_value(
                _as_dict(brand_map.get("audience")).get("primaryPersona"),
                raw.get("persona"),
                "",
            ),
        },
        "audienceSegments": {
            **_as_dict(brand_map.get("audienceSegments")),
        },
        "customerPersonas": {
            **_as_dict(brand_map.get("customerPersonas")),
        },
        "customerJourney": {
            **_as_dict(brand_map.get("customerJourney")),
        },
        "customerPainPoints": {
            **_as_dict(brand_map.get("customerPainPoints")),
        },
        "competitorAnalysis": {
            **_as_dict(brand_map.get("competitorAnalysis")),
        },
        "differentiation": {
            **_as_dict(brand_map.get("differentiation")),
        },
        "strategy": {
            **_as_dict(brand_map.get("strategy")),
            "objective": _first_value(
                _as_dict(brand_map.get("strategy")).get("objective"),
                raw.get("objective"),
                "",
            ),
            "funnelGoal": _first_value(
                _as_dict(brand_map.get("strategy")).get("funnelGoal"),
                funnel_goal,
            ),
            "campaignNotes": _first_value(
                _as_dict(brand_map.get("strategy")).get("campaignNotes"),
                campaign_notes,
            ),
        },
        "offer": {
            **_as_dict(brand_map.get("offer")),
            "primaryOffer": _first_value(
                _as_dict(brand_map.get("offer")).get("primaryOffer"),
                raw.get("offer"),
                "",
            ),
        },
        "messaging": {
            **_as_dict(brand_map.get("messaging")),
            "hashtags": _first_value(
                _as_dict(brand_map.get("messaging")).get("hashtags"),
                hashtags,
            ),
            "keywords": _first_value(
                _as_dict(brand_map.get("messaging")).get("keywords"),
                keywords,
            ),
            "guidanceNotes": _first_value(
                _as_dict(brand_map.get("messaging")).get("guidanceNotes"),
                guidance_notes,
            ),
        },
        "channels": {
            **_as_dict(brand_map.get("channels")),
            "activeChannels": _first_value(
                _as_dict(brand_map.get("channels")).get("activeChannels"),
                channels,
            ),
        },
        "platformStrategy": {
            **_as_dict(brand_map.get("platformStrategy")),
        },
        "creativeDirection": {
            **_as_dict(brand_map.get("creativeDirection")),
        },
        "visualIdentity": {
            **_as_dict(brand_map.get("visualIdentity")),
        },
        "governance": {
            **_as_dict(brand_map.get("governance")),
            "hardRules": _first_value(
                _as_dict(brand_map.get("governance")).get("hardRules"),
                hard_rules,
            ),
        },
    }

    updated_at = _first_value(
        raw.get("updatedAt"),
        raw.get("updated_at"),
        _utc_now_iso(),
    )

    return {
        # Flat compatibility fields
        "objective": raw.get("objective") or brand_map["strategy"].get("objective") or "",
        "funnelGoal": funnel_goal or brand_map["strategy"].get("funnelGoal") or "",
        "funnel_goal": funnel_goal or brand_map["strategy"].get("funnelGoal") or "",
        "targetAudience": target_audience
        or brand_map["audience"].get("primaryAudience")
        or "",
        "target_audience": target_audience
        or brand_map["audience"].get("primaryAudience")
        or "",
        "persona": raw.get("persona") or brand_map["audience"].get("primaryPersona") or "",
        "offer": raw.get("offer") or brand_map["offer"].get("primaryOffer") or "",
        "channels": channels or brand_map["channels"].get("activeChannels") or [],
        "hashtags": hashtags or brand_map["messaging"].get("hashtags") or [],
        "keywords": keywords or brand_map["messaging"].get("keywords") or [],
        "hardRules": hard_rules or brand_map["governance"].get("hardRules") or [],
        "hard_rules": hard_rules or brand_map["governance"].get("hardRules") or [],
        "guidanceNotes": guidance_notes
        or brand_map["messaging"].get("guidanceNotes")
        or [],
        "guidance_notes": guidance_notes
        or brand_map["messaging"].get("guidanceNotes")
        or [],
        "campaignNotes": campaign_notes
        or brand_map["strategy"].get("campaignNotes")
        or [],
        "campaign_notes": campaign_notes
        or brand_map["strategy"].get("campaignNotes")
        or [],
        # New canonical map fields
        "brandMap": brand_map,
        "brand_map": brand_map,
        "brandIntelligenceMap": brand_map,
        "brand_intelligence_map": brand_map,
        "updatedAt": updated_at,
        "updated_at": updated_at,
    }


@router.get("/{workspace_id}", response_model=BrandFoundationResponse)
def get_brand_foundation(workspace_id: str) -> BrandFoundationResponse:
    service = get_business_container_service()

    try:
        payload = service.get_brand_foundation_payload(workspace_id)

        if not isinstance(payload, dict):
            payload = {}

        normalized = _normalize_payload(BrandFoundationPayload(**payload))

        return BrandFoundationResponse(
            ok=True,
            workspace_id=workspace_id,
            item=normalized,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post("/{workspace_id}", response_model=BrandFoundationResponse)
def save_brand_foundation(
    workspace_id: str,
    payload: BrandFoundationPayload,
) -> BrandFoundationResponse:
    service = get_business_container_service()

    try:
        normalized = _normalize_payload(payload)

        saved = service.save_brand_foundation_payload(
            workspace_id,
            normalized,
        )

        if not isinstance(saved, dict):
            saved = normalized

        # Ensure response always returns the full canonical shape.
        saved = _normalize_payload(BrandFoundationPayload(**saved))

        return BrandFoundationResponse(
            ok=True,
            workspace_id=workspace_id,
            item=saved,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc