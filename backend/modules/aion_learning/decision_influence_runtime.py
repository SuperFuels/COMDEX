from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import math
import uuid

from backend.modules.aion_learning.contracts_decision_influence import (
    DecisionInfluenceUpdate,
)


SCHEMA_VERSION_WEIGHTS = "aion.trading.decision_influence_weights.v1"
SCHEMA_VERSION_AUDIT = "aion.trading.decision_influence_audit.v1"

# Adjust if you already have a preferred runtime path convention
DEFAULT_WEIGHTS_PATH = Path(".runtime/COMDEX_MOVE/data/trading/decision_influence_weights.json")
DEFAULT_AUDIT_JSONL_PATH = Path(".runtime/COMDEX_MOVE/data/trading/decision_influence_audit.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_finite_number(x: Any) -> bool:
    return _is_number(x) and math.isfinite(float(x))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent_dir(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent_dir(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


class DecisionInfluenceRuntime:
    """
    Governed writable decision influence runtime (Sprint 3 / Phase 3).

    Finalized runtime behavior:
    - Whitelist-only sections (contract validate() handles top-level schema intent)
    - Clamps numeric values by section
    - Structured non-breaking failures (no exceptions escape apply_update)
    - Dry-run support (no state mutation / no persistence)
    - Persistent weights document (versioned JSON)
    - Audit trail (JSONL append; non-fatal if audit write fails)
    """

    SECTION_CLAMPS = {
        "setup_confidence_weights": (0.0, 2.0),
        "pair_session_preferences": (0.0, 2.0),
        "stand_down_sensitivity": (0.5, 2.0),
        "llm_trust_weights": (0.0, 2.0),
        "event_caution_multipliers": (0.5, 3.0),
    }

    def __init__(
        self,
        *,
        weights_path: Path = DEFAULT_WEIGHTS_PATH,
        audit_jsonl_path: Path = DEFAULT_AUDIT_JSONL_PATH,
        autoload: bool = True,
    ) -> None:
        self._weights_path = Path(weights_path)
        self._audit_jsonl_path = Path(audit_jsonl_path)

        self._state: Dict[str, Dict[str, Any]] = self._empty_state()
        self._weights_version: int = 1
        self._updated_at: Optional[str] = None
        self._last_persist_error: Optional[str] = None

        # In-memory mirror for tests/debug convenience
        self._audit_log: List[Dict[str, Any]] = []

        if autoload:
            self._load_state_from_disk_nonfatal()

    # ---------------------------------------------------------------------
    # Public properties / helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _empty_state() -> Dict[str, Dict[str, Any]]:
        return {
            "setup_confidence_weights": {},
            "pair_session_preferences": {},
            "stand_down_sensitivity": {},
            "llm_trust_weights": {},
            "event_caution_multipliers": {},
        }

    @property
    def state(self) -> Dict[str, Dict[str, Any]]:
        return deepcopy(self._state)

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        return deepcopy(self._audit_log)

    @property
    def weights_version(self) -> int:
        return int(self._weights_version)

    @property
    def updated_at(self) -> Optional[str]:
        return self._updated_at

    @property
    def last_persist_error(self) -> Optional[str]:
        return self._last_persist_error

    def show_state(self) -> Dict[str, Any]:
        """
        Read-only structured snapshot for 'show' action routing.
        """
        return {
            "ok": True,
            "state": self.state,
            "meta": {
                "schema_version": SCHEMA_VERSION_WEIGHTS,
                "weights_version": self.weights_version,
                "updated_at": self.updated_at,
                "weights_path": str(self._weights_path),
                "audit_jsonl_path": str(self._audit_jsonl_path),
                "last_persist_error": self.last_persist_error,
            },
        }

    # ---------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------

    def _weights_doc(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_WEIGHTS,
            "version": int(self._weights_version),
            "updated_at": self._updated_at,
            "state": deepcopy(self._state),
        }

    def _load_state_from_disk_nonfatal(self) -> None:
        try:
            if not self._weights_path.exists():
                return

            raw = json.loads(self._weights_path.read_text(encoding="utf-8"))
            state = raw.get("state")
            if not isinstance(state, dict):
                self._last_persist_error = "weights file missing/invalid 'state' object"
                return

            clean_state = self._empty_state()
            # Only allow known sections
            for section in self.SECTION_CLAMPS.keys():
                section_payload = state.get(section, {})
                if not isinstance(section_payload, dict):
                    continue
                # Normalize & clamp leaf values recursively
                normalized, _rejected = self._normalize_section_payload(section, section_payload)
                clean_state[section] = normalized

            self._state = clean_state
            self._weights_version = int(raw.get("version") or 1)
            self._updated_at = raw.get("updated_at")
            self._last_persist_error = None
        except Exception as e:
            # Non-fatal: keep empty/default in-memory state
            self._last_persist_error = f"load_failed: {e}"

    def _persist_state(self) -> None:
        doc = self._weights_doc()
        _atomic_json_write(self._weights_path, doc)
        self._last_persist_error = None

    def _append_audit_nonfatal(self, audit_entry: Dict[str, Any]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION_AUDIT,
            "audit_id": str(uuid.uuid4()),
            **deepcopy(audit_entry),
        }
        try:
            _append_jsonl(self._audit_jsonl_path, payload)
        except Exception as e:
            # Keep runtime non-breaking; record in memory and surface via metadata if needed
            payload["audit_write_error"] = str(e)
        finally:
            self._audit_log.append(deepcopy(payload))

    # ---------------------------------------------------------------------
    # Main update API
    # ---------------------------------------------------------------------

    def apply_update(
        self,
        update: DecisionInfluenceUpdate,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Returns structured result:
        {
          "ok": bool,
          "applied": {...},
          "rejected": [...],
          "audit_entry": {...},
          "error": {...} | None,
          "meta": {...}
        }
        """
        version_before = int(self._weights_version)

        try:
            update = update.validate()
            applied: Dict[str, Any] = {}
            rejected: List[Dict[str, Any]] = []

            # Work on a temp copy first (atomic-ish behavior)
            next_state = deepcopy(self._state)

            for section, payload in (update.updates or {}).items():
                # Defensive guard in case validate() evolves/changes
                if section not in self.SECTION_CLAMPS:
                    rejected.append(
                        {
                            "section": section,
                            "path": section,
                            "reason": "unknown/forbidden section",
                            "value": payload,
                        }
                    )
                    continue

                section_applied, section_rejected = self._apply_section(
                    section=section,
                    payload=payload,
                    state_bucket=next_state[section],
                )
                if section_applied:
                    applied[section] = section_applied
                rejected.extend(section_rejected)

            applied_count = self._count_leaf_values(applied)
            changed = applied_count > 0

            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "session_id": update.session_id,
                "turn_id": update.turn_id,
                "source": update.source,
                "reason": update.reason,
                "confidence": float(update.confidence),
                "dry_run": bool(dry_run),
                "applied_sections": sorted(list(applied.keys())),
                "applied_count": applied_count,
                "rejected_count": len(rejected),
                "rejected": deepcopy(rejected),
                "metadata": deepcopy(update.metadata or {}),
                "weights_version_before": version_before,
                "weights_version_after": version_before if dry_run else (version_before + (1 if changed else 0)),
                "changed": changed,
            }

            if not dry_run:
                # Commit in-memory first
                self._state = next_state

                # Bump version only if actual leaf changes were applied
                if changed:
                    self._weights_version += 1
                    self._updated_at = _utc_now_iso()

                # Persist weights (if this fails, return structured error and keep runtime usable)
                try:
                    self._persist_state()
                except Exception as e:
                    self._last_persist_error = str(e)
                    audit_entry["persist_error"] = str(e)
                    self._append_audit_nonfatal(audit_entry)
                    return {
                        "ok": False,
                        "applied": applied,
                        "rejected": rejected,
                        "audit_entry": audit_entry,
                        "error": {
                            "type": e.__class__.__name__,
                            "message": str(e),
                        },
                        "meta": {
                            "dry_run": False,
                            "changed": changed,
                            "weights_version_before": version_before,
                            "weights_version_after": int(self._weights_version),
                            "persisted": False,
                            "updated_at": self._updated_at,
                            "weights_path": str(self._weights_path),
                            "audit_jsonl_path": str(self._audit_jsonl_path),
                        },
                    }

            # Always audit (including dry-run)
            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": True,
                "applied": applied,
                "rejected": rejected,
                "audit_entry": audit_entry,
                "error": None,
                "meta": {
                    "dry_run": bool(dry_run),
                    "changed": changed,
                    "weights_version_before": version_before,
                    "weights_version_after": int(self._weights_version) if not dry_run else version_before,
                    "persisted": False if dry_run else True,
                    "updated_at": self._updated_at,
                    "weights_path": str(self._weights_path),
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                    "last_persist_error": self._last_persist_error,
                },
            }

        except Exception as e:  # non-breaking contract
            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "dry_run": bool(dry_run),
                "applied_sections": [],
                "applied_count": 0,
                "rejected_count": 0,
                "rejected": [],
                "runtime_error": str(e),
                "weights_version_before": version_before,
                "weights_version_after": version_before,
                "changed": False,
            }
            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": False,
                "applied": {},
                "rejected": [],
                "audit_entry": audit_entry,
                "error": {
                    "type": e.__class__.__name__,
                    "message": str(e),
                },
                "meta": {
                    "dry_run": bool(dry_run),
                    "changed": False,
                    "weights_version_before": version_before,
                    "weights_version_after": version_before,
                    "persisted": False,
                    "updated_at": self._updated_at,
                    "weights_path": str(self._weights_path),
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                    "last_persist_error": self._last_persist_error,
                },
            }

    # ---------------------------------------------------------------------
    # Internal apply / normalization
    # ---------------------------------------------------------------------

    def _apply_section(
        self,
        section: str,
        payload: Any,
        state_bucket: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Supports nested dicts. All leaf values must be numeric (first pass).
        Non-numeric leaves are rejected, not fatal.
        """
        if not isinstance(payload, dict):
            return {}, [
                {
                    "section": section,
                    "path": section,
                    "reason": "section payload must be a dict",
                    "value": payload,
                }
            ]

        lo, hi = self.SECTION_CLAMPS[section]
        applied: Dict[str, Any] = {}
        rejected: List[Dict[str, Any]] = []

        def walk_apply(
            src: Dict[str, Any],
            dst_state: Dict[str, Any],
            dst_applied: Dict[str, Any],
            path_parts: List[str],
        ) -> None:
            for k, v in src.items():
                cur_path_parts = [*path_parts, str(k)]
                cur_path = ".".join(cur_path_parts)

                if isinstance(v, dict):
                    dst_state.setdefault(k, {})
                    if not isinstance(dst_state[k], dict):
                        # If existing leaf clashes with dict shape, replace safely.
                        dst_state[k] = {}
                    dst_applied.setdefault(k, {})
                    walk_apply(v, dst_state[k], dst_applied[k], cur_path_parts)
                    # Clean empty nested applied dict
                    if dst_applied.get(k) == {}:
                        dst_applied.pop(k, None)
                    continue

                if not _is_finite_number(v):
                    rejected.append(
                        {
                            "section": section,
                            "path": cur_path,
                            "reason": "leaf value must be finite numeric",
                            "value": v,
                        }
                    )
                    continue

                clamped = _clamp(float(v), lo, hi)
                dst_state[k] = clamped
                dst_applied[k] = clamped

        walk_apply(payload, state_bucket, applied, [section])
        return applied, rejected

    def _normalize_section_payload(
        self,
        section: str,
        payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Used on load-from-disk to sanitize persisted state. Returns (normalized, rejected).
        """
        normalized: Dict[str, Any] = {}
        rejected: List[Dict[str, Any]] = []
        lo, hi = self.SECTION_CLAMPS[section]

        def walk(src: Dict[str, Any], dst: Dict[str, Any], path_parts: List[str]) -> None:
            for k, v in src.items():
                cur_path_parts = [*path_parts, str(k)]
                cur_path = ".".join(cur_path_parts)
                if isinstance(v, dict):
                    dst[k] = {}
                    walk(v, dst[k], cur_path_parts)
                    if dst[k] == {}:
                        dst.pop(k, None)
                    continue
                if not _is_finite_number(v):
                    rejected.append(
                        {
                            "section": section,
                            "path": cur_path,
                            "reason": "persisted leaf value invalid",
                            "value": v,
                        }
                    )
                    continue
                dst[k] = _clamp(float(v), lo, hi)

        walk(payload, normalized, [section])
        return normalized, rejected

    @staticmethod
    def _count_leaf_values(obj: Any) -> int:
        if isinstance(obj, dict):
            total = 0
            for v in obj.values():
                total += DecisionInfluenceRuntime._count_leaf_values(v)
            return total
        return 1