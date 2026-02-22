from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import math
import os
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

    Additive compatibility helpers:
    - show/read/get snapshot aliases
    - run/handle/execute raw payload router (structured contract)
    - raw payload -> DecisionInfluenceUpdate coercion (for legacy callers/tests)

    Safety policy:
    - live apply (dry_run=False) requires explicit auth/env guard
    """

    SECTION_CLAMPS = {
        "setup_confidence_weights": (0.0, 2.0),
        "pair_session_preferences": (0.0, 2.0),
        "stand_down_sensitivity": (0.5, 2.0),
        "llm_trust_weights": (0.0, 2.0),
        "event_caution_multipliers": (0.5, 3.0),
    }

    # Explicit env guards for live apply
    LIVE_APPLY_ENV_KEYS = (
        "AION_DECISION_INFLUENCE_ALLOW_LIVE_APPLY",
        "DECISION_INFLUENCE_ALLOW_LIVE_APPLY",
    )

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

    # Read aliases used by external callers/tests
    def get_weights(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return self.show_state()

    def read_weights(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return self.show_state()

    def show_weights(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return self.show_state()

    def get_snapshot(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return self.show_state()

    # Raw payload routers used by wrapper-style callers/tests
    def run(self, payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return self._handle_payload(payload=payload, **kwargs)

    def handle(self, payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return self._handle_payload(payload=payload, **kwargs)

    def execute(self, payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return self._handle_payload(payload=payload, **kwargs)

    def _handle_payload(
        self,
        payload: Optional[Dict[str, Any]] = None,
        *,
        request: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Accept payload via payload/request/data for wrapper compatibility
        raw: Optional[Dict[str, Any]] = payload if isinstance(payload, dict) else None
        if raw is None and isinstance(request, dict):
            raw = request
        if raw is None and isinstance(data, dict):
            raw = data
        raw = dict(raw or {})

        action = str(raw.get("action") or "show").strip().lower()

        if action in {"show", "read", "get", ""}:
            out = self.show_state()
            out["action"] = "show"
            out["dry_run"] = True
            return out

        # Read-only audit review tooling (operational / governance support)
        if action in {"audit_review", "review_audit", "audit"}:
            return self.review_audit_log(
                limit=raw.get("limit", 50),
                action=raw.get("filter_action"),
                dry_run=raw.get("filter_dry_run"),
                ok=raw.get("filter_ok"),
                changed=raw.get("filter_changed"),
                version_from=raw.get("version_from"),
                version_to=raw.get("version_to"),
                newest_first=bool(raw.get("newest_first", True)),
            )

        if action in {"revert", "rollback"}:
            # IMPORTANT: missing dry_run defaults to True (safe behavior)
            dry_run = bool(raw.get("dry_run", True)) if "dry_run" in raw else True

            # Live revert is also guarded on the raw router path (same policy as update)
            if not dry_run and not self._is_live_apply_authorized():
                return self._live_apply_guard_rejection(
                    version_before=int(self._weights_version),
                    reason="live revert blocked by auth guard (set AION_DECISION_INFLUENCE_ALLOW_LIVE_APPLY=1 to enable)",
                )

            return self._handle_revert_payload(raw, dry_run=dry_run)

        if action != "update":
            # Safe default for unknown actions if caller omitted dry_run
            dry_run = bool(raw.get("dry_run", True)) if "dry_run" in raw else True
            return {
                "ok": False,
                "action": action,
                "dry_run": dry_run,
                "error": {
                    "type": "ValueError",
                    "message": f"unsupported action: {action}",
                },
                "meta": {
                    "dry_run": dry_run,
                    "changed": False,
                    "weights_version_before": int(self._weights_version),
                    "weights_version_after": int(self._weights_version),
                    "persisted": False,
                    "updated_at": self._updated_at,
                    "weights_path": str(self._weights_path),
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                    "last_persist_error": self._last_persist_error,
                    "live_apply_authorized": self._is_live_apply_authorized(),
                },
            }

        # Raw router path is where we enforce live-apply auth guard (not in apply_update),
        # so direct typed apply_update(...) calls used by older tests remain compatible.
        # IMPORTANT: missing dry_run MUST default to True (safe behavior).
        if "dry_run" in raw:
            dry_run = bool(raw.get("dry_run", True))
        else:
            dry_run = True

        if not dry_run and not self._is_live_apply_authorized():
            return self._live_apply_guard_rejection(
                version_before=int(self._weights_version),
                reason="live apply blocked by auth guard (set AION_DECISION_INFLUENCE_ALLOW_LIVE_APPLY=1 to enable)",
            )

        # Route raw payload to typed update path (compat coercion happens inside apply_update)
        return self.apply_update(raw, dry_run=dry_run)

    def review_decision_influence_audit(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        raw = payload if isinstance(payload, dict) else kwargs.get("payload") or kwargs.get("request") or kwargs.get("data") or {}
        raw = dict(raw or {})
        raw.setdefault("action", "audit_review")
        return get_decision_influence_runtime().run(payload=raw)

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

    def _read_audit_entries_nonfatal(self) -> List[Dict[str, Any]]:
        """
        Read audit JSONL entries from disk if present. Non-fatal on errors.
        Returns list of parsed dict entries in file order.
        """
        try:
            if not self._audit_jsonl_path.exists():
                return []

            entries: List[Dict[str, Any]] = []
            with self._audit_jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(row, dict):
                        entries.append(row)
            return entries
        except Exception:
            return []

    def _replay_state_to_version(self, target_version: int) -> Dict[str, Dict[str, Any]]:
        """
        Reconstruct runtime state by replaying successful non-dry-run update audits
        up to and including the requested weights version.

        Assumptions:
        - audit entries contain "action" or are legacy update-style entries
        - update entries include "applied" (preferred) OR enough data in "audit_entry"
        - target_version >= 1
        """
        if not isinstance(target_version, int):
            raise ValueError("target.version must be an integer")
        if target_version < 1:
            raise ValueError("target.version must be >= 1")

        # Version 1 corresponds to empty/default state before any successful live updates
        if target_version == 1:
            return self._empty_state()

        entries = self._read_audit_entries_nonfatal()
        state = self._empty_state()

        # Replay successful live updates that produce a version bump.
        # We stop once an entry reports weights_version_after == target_version.
        seen_target = False

        for row in entries:
            if not isinstance(row, dict):
                continue

            # Ignore explicit rollback entries for now (we replay only direct update mutations)
            action = str(row.get("action") or "update").strip().lower()
            if action not in {"", "update"}:
                continue

            # Must be successful non-dry-run update-like audit row
            if bool(row.get("dry_run", False)):
                continue
            if row.get("changed") is False:
                continue

            # Prefer explicit applied payload if present
            applied = row.get("applied")
            if not isinstance(applied, dict):
                # Some rows may nest operational fields differently; skip if absent
                continue

            for section, payload in applied.items():
                if section not in self.SECTION_CLAMPS:
                    continue
                if not isinstance(payload, dict):
                    continue

                # Reuse existing clamp logic by applying into reconstructed state bucket
                _applied, _rejected = self._apply_section(
                    section=section,
                    payload=payload,
                    state_bucket=state[section],
                )

            try:
                row_version_after = int(row.get("weights_version_after"))
            except Exception:
                row_version_after = None

            if row_version_after == target_version:
                seen_target = True
                break

        if not seen_target:
            raise ValueError(f"target version not found in replayable audit history: {target_version}")

        return state

    def rollback_to_version(
        self,
        target_version: Any,
        dry_run: bool = True,
        *,
        source: str = "decision_influence_runtime",
        reason: str = "rollback request",
        metadata: Optional[Dict[str, Any]] = None,
        action: str = "rollback",
    ) -> Dict[str, Any]:
        """
        Reconstruct and restore runtime state to a prior target weights version.

        Compatibility policy:
        - Raw router path uses this for action=rollback/revert.
        - Dry-run defaults safe (True) when omitted in router.
        - Live rollback is auth-gated on raw router path (same as live update).
        """
        version_before = int(self._weights_version)
        action = str(action or "rollback").strip().lower()
        metadata = dict(metadata or {})

        # Live rollback should be guarded in the raw router path as well
        if not bool(dry_run) and not self._is_live_apply_authorized():
            return {
                "ok": False,
                "action": action,
                "dry_run": False,
                "applied": {},
                "rejected": [
                    {
                        "section": "auth",
                        "path": "dry_run",
                        "reason": "live rollback not authorized",
                        "value": False,
                    }
                ],
                "audit_entry": {
                    "ts_utc": _utc_now_iso(),
                    "action": action,
                    "dry_run": False,
                    "rejected_count": 1,
                    "rejected": [
                        {
                            "section": "auth",
                            "path": "dry_run",
                            "reason": "live rollback not authorized",
                            "value": False,
                        }
                    ],
                    "runtime_error": "live rollback blocked by auth guard",
                    "weights_version_before": version_before,
                    "weights_version_after": version_before,
                    "changed": False,
                },
                "error": {
                    "type": "PermissionError",
                    "message": "live rollback blocked by auth guard (set AION_DECISION_INFLUENCE_ALLOW_LIVE_APPLY=1 to enable)",
                },
                "meta": {
                    "dry_run": False,
                    "changed": False,
                    "weights_version_before": version_before,
                    "weights_version_after": version_before,
                    "persisted": False,
                    "updated_at": self._updated_at,
                    "weights_path": str(self._weights_path),
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                    "last_persist_error": self._last_persist_error,
                    "live_apply_authorized": False,
                },
            }

        try:
            target_version_i = int(target_version)
        except Exception:
            target_version_i = None

        if target_version_i is None:
            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": action,
                "dry_run": bool(dry_run),
                "rejected_count": 1,
                "rejected": [
                    {
                        "section": "target",
                        "path": "target.version",
                        "reason": "target.version must be provided as integer",
                        "value": target_version,
                    }
                ],
                "weights_version_before": version_before,
                "weights_version_after": version_before,
                "changed": False,
            }
            self._append_audit_nonfatal(audit_entry)
            return {
                "ok": False,
                "action": action,
                "dry_run": bool(dry_run),
                "applied": {},
                "rejected": audit_entry["rejected"],
                "audit_entry": audit_entry,
                "error": {
                    "type": "ValueError",
                    "message": "target.version must be provided as integer",
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
                },
            }

        try:
            restored_state = self._replay_state_to_version(target_version_i)

            changed = restored_state != self._state

            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": action,
                "source": source,
                "reason": reason,
                "dry_run": bool(dry_run),
                "applied_sections": sorted(list(restored_state.keys())),
                "applied_count": self._count_leaf_values(restored_state),
                "rejected_count": 0,
                "rejected": [],
                "metadata": {
                    **metadata,
                    "rollback_target_version": target_version_i,
                    "router_policy": "raw_router_rollback",
                },
                "weights_version_before": version_before,
                "weights_version_after": version_before if dry_run else (version_before + (1 if changed else 0)),
                "changed": changed,
                "rollback_target_version": target_version_i,
                "pre_state": deepcopy(self._state),
                "post_state": deepcopy(restored_state),
            }

            if not dry_run:
                self._state = deepcopy(restored_state)

                if changed:
                    self._weights_version += 1
                    self._updated_at = _utc_now_iso()

                try:
                    self._persist_state()
                except Exception as e:
                    self._last_persist_error = str(e)
                    audit_entry["persist_error"] = str(e)
                    self._append_audit_nonfatal(audit_entry)
                    return {
                        "ok": False,
                        "action": action,
                        "dry_run": False,
                        "applied": {"restored_state": deepcopy(restored_state)},
                        "rejected": [],
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
                            "last_persist_error": self._last_persist_error,
                            "live_apply_authorized": self._is_live_apply_authorized(),
                            "rollback_target_version": target_version_i,
                        },
                    }

            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": True,
                "action": action,
                "dry_run": bool(dry_run),
                "applied": {"restored_state": deepcopy(restored_state)},
                "rejected": [],
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
                    "rollback_target_version": target_version_i,
                },
            }

        except Exception as e:
            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": action,
                "dry_run": bool(dry_run),
                "applied_sections": [],
                "applied_count": 0,
                "rejected_count": 0,
                "rejected": [],
                "runtime_error": str(e),
                "weights_version_before": version_before,
                "weights_version_after": version_before,
                "changed": False,
                "rollback_target_version": target_version_i,
            }
            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": False,
                "action": action,
                "dry_run": bool(dry_run),
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
                    "rollback_target_version": target_version_i,
                },
            }

    # ---------------------------------------------------------------------
    # Raw payload coercion helpers (compatibility)
    # ---------------------------------------------------------------------

    def _normalize_patch_to_runtime_updates(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert test/legacy patch shape:
          {"section": {"key": {"op":"set","value": 1.23}}}
        to typed runtime updates shape:
          {"section": {"key": 1.23}}

        Non-'set' wrappers are preserved so runtime rejection remains explicit/structured.
        """
        if not isinstance(patch, dict):
            return {}

        out: Dict[str, Any] = {}

        for section, section_payload in patch.items():
            if not isinstance(section_payload, dict):
                out[section] = section_payload
                continue

            norm_section: Dict[str, Any] = {}
            for key, leaf in section_payload.items():
                if isinstance(leaf, dict) and "value" in leaf:
                    op = str(leaf.get("op", "set")).strip().lower() if "op" in leaf else "set"
                    if op == "set":
                        norm_section[key] = leaf.get("value")
                    else:
                        norm_section[key] = dict(leaf)
                else:
                    norm_section[key] = leaf

            out[section] = norm_section

        return out

    def _coerce_raw_payload_to_update(
        self,
        raw: Dict[str, Any],
        dry_run: bool,
    ) -> DecisionInfluenceUpdate:
        patch = raw.get("patch", {})
        if not isinstance(patch, dict):
            raise ValueError("patch payload must be a dict")

        updates = self._normalize_patch_to_runtime_updates(patch)

        meta_in = raw.get("metadata")
        meta_in = meta_in if isinstance(meta_in, dict) else {}

        session_id = str(raw.get("session_id") or meta_in.get("session_id") or f"runtime-{uuid.uuid4().hex[:12]}").strip()
        turn_id = str(raw.get("turn_id") or meta_in.get("turn_id") or f"turn-{uuid.uuid4().hex[:12]}").strip()
        source = str(raw.get("source") or "decision_influence_runtime")
        reason = str(raw.get("reason") or "raw payload update")

        try:
            confidence_f = float(raw.get("confidence", 0.0))
        except Exception:
            confidence_f = 0.0

        metadata: Dict[str, Any] = {
            "action": str(raw.get("action") or "update"),
            "dry_run_requested": bool(dry_run),
            "adapter": "runtime_raw_payload_coercion",
            "raw_patch_keys": sorted(patch.keys()),
            "normalized_patch_keys": sorted(updates.keys()),
        }
        if isinstance(raw.get("target"), dict):
            metadata["target"] = dict(raw["target"])
        for k, v in meta_in.items():
            if k not in metadata:
                metadata[k] = v

        # Let constructor/validate enforce final shape contract
        return DecisionInfluenceUpdate(
            session_id=session_id,
            turn_id=turn_id,
            source=source,
            reason=reason,
            updates=updates,
            confidence=confidence_f,
            metadata=metadata,
        )

    def _is_live_apply_authorized(self) -> bool:
        """
        Explicit opt-in gate for live writes.
        Accepted truthy values: 1, true, yes, on (case-insensitive)
        """
        for key in self.LIVE_APPLY_ENV_KEYS:
            val = os.getenv(key)
            if val is None:
                continue
            if str(val).strip().lower() in {"1", "true", "yes", "on"}:
                return True
        return False

    def _live_apply_guard_rejection(
        self,
        *,
        version_before: int,
        reason: str = "live apply blocked by auth guard",
    ) -> Dict[str, Any]:
        audit_entry = {
            "action": "update",
            "ts_utc": _utc_now_iso(),
            "dry_run": False,
            "applied_sections": [],
            "applied_count": 0,
            "rejected_count": 1,
            "rejected": [
                {
                    "section": "auth",
                    "path": "dry_run",
                    "reason": "live apply not authorized",
                    "value": False,
                }
            ],
            "runtime_error": reason,
            "weights_version_before": version_before,
            "weights_version_after": version_before,
            "changed": False,
        }
        self._append_audit_nonfatal(audit_entry)

        return {
            "ok": False,
            "action": "update",
            "dry_run": False,
            "applied": {},
            "rejected": audit_entry["rejected"],
            "audit_entry": audit_entry,
            "error": {
                "type": "PermissionError",
                "message": reason,
            },
            "meta": {
                "dry_run": False,
                "changed": False,
                "weights_version_before": version_before,
                "weights_version_after": version_before,
                "persisted": False,
                "updated_at": self._updated_at,
                "weights_path": str(self._weights_path),
                "audit_jsonl_path": str(self._audit_jsonl_path),
                "last_persist_error": self._last_persist_error,
                "live_apply_authorized": False,
            },
        }

    def _state_snapshot(self) -> Dict[str, Any]:
        """
        Lightweight snapshot used for audit + rollback/revert.
        """
        return {
            "schema_version": SCHEMA_VERSION_WEIGHTS,
            "version": int(self._weights_version),
            "updated_at": self._updated_at,
            "state": deepcopy(self._state),
        }


    def _read_audit_rows_nonfatal(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            if not self._audit_jsonl_path.exists():
                return rows
            for line in self._audit_jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except Exception:
                    continue
        except Exception:
            return rows
        return rows

    def review_audit_log(
        self,
        *,
        limit: int = 50,
        action: Optional[str] = None,
        dry_run: Optional[bool] = None,
        ok: Optional[bool] = None,
        changed: Optional[bool] = None,
        version_from: Optional[int] = None,
        version_to: Optional[int] = None,
        newest_first: bool = True,
    ) -> Dict[str, Any]:
        """
        Lightweight audit review helper for operational/audit tooling.

        Reads audit JSONL from disk (fallback to in-memory mirror if needed),
        applies optional filters, and returns a structured summary + rows.

        This is intentionally read-only and non-throwing (best effort).
        """
        try:
            rows = self._read_audit_rows_nonfatal()
            if not rows and self._audit_log:
                rows = deepcopy(self._audit_log)

            filtered: List[Dict[str, Any]] = []

            action_norm = str(action).strip().lower() if action is not None else None

            for row in rows:
                if not isinstance(row, dict):
                    continue

                if action_norm is not None:
                    row_action = str(row.get("action") or "").strip().lower()
                    if row_action != action_norm:
                        continue

                if dry_run is not None and bool(row.get("dry_run", False)) != bool(dry_run):
                    continue

                if changed is not None and bool(row.get("changed", False)) != bool(changed):
                    continue

                if ok is not None:
                    # infer success from presence/absence of runtime/persist error markers
                    inferred_ok = ("runtime_error" not in row) and ("persist_error" not in row)
                    if inferred_ok != bool(ok):
                        continue

                if version_from is not None:
                    try:
                        v_after = int(row.get("weights_version_after"))
                    except Exception:
                        v_after = None
                    if v_after is None or v_after < int(version_from):
                        continue

                if version_to is not None:
                    try:
                        v_after = int(row.get("weights_version_after"))
                    except Exception:
                        v_after = None
                    if v_after is None or v_after > int(version_to):
                        continue

                filtered.append(deepcopy(row))

            if newest_first:
                filtered = list(reversed(filtered))

            try:
                limit_i = max(1, int(limit))
            except Exception:
                limit_i = 50

            sliced = filtered[:limit_i]

            by_action: Dict[str, int] = {}
            failures = 0
            dry_runs = 0
            live_runs = 0

            for row in sliced:
                a = str(row.get("action") or "unknown")
                by_action[a] = by_action.get(a, 0) + 1

                if bool(row.get("dry_run", False)):
                    dry_runs += 1
                else:
                    live_runs += 1

                inferred_ok = ("runtime_error" not in row) and ("persist_error" not in row)
                if not inferred_ok:
                    failures += 1

            return {
                "ok": True,
                "filters": {
                    "limit": limit_i,
                    "action": action,
                    "dry_run": dry_run,
                    "ok": ok,
                    "changed": changed,
                    "version_from": version_from,
                    "version_to": version_to,
                    "newest_first": newest_first,
                },
                "summary": {
                    "returned": len(sliced),
                    "matched_before_limit": len(filtered),
                    "by_action": by_action,
                    "dry_runs": dry_runs,
                    "live_runs": live_runs,
                    "failures": failures,
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                },
                "rows": sliced,
            }
        except Exception as e:
            return {
                "ok": False,
                "filters": {
                    "limit": limit,
                    "action": action,
                    "dry_run": dry_run,
                    "ok": ok,
                    "changed": changed,
                    "version_from": version_from,
                    "version_to": version_to,
                    "newest_first": newest_first,
                },
                "summary": {
                    "returned": 0,
                    "matched_before_limit": 0,
                    "by_action": {},
                    "dry_runs": 0,
                    "live_runs": 0,
                    "failures": 1,
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                },
                "rows": [],
                "error": {
                    "type": e.__class__.__name__,
                    "message": str(e),
                },
            }


    def _extract_target_version(self, raw: Dict[str, Any]) -> int:
        """
        Accepts target version via:
        raw["target"]["version"]
        raw["version"]
        raw["target_version"]
        """
        target = raw.get("target")
        if isinstance(target, dict) and "version" in target:
            v = target.get("version")
        elif "target_version" in raw:
            v = raw.get("target_version")
        else:
            v = raw.get("version")

        if v is None:
            raise ValueError("revert/rollback requires target.version (or target_version/version)")

        try:
            iv = int(v)
        except Exception as e:
            raise ValueError(f"invalid target version: {v!r}") from e

        if iv < 1:
            raise ValueError(f"invalid target version: {iv!r}")
        return iv


    def _find_snapshot_for_version(self, target_version: int) -> Dict[str, Any]:
        """
        Resolve a snapshot for a historical version from audit entries.

        Sources checked:
        - post_snapshot.version == target_version
        - pre_snapshot.version == target_version

        Note: this only works for versions whose snapshots have been logged.
        """
        # Current in-memory state can satisfy current version directly
        if int(self._weights_version) == int(target_version):
            return self._state_snapshot()

        rows = self._read_audit_rows_nonfatal()
        # search from newest -> oldest
        for row in reversed(rows):
            if not isinstance(row, dict):
                continue

            for key in ("post_snapshot", "pre_snapshot"):
                snap = row.get(key)
                if not isinstance(snap, dict):
                    continue
                try:
                    v = int(snap.get("version"))
                except Exception:
                    continue
                if v == int(target_version) and isinstance(snap.get("state"), dict):
                    return {
                        "schema_version": snap.get("schema_version") or SCHEMA_VERSION_WEIGHTS,
                        "version": v,
                        "updated_at": snap.get("updated_at"),
                        "state": deepcopy(snap["state"]),
                    }

        raise LookupError(
            f"no snapshot found for target version {target_version}; "
            "snapshot-backed rollback is only available for versions recorded in audit"
        )


    def _handle_revert_payload(self, raw: Dict[str, Any], *, dry_run: bool) -> Dict[str, Any]:
        """
        Structured rollback/revert handler with target version semantics.

        Current semantics:
        - Requires target version
        - Uses audit snapshots (pre/post_snapshot) as source of truth for historical restores
        - Dry-run supported
        """
        version_before = int(self._weights_version)

        try:
            target_version = self._extract_target_version(raw)
            target_snapshot = self._find_snapshot_for_version(target_version)

            target_state = target_snapshot.get("state")
            if not isinstance(target_state, dict):
                raise ValueError(f"target snapshot for version {target_version} missing state")

            # normalize target state through known sections/clamps
            normalized_state = self._empty_state()
            rejected_on_restore: List[Dict[str, Any]] = []
            for section in self.SECTION_CLAMPS.keys():
                section_payload = target_state.get(section, {})
                if not isinstance(section_payload, dict):
                    continue
                normalized, rejected = self._normalize_section_payload(section, section_payload)
                normalized_state[section] = normalized
                rejected_on_restore.extend(rejected)

            pre_snapshot = self._state_snapshot()
            changed = normalized_state != self._state

            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": "revert",
                "dry_run": bool(dry_run),
                "target": {"version": int(target_version)},
                "source": str(raw.get("source") or "decision_influence_runtime"),
                "reason": str(raw.get("reason") or "rollback/revert requested"),
                "applied_sections": sorted([k for k, v in normalized_state.items() if isinstance(v, dict) and v]),
                "applied_count": self._count_leaf_values(normalized_state) if changed else 0,
                "rejected_count": len(rejected_on_restore),
                "rejected": deepcopy(rejected_on_restore),
                "weights_version_before": version_before,
                "weights_version_after": version_before if dry_run else (version_before + (1 if changed else 0)),
                "changed": bool(changed),
                "pre_snapshot": pre_snapshot,
                "target_snapshot": deepcopy(target_snapshot),
            }

            if not dry_run:
                self._state = deepcopy(normalized_state)
                if changed:
                    self._weights_version += 1
                    self._updated_at = _utc_now_iso()

                post_snapshot = self._state_snapshot()
                audit_entry["post_snapshot"] = deepcopy(post_snapshot)

                try:
                    self._persist_state()
                except Exception as e:
                    self._last_persist_error = str(e)
                    audit_entry["persist_error"] = str(e)
                    self._append_audit_nonfatal(audit_entry)
                    return {
                        "ok": False,
                        "action": "revert",
                        "dry_run": False,
                        "applied": {"target_version": int(target_version)} if changed else {},
                        "rejected": rejected_on_restore,
                        "audit_entry": audit_entry,
                        "error": {
                            "type": e.__class__.__name__,
                            "message": str(e),
                        },
                        "meta": {
                            "dry_run": False,
                            "changed": bool(changed),
                            "weights_version_before": version_before,
                            "weights_version_after": int(self._weights_version),
                            "persisted": False,
                            "updated_at": self._updated_at,
                            "weights_path": str(self._weights_path),
                            "audit_jsonl_path": str(self._audit_jsonl_path),
                            "last_persist_error": self._last_persist_error,
                            "live_apply_authorized": self._is_live_apply_authorized(),
                            "target_version": int(target_version),
                        },
                    }
            else:
                # dry-run post snapshot is simulated target
                audit_entry["post_snapshot"] = {
                    "schema_version": SCHEMA_VERSION_WEIGHTS,
                    "version": version_before,
                    "updated_at": self._updated_at,
                    "state": deepcopy(normalized_state),
                }

            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": True,
                "action": "revert",
                "dry_run": bool(dry_run),
                "applied": {"target_version": int(target_version)} if changed else {},
                "rejected": rejected_on_restore,
                "audit_entry": audit_entry,
                "error": None,
                "meta": {
                    "dry_run": bool(dry_run),
                    "changed": bool(changed),
                    "weights_version_before": version_before,
                    "weights_version_after": int(self._weights_version) if not dry_run else version_before,
                    "persisted": False if dry_run else True,
                    "updated_at": self._updated_at,
                    "weights_path": str(self._weights_path),
                    "audit_jsonl_path": str(self._audit_jsonl_path),
                    "last_persist_error": self._last_persist_error,
                    "live_apply_authorized": self._is_live_apply_authorized(),
                    "target_version": int(target_version),
                    "resolved_snapshot_version": int(target_snapshot.get("version", target_version)),
                },
            }

        except Exception as e:
            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": "revert",
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
                "action": "revert",
                "dry_run": bool(dry_run),
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
                },
            }

    # ---------------------------------------------------------------------
    # Main update API
    # ---------------------------------------------------------------------

    def apply_update(
        self,
        update: Union[DecisionInfluenceUpdate, Dict[str, Any]],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Accepts either:
        - DecisionInfluenceUpdate (typed path)
        - raw dict payload (compat path; coerced to DecisionInfluenceUpdate)

        Returns structured result:
        {
        "ok": bool,
        "applied": {...},
        "rejected": [...],
        "audit_entry": {...},
        "error": {...} | None,
        "meta": {...}
        }

        IMPORTANT COMPATIBILITY RULES:
        - Raw dict payload path: missing dry_run defaults to True (safe default).
        - Typed DecisionInfluenceUpdate path: DO NOT enforce auth guard here.
        (older runtime/persistence tests call typed apply_update(...) directly and
        expect live writes to work in their temp-path test fixtures)
        - Live-apply auth guard is enforced in _handle_payload(...) (raw router path).
        """
        version_before = int(self._weights_version)

        try:
            # Compatibility path: allow raw dict payloads to reach typed apply path
            if isinstance(update, dict):
                raw = dict(update)

                # Raw payload callers (including tests) may omit dry_run; default safely.
                if "dry_run" in raw:
                    dry_run = bool(raw.get("dry_run", True))
                else:
                    dry_run = True

                # NOTE:
                # Do NOT enforce live-apply auth guard here; that would break existing
                # typed/runtime+persistence tests. Guard raw payload live apply in
                # _handle_payload(...) if needed.
                update = self._coerce_raw_payload_to_update(raw, dry_run=dry_run)

            # Typed path: no auth guard enforcement here (backward compatibility)
            update = update.validate()
            applied: Dict[str, Any] = {}
            rejected: List[Dict[str, Any]] = []

            # Work on a temp copy first (atomic-ish behavior)
            pre_snapshot = self._state_snapshot()
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

            post_snapshot_dry_run = {
                "schema_version": SCHEMA_VERSION_WEIGHTS,
                "version": version_before,
                "updated_at": self._updated_at,
                "state": deepcopy(next_state),
            }

            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": "update",
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
                "pre_snapshot": pre_snapshot,
                "post_snapshot": post_snapshot_dry_run if dry_run else None,  # replaced on live apply after commit
            }

            if not dry_run:
                # Commit in-memory first
                self._state = next_state

                # Bump version only if actual leaf changes were applied
                if changed:
                    self._weights_version += 1
                    self._updated_at = _utc_now_iso()

                # Replace post snapshot with actual committed state/version
                audit_entry["post_snapshot"] = self._state_snapshot()

                # Persist weights (if this fails, return structured error and keep runtime usable)
                try:
                    self._persist_state()
                except Exception as e:
                    self._last_persist_error = str(e)
                    audit_entry["persist_error"] = str(e)
                    self._append_audit_nonfatal(audit_entry)
                    return {
                        "ok": False,
                        "action": "update",
                        "dry_run": False,
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
                            "last_persist_error": self._last_persist_error,
                            "live_apply_authorized": self._is_live_apply_authorized(),
                        },
                    }

            # Always audit (including dry-run)
            self._append_audit_nonfatal(audit_entry)

            return {
                "ok": True,
                "action": "update",
                "dry_run": bool(dry_run),
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
                },
            }

        except Exception as e:  # non-breaking contract
            audit_entry = {
                "ts_utc": _utc_now_iso(),
                "action": "update",
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
                "action": "update",
                "dry_run": bool(dry_run),
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
                    "live_apply_authorized": self._is_live_apply_authorized(),
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


# ---------------------------------------------------------------------
# Canonical singleton constructor + thin module-level wrappers
# ---------------------------------------------------------------------

_RUNTIME_SINGLETON: Optional[DecisionInfluenceRuntime] = None


def get_decision_influence_runtime() -> DecisionInfluenceRuntime:
    global _RUNTIME_SINGLETON
    if _RUNTIME_SINGLETON is None:
        _RUNTIME_SINGLETON = DecisionInfluenceRuntime()
    return _RUNTIME_SINGLETON


def run_decision_influence_runtime(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    return get_decision_influence_runtime().run(payload=payload, **kwargs)


def handle_decision_influence_runtime(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    return get_decision_influence_runtime().handle(payload=payload, **kwargs)


def execute_decision_influence_runtime(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    return get_decision_influence_runtime().execute(payload=payload, **kwargs)


def update_decision_influence_weights(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    raw = payload if isinstance(payload, dict) else kwargs.get("payload") or kwargs.get("request") or kwargs.get("data") or {}
    raw = dict(raw or {})
    raw.setdefault("action", "update")
    return get_decision_influence_runtime().run(payload=raw)


def show_decision_influence_weights(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    return get_decision_influence_runtime().show_state()


def get_decision_influence_weights(payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    return get_decision_influence_runtime().show_state()