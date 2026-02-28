from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import json

# v0.1 is the current locked schema pack for the investing runtime bootstrap
DEFAULT_SCHEMA_VERSION = "v0_1"


@dataclass(frozen=True)
class SchemaRef:
    name: str
    version: str
    path: Path


class AionEquitiesSchemaRegistry:
    """
    Versioned schema registry for AION Equities schema packs.

    Expected layout:
      backend/modules/aion_equities/schemas/
        v0_1/
          assessment.schema.json
          thesis_state.schema.json
          kg_edge.schema.json
          write_event_envelope.schema.json
          company.schema.json
          quarter_event.schema.json
          catalyst_event.schema.json
          observer_decision_cycle.schema.json
          macro_regime.schema.json
          top_down_levers_snapshot.schema.json
          country_ambassador.schema.json
          country_relationship.schema.json
          global_capital_markets.schema.json
          sector_template.schema.json
          company_structural_profile.schema.json
          credit_trajectory.schema.json
          sqi_field_mapping.v0_1.json
    """

    _SCHEMA_FILES: Dict[str, str] = {
        "assessment": "assessment.schema.json",
        "thesis_state": "thesis_state.schema.json",
        "kg_edge": "kg_edge.schema.json",
        "write_event_envelope": "write_event_envelope.schema.json",
        "company": "company.schema.json",
        "quarter_event": "quarter_event.schema.json",
        "catalyst_event": "catalyst_event.schema.json",
        "observer_decision_cycle": "observer_decision_cycle.schema.json",
        "macro_regime": "macro_regime.schema.json",
        "top_down_levers_snapshot": "top_down_levers_snapshot.schema.json",
        "country_ambassador": "country_ambassador.schema.json",
        "country_relationship": "country_relationship.schema.json",
        "global_capital_markets": "global_capital_markets.schema.json",
        "sector_template": "sector_template.schema.json",
        "company_structural_profile": "company_structural_profile.schema.json",
        "credit_trajectory": "credit_trajectory.schema.json",
        # mapping doc (not JSON Schema, but versioned alongside schemas)
        "sqi_field_mapping": "sqi_field_mapping.v0_1.json",
    }

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        default_version: str = DEFAULT_SCHEMA_VERSION,
    ):
        self._base_dir = base_dir or Path(__file__).resolve().parent / "schemas"
        self._default_version = default_version
        self._cache: Dict[str, dict] = {}

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @property
    def default_version(self) -> str:
        return self._default_version

    def available_versions(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        return sorted(
            [
                p.name
                for p in self._base_dir.iterdir()
                if p.is_dir() and p.name.startswith("v")
            ]
        )

    def available_schema_names(self) -> list[str]:
        return sorted(self._SCHEMA_FILES.keys())

    def resolve(self, schema_name: str, version: Optional[str] = None) -> SchemaRef:
        if schema_name not in self._SCHEMA_FILES:
            raise KeyError(
                f"Unknown schema name: {schema_name!r}. "
                f"Available: {', '.join(self.available_schema_names())}"
            )

        ver = version or self._default_version
        path = self._base_dir / ver / self._SCHEMA_FILES[schema_name]
        if not path.exists():
            raise FileNotFoundError(
                f"Schema file not found for {schema_name!r} at {path}"
            )
        return SchemaRef(name=schema_name, version=ver, path=path)

    def load_json(
        self,
        schema_name: str,
        version: Optional[str] = None,
        use_cache: bool = True,
    ) -> dict:
        ref = self.resolve(schema_name, version)
        cache_key = f"{ref.version}:{ref.name}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        with ref.path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if use_cache:
            self._cache[cache_key] = data
        return data

    def clear_cache(self) -> None:
        self._cache.clear()


# module-global singleton registry for convenience
REGISTRY = AionEquitiesSchemaRegistry()


def get_schema(schema_name: str, version: Optional[str] = None) -> dict:
    """Convenience helper."""
    return REGISTRY.load_json(schema_name, version=version)


def get_schema_path(schema_name: str, version: Optional[str] = None) -> Path:
    """Convenience helper."""
    return REGISTRY.resolve(schema_name, version=version).path