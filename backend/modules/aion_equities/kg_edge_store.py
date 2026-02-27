from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.builders import (
    build_kg_edge_payload,
    build_write_event_envelope,
)
from backend.modules.aion_equities.schema_validate import validate_payload


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


class KGEdgeStore:
    """
    File-backed runtime store for AION equities KG edge payloads.

    Layout:
      <base_dir>/
        kg_edges/
          edge_exposure_company_AHT.L-_sector_industrial_equipment_rental_2026-02-22T22-00-00Z.json
        kg_edge_history/
          edge_exposure_company_AHT.L-_sector_industrial_equipment_rental_2026-02-22T22-00-00Z/
            2026-02-22T22-00-00Z.json
            2026-03-01T09-15-00Z.json
        write_events/
          edge_exposure_company_AHT.L-_sector_industrial_equipment_rental_2026-02-22T22-00-00Z/
            interpretation/
              write_event_....json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.edges_dir = self.base_dir / "kg_edges"
        self.history_dir = self.base_dir / "kg_edge_history"
        self.write_events_dir = self.base_dir / "write_events"
        self.edges_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.write_events_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # path helpers
    # ------------------------------------------------------------------
    def _latest_path(self, edge_id: str) -> Path:
        return self.edges_dir / f"{_safe_segment(edge_id)}.json"

    def _history_entity_dir(self, edge_id: str) -> Path:
        return self.history_dir / _safe_segment(edge_id)

    def _history_path(self, edge_id: str, created_at: str) -> Path:
        return self._history_entity_dir(edge_id) / f"{_safe_segment(created_at)}.json"

    def _write_event_stage_dir(self, edge_id: str, stage: str) -> Path:
        return self.write_events_dir / _safe_segment(edge_id) / stage

    def _write_event_path(self, edge_id: str, stage: str, event_id: str) -> Path:
        return self._write_event_stage_dir(edge_id, stage) / f"{_safe_segment(event_id)}.json"

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
    def save_kg_edge(
        self,
        *,
        edge_id: str,
        src: str,
        dst: str,
        link_type: str,
        created_at: Any,
        confidence: float,
        active: bool,
        weight: Optional[float] = None,
        source_event_ids: Optional[List[str]] = None,
        source_hashes: Optional[List[str]] = None,
        generated_by: str = "aion_equities.kg_edge_store",
        create_write_event: bool = True,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_kg_edge_payload(
            edge_id=edge_id,
            src=src,
            dst=dst,
            link_type=link_type,
            created_at=created_at,
            confidence=confidence,
            active=active,
            weight=weight,
            source_event_ids=source_event_ids or [],
            source_hashes=source_hashes or [],
            generated_by=generated_by,
            validate=validate,
        )

        if validate:
            validate_payload("kg_edge", payload, version="v0_1")

        latest_path = self._latest_path(edge_id)
        history_path = self._history_path(edge_id, payload["created_at"])

        self._write_json(history_path, payload)
        self._write_json(latest_path, payload)

        if create_write_event:
            env = build_write_event_envelope(
                event_id=f"write_event/{edge_id}/interpretation/{payload['created_at']}",
                stage="interpretation",
                timestamp=payload["created_at"],
                entity_id=edge_id,
                entity_type="kg_edge",
                operation="upsert",
                payload_schema_id="kg_edge",
                payload_data=payload,
                source_kind="system",
                source_refs=source_event_ids or [src, dst],
                generated_by=generated_by,
                correlation_id=f"corr_{_safe_segment(edge_id)}",
                validate=validate,
            )
            self._write_json(
                self._write_event_path(edge_id, "interpretation", env["event_id"]),
                env,
            )

        return payload

    def update_kg_edge(
        self,
        *,
        edge_id: str,
        patch: Dict[str, Any],
        updated_at: Any,
        generated_by: str = "aion_equities.kg_edge_store",
        create_write_event: bool = True,
        validate: bool = True,
    ) -> Dict[str, Any]:
        current = self.load_latest_kg_edge(edge_id)
        updated = dict(current)
        updated.update(patch)

        # kg_edge schema supports updated_at, but created_at remains the identity timestamp
        if hasattr(updated_at, "astimezone"):
            updated_at_s = updated_at.astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            updated_at_s = str(updated_at)

        updated["updated_at"] = updated_at_s

        if not isinstance(updated.get("provenance"), dict):
            updated["provenance"] = {}
        updated["provenance"] = dict(updated["provenance"])
        updated["provenance"]["generated_by"] = generated_by

        if validate:
            validate_payload("kg_edge", updated, version="v0_1")

        history_path = self._history_path(edge_id, updated_at_s)
        latest_path = self._latest_path(edge_id)

        self._write_json(history_path, updated)
        self._write_json(latest_path, updated)

        if create_write_event:
            env = build_write_event_envelope(
                event_id=f"write_event/{edge_id}/interpretation/{updated_at_s}",
                stage="interpretation",
                timestamp=updated_at_s,
                entity_id=edge_id,
                entity_type="kg_edge",
                operation="update",
                payload_schema_id="kg_edge",
                payload_data=updated,
                source_kind="system",
                source_refs=updated.get("provenance", {}).get("source_event_ids", []) or [updated["src"], updated["dst"]],
                generated_by=generated_by,
                correlation_id=f"corr_{_safe_segment(edge_id)}",
                validate=validate,
            )
            self._write_json(
                self._write_event_path(edge_id, "interpretation", env["event_id"]),
                env,
            )

        return updated

    def load_latest_kg_edge(self, edge_id: str) -> Dict[str, Any]:
        path = self._latest_path(edge_id)
        if not path.exists():
            raise FileNotFoundError(f"No latest kg edge found for {edge_id}")
        return self._read_json(path)

    def load_kg_edge_at(self, edge_id: str, stamp: str) -> Dict[str, Any]:
        path = self._history_path(edge_id, stamp)
        if not path.exists():
            raise FileNotFoundError(f"No kg edge history entry found for {edge_id} at {stamp}")
        return self._read_json(path)

    def kg_edge_exists(self, edge_id: str) -> bool:
        return self._latest_path(edge_id).exists()

    def list_kg_edge_history(self, edge_id: str) -> List[str]:
        p = self._history_entity_dir(edge_id)
        if not p.exists():
            return []
        return sorted(x.stem for x in p.glob("*.json"))

    def load_write_events(self, edge_id: str, stage: str = "interpretation") -> List[Dict[str, Any]]:
        stage_dir = self._write_event_stage_dir(edge_id, stage)
        if not stage_dir.exists():
            return []
        return [self._read_json(p) for p in sorted(stage_dir.glob("*.json"))]

    def save_edge(self, **kwargs):
        """
        Compatibility wrapper for runtime callers.

        Accepts runtime-style calls like:
        save_edge(
            src=...,
            dst=...,
            link_type=...,
            created_at=...,
            confidence=...,
            active=...,
            payload={...},
        )

        and adapts them to the stricter save_kg_edge() signature.
        """
        import inspect
        import re
        from datetime import datetime, timezone

        def _iso_z(value):
            if isinstance(value, str):
                return value
            if isinstance(value, datetime):
                dt = value
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            raise ValueError(f"Unsupported datetime value: {value!r}")

        def _safe(value: str) -> str:
            return re.sub(r"[^A-Za-z0-9._:/-]+", "_", str(value))

        # Pull runtime payload aliases out first
        payload_value = None
        if "payload" in kwargs:
            payload_value = kwargs.pop("payload")
        if "edge_payload_patch" in kwargs:
            payload_value = kwargs.pop("edge_payload_patch")

        # Build edge_id if caller did not provide one
        if "edge_id" not in kwargs:
            src = kwargs.get("src")
            dst = kwargs.get("dst")
            link_type = kwargs.get("link_type", "edge")
            created_at = kwargs.get("created_at") or kwargs.get("updated_at")

            if src is None or dst is None or created_at is None:
                raise TypeError("save_edge requires src, dst, link_type, and created_at when edge_id is not provided")

            created_at_s = _iso_z(created_at)
            kwargs["edge_id"] = f"edge/{link_type}/{_safe(src)}->{_safe(dst)}/{created_at_s}"

        sig = inspect.signature(self.save_kg_edge)
        params = sig.parameters

        # Map payload only if the underlying method supports it
        if payload_value is not None:
            if "payload" in params:
                kwargs["payload"] = payload_value
            elif "edge_payload_patch" in params:
                kwargs["edge_payload_patch"] = payload_value
            elif "payload_patch" in params:
                kwargs["payload_patch"] = payload_value
            elif "metadata" in params:
                kwargs["metadata"] = payload_value
            elif "edge_metadata" in params:
                kwargs["edge_metadata"] = payload_value

        return self.save_kg_edge(**kwargs)