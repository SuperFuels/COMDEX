from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.builders import (
    build_assessment_payload,
    build_write_event_envelope,
)
from backend.modules.aion_equities.schema_validate import validate_payload


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


class AssessmentStore:
    """
    File-backed runtime store for AION equities assessment payloads.

    Layout:
      <base_dir>/
        assessments/
          assessment_company_AHT.L_2026-02-22T22-00-00Z.json
        assessment_history/
          company_AHT.L/
            2026-02-22T22-00-00Z.json
        write_events/
          company_AHT.L/
            interpretation/
              write_event_....json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.assessments_dir = self.base_dir / "assessments"
        self.history_dir = self.base_dir / "assessment_history"
        self.write_events_dir = self.base_dir / "write_events"
        self.assessments_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.write_events_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # path helpers
    # ------------------------------------------------------------------
    def _latest_path(self, entity_id: str) -> Path:
        return self.assessments_dir / f"{_safe_segment(entity_id)}.json"

    def _history_entity_dir(self, entity_id: str) -> Path:
        return self.history_dir / _safe_segment(entity_id)

    def _history_path(self, entity_id: str, as_of: str) -> Path:
        return self._history_entity_dir(entity_id) / f"{_safe_segment(as_of)}.json"

    def _write_event_stage_dir(self, entity_id: str, stage: str) -> Path:
        return self.write_events_dir / _safe_segment(entity_id) / stage

    def _write_event_path(self, entity_id: str, stage: str, event_id: str) -> Path:
        return self._write_event_stage_dir(entity_id, stage) / f"{_safe_segment(event_id)}.json"

    def list_assessments(self, entity_id: str) -> List[str]:
        """
        Back-compat helper expected by tests.
        Returns assessment_ids from history for the given entity.
        """
        out: List[str] = []
        p = self._history_entity_dir(entity_id)
        if not p.exists():
            return out

        for fp in sorted(p.glob("*.json")):
            payload = self._read_json(fp)
            assessment_id = payload.get("assessment_id")
            if assessment_id:
                out.append(assessment_id)
        return out

    def load_assessment(self, entity_id: str, assessment_id: str) -> Dict[str, Any]:
        p = self._history_entity_dir(entity_id)
        if not p.exists():
            raise FileNotFoundError(f"No assessment history found for {entity_id}")

        for fp in sorted(p.glob("*.json")):
            payload = self._read_json(fp)
            if payload.get("assessment_id") == assessment_id:
                return payload

        raise FileNotFoundError(
            f"No assessment found for entity_id={entity_id!r} assessment_id={assessment_id!r}"
        )
        
    def load_assessment_by_id(self, assessment_id: str) -> Dict[str, Any]:
        for entity_dir in sorted(self.history_dir.glob("*")):
            if not entity_dir.is_dir():
                continue
            for fp in sorted(entity_dir.glob("*.json")):
                payload = self._read_json(fp)
                if payload.get("assessment_id") == assessment_id:
                    return payload

        raise FileNotFoundError(f"No assessment found for assessment_id={assessment_id!r}")
    # ------------------------------------------------------------------
    # io helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # public api
    # ------------------------------------------------------------------
    def save_assessment(
        self,
        *,
        entity_id: str,
        entity_type: str,
        as_of: Any,
        source_event_ids: Optional[List[str]] = None,
        source_hashes: Optional[List[str]] = None,
        risk_notes: str = "bootstrap",
        has_active_catalyst: bool = False,
        catalyst_count: int = 0,
        generated_by: str = "aion_equities.assessment_store",
        assessment_payload_patch: Optional[Dict[str, Any]] = None,
        create_write_event: bool = True,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Build, validate, and persist an assessment payload.

        `assessment_payload_patch` is a deep patch applied after builder defaults,
        allowing runtime/bootstrap code to override schema fields cleanly.
        """
        payload = build_assessment_payload(
            entity_id=entity_id,
            entity_type=entity_type,
            as_of=as_of,
            source_event_ids=source_event_ids or [f"{entity_id}/bootstrap"],
            source_hashes=source_hashes or [],
            risk_notes=risk_notes,
            has_active_catalyst=has_active_catalyst,
            catalyst_count=catalyst_count,
            generated_by=generated_by,
            validate=validate,
        )

        if assessment_payload_patch:
            payload = _deep_merge(payload, assessment_payload_patch)

        if validate:
            validate_payload("assessment", payload, version="v0_1")

        latest_path = self._latest_path(entity_id)
        history_path = self._history_path(entity_id, payload["as_of"])

        self._write_json(history_path, payload)
        self._write_json(latest_path, payload)

        if create_write_event:
            env = build_write_event_envelope(
                event_id=f"write_event/{entity_id}/interpretation/{payload['as_of']}",
                stage="interpretation",
                timestamp=payload["as_of"],
                entity_id=entity_id,
                entity_type=entity_type,
                operation="upsert",
                payload_schema_id="assessment",
                payload_data=payload,
                source_kind="system",
                source_refs=payload.get("provenance", {}).get("source_event_ids", [entity_id]),
                generated_by=generated_by,
                correlation_id=f"corr_{_safe_segment(entity_id)}",
                validate=validate,
            )
            self._write_json(
                self._write_event_path(entity_id, "interpretation", env["event_id"]),
                env,
            )

        return payload

    def load_latest_assessment(self, entity_id: str) -> Dict[str, Any]:
        path = self._latest_path(entity_id)
        if not path.exists():
            raise FileNotFoundError(f"No latest assessment found for {entity_id}")
        return self._read_json(path)

    def load_assessment_by_id(self, assessment_id: str) -> Dict[str, Any]:
        """
        assessment_id format:
          assessment/<entity-ish>/<timestamp-prefix...>

        We resolve from history/latest by scanning stored payloads.
        Good enough for bootstrap runtime.
        """
        # First try latest snapshots
        for p in sorted(self.assessments_dir.glob("*.json")):
            payload = self._read_json(p)
            if payload.get("assessment_id") == assessment_id:
                return payload

        # Then full history
        for p in sorted(self.history_dir.glob("**/*.json")):
            payload = self._read_json(p)
            if payload.get("assessment_id") == assessment_id:
                return payload

        raise FileNotFoundError(f"Assessment not found: {assessment_id}")

    def assessment_exists(self, entity_id: str, assessment_id: str | None = None) -> bool:
        if assessment_id is None:
            return self._latest_path(entity_id).exists()

        p = self._history_entity_dir(entity_id)
        if not p.exists():
            return False

        for fp in p.glob("*.json"):
            payload = self._read_json(fp)
            if payload.get("assessment_id") == assessment_id:
                return True
        return False

    def list_assessment_history(self, entity_id: str) -> List[str]:
        p = self._history_entity_dir(entity_id)
        if not p.exists():
            return []
        return sorted(x.stem for x in p.glob("*.json"))

    def load_write_events(self, entity_id: str, stage: str = "interpretation") -> List[Dict[str, Any]]:
        stage_dir = self._write_event_stage_dir(entity_id, stage)
        if not stage_dir.exists():
            return []
        return [self._read_json(p) for p in sorted(stage_dir.glob("*.json"))]