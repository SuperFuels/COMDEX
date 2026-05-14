from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.sector_template_presets import get_sector_template_presets_v0
from backend.modules.aion_equities.sector_template_store import SectorTemplateStore


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class SectorTemplateSeedRuntime:
    def __init__(self, *, sector_template_store: SectorTemplateStore):
        self.sector_template_store = sector_template_store

    def seed_presets_v0(
        self,
        *,
        as_of_date: Optional[Any] = None,
        created_by: str = "aion_equities.sector_template_seed_runtime",
        validate: bool = False,
    ) -> List[Dict[str, Any]]:
        as_of_date = as_of_date or _utc_today()
        out: List[Dict[str, Any]] = []
        for preset in get_sector_template_presets_v0():
            payload = self.sector_template_store.save_sector_template(
                sector_ref=preset["sector_ref"],
                sector_name=preset["sector_name"],
                as_of_date=as_of_date,
                created_by=created_by,
                variable_map_patch=preset.get("variable_map_patch"),
                reporting_template_patch=preset.get("reporting_template_patch"),
                fingerprint_defaults_patch=preset.get("fingerprint_defaults_patch"),
                validate=validate,
            )
            out.append(payload)
        return out


__all__ = ["SectorTemplateSeedRuntime"]