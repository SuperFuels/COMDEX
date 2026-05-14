# /workspaces/COMDEX/backend/modules/aion_trading/skills/skill_trading_update_decision_influence_weights.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from backend.modules.aion_skills.contracts import SkillRunRequest, SkillRunResult

# Sprint 3 governed writable influence runtime (preferred path)
from backend.modules.aion_learning.decision_influence_runtime import (
    get_decision_influence_runtime,
)

# Local deterministic fallback helpers (non-breaking, used if runtime API surface is incomplete)
from backend.modules.aion_trading.decision_influence_weights import (
    DEFAULT_WEIGHTS,
    default_weights_snapshot,
    apply_patch_dry_run,
)


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _canonical_action(value: Any) -> str:
    """
    Supported actions:
      - show   (read current snapshot)
      - update (validate/apply patch dry-run or governed write)
    Default is update for backward compatibility.
    """
    a = _safe_str(value, "update").lower()
    if a in {"show", "read", "get", "display"}:
        return "show"
    return "update"


def _normalize_patch(value: Any) -> Dict[str, Any]:
    """
    Normalize to patch dict with optional ops list.
    Tolerant by design to avoid breaking callers.
    """
    patch = _safe_dict(value)
    ops = patch.get("ops")
    if ops is None:
        patch["ops"] = []
        return patch
    if not isinstance(ops, list):
        patch["ops"] = []
    return patch


def _normalize_scope(value: Any) -> Dict[str, Any]:
    return _safe_dict(value)


def _default_snapshot_for_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic fallback snapshot if runtime doesn't expose a reader.
    """
    profile_id = _safe_str(scope.get("profile_id"), "default")
    environment = _safe_str(scope.get("environment"), "paper") or "paper"
    return default_weights_snapshot(
        profile_id=profile_id,
        environment=environment,
        version=1,
        updated_by="system",
        reason="fallback bootstrap defaults",
    )


def _extract_snapshot_hash(snapshot: Dict[str, Any]) -> Optional[str]:
    if not isinstance(snapshot, dict):
        return None
    h = snapshot.get("snapshot_hash")
    return str(h) if h else None


def _extract_weights(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    w = snapshot.get("weights")
    return dict(w) if isinstance(w, dict) else {}


def _diff_to_validated_diff_rows(diff_obj: Any) -> list[Dict[str, Any]]:
    """
    Convert DecisionInfluenceDiff (or compatible dict) into stable validated_diff rows:
      [{key, op?, old, new, delta, before_raw?, after_raw?}, ...]
    """
    if diff_obj is None:
        return []

    changed = None
    if isinstance(diff_obj, dict):
        changed = diff_obj.get("changed")
    elif hasattr(diff_obj, "changed"):
        changed = getattr(diff_obj, "changed")

    if not isinstance(changed, dict):
        return []

    rows: list[Dict[str, Any]] = []
    for key in sorted(changed.keys()):
        row = changed.get(key)
        if not isinstance(row, dict):
            continue
        before = row.get("before")
        after_norm = row.get("after_normalized", row.get("after"))
        after_raw = row.get("after_raw")
        try:
            old_val = float(before)
        except Exception:
            old_val = 0.0
        try:
            new_val = float(after_norm if after_norm is not None else after_raw)
        except Exception:
            new_val = old_val

        rr: Dict[str, Any] = {
            "key": str(key),
            "old": old_val,
            "new": new_val,
            "delta": float(new_val - old_val),
        }
        if after_raw is not None:
            try:
                rr["after_raw"] = float(after_raw)
            except Exception:
                rr["after_raw"] = after_raw
        rows.append(rr)
    return rows


def _build_show_output(
    *,
    snapshot: Dict[str, Any],
    dry_run: bool,
    scope: Dict[str, Any],
    source: str,
) -> Dict[str, Any]:
    """
    Stable skill output contract for read/show path.
    """
    return {
        "ok": True,
        "schema_version": "aion.trading.decision_influence_skill_result.v1",
        "action": "show",
        "dry_run": True if dry_run else True,  # show is always effectively dry-run/read-only
        "applied": False,
        "scope": scope,
        "weights": _extract_weights(snapshot),
        "validated_diff": [],
        "warnings": [],
        "snapshot_hash": _extract_snapshot_hash(snapshot),
        "previous_snapshot_hash": _extract_snapshot_hash(snapshot),
        "version": snapshot.get("version"),
        "proposed_patch": {},
        "source": source,
        "runtime_mode": "read_only",
    }


def _build_update_output_from_fallback(
    *,
    current_snapshot: Dict[str, Any],
    dry_run: bool,
    patch: Dict[str, Any],
    scope: Dict[str, Any],
    reason: str,
    source: str,
    updated_by: str,
) -> Dict[str, Any]:
    """
    Deterministic local fallback update path using aion_trading.decision_influence_weights.
    This gives the orchestrator the exact contract shape even when the governed runtime
    has not fully implemented read/update APIs yet.
    """
    vr, diff = apply_patch_dry_run(
        current_snapshot,
        patch=patch,
        reason=reason or "orchestrator decision influence update",
        updated_by=updated_by,
        increment_version=True,
    )

    validated_diff = _diff_to_validated_diff_rows(diff)
    warnings = []
    # diff warnings first, then validation warnings
    try:
        warnings.extend(list(getattr(diff, "warnings", []) or []))
    except Exception:
        pass
    try:
        warnings.extend(list(getattr(vr, "warnings", []) or []))
    except Exception:
        pass

    if not bool(getattr(vr, "ok", False)):
        return {
            "ok": False,
            "schema_version": "aion.trading.decision_influence_skill_result.v1",
            "action": "update",
            "dry_run": bool(dry_run),
            "applied": False,
            "scope": scope,
            "proposed_patch": patch,
            "validated_diff": validated_diff,
            "warnings": warnings,
            "errors": list(getattr(vr, "errors", []) or []),
            "snapshot_hash": _extract_snapshot_hash(current_snapshot),
            "previous_snapshot_hash": _extract_snapshot_hash(current_snapshot),
            "version": current_snapshot.get("version"),
            "source": source,
            "runtime_mode": "local_fallback_validation",
        }

    canonical_payload = dict(getattr(vr, "canonical_payload", {}) or {})
    next_snapshot_hash = getattr(vr, "snapshot_hash", None) or canonical_payload.get("snapshot_hash")

    out: Dict[str, Any] = {
        "ok": True,
        "schema_version": "aion.trading.decision_influence_skill_result.v1",
        "action": "update",
        "dry_run": bool(dry_run),
        "applied": False,  # fallback path is validation-only (no writes)
        "scope": scope,
        "proposed_patch": patch,
        "validated_diff": validated_diff,
        "warnings": warnings,
        "errors": [],
        "snapshot_hash": str(next_snapshot_hash) if next_snapshot_hash else None,
        "previous_snapshot_hash": _extract_snapshot_hash(current_snapshot),
        "version": canonical_payload.get("version", current_snapshot.get("version")),
        "source": source,
        "runtime_mode": "local_fallback_validation",
    }

    # For dry-run/debug visibility it is useful to return normalized next weights
    next_weights = _extract_weights(canonical_payload)
    if dry_run:
        out["weights"] = next_weights

    return out


def _normalize_runtime_output(
    *,
    raw: Any,
    action: str,
    dry_run: bool,
    patch: Dict[str, Any],
    scope: Dict[str, Any],
    source: str,
) -> Dict[str, Any]:
    """
    Normalize evolving runtime outputs into a stable contract.
    """
    if isinstance(raw, dict):
        out = dict(raw)
    elif hasattr(raw, "to_dict"):
        try:
            out = dict(raw.to_dict())
        except Exception:
            out = {"ok": True, "raw_type": type(raw).__name__}
    else:
        out = {"ok": True, "raw_type": type(raw).__name__}

    out.setdefault("schema_version", "aion.trading.decision_influence_skill_result.v1")
    out.setdefault("ok", bool(out.get("ok", True)))
    out.setdefault("action", action)
    out.setdefault("dry_run", bool(dry_run))
    out.setdefault("scope", scope)
    out.setdefault("proposed_patch", patch if action == "update" else {})
    out.setdefault("validated_diff", [])
    out.setdefault("warnings", [])
    out.setdefault("source", source)

    # applied default behavior
    if "applied" not in out:
        if action == "show":
            out["applied"] = False
        else:
            out["applied"] = False if dry_run else bool(out.get("ok", False))

    # show is always read-only
    if action == "show":
        out["dry_run"] = True
        out["applied"] = False

    return out


@dataclass
class TradingDecisionInfluenceSkill:
    """
    Sprint 3 governed write wrapper (paper-safe, dry-run-first) with stable output contract.

    Skill contract:
      skill_id = "skill.trading_update_decision_influence_weights"

    Inputs:
      action: str = "update"                     # "show" | "update" (aliases tolerated)
      dry_run: bool = True                       # default hard-safe
      patch: dict = {}                           # {"ops":[{"op":"set|delta","key":"...","value":...}]}
      reason: str = ""                           # audit note
      source: str = "conversation_orchestrator"  # caller/source tag
      scope: dict = {}                           # optional targeting (profile/env/etc)

    Stable output (both show and update):
      {
        "ok": bool,
        "schema_version": "aion.trading.decision_influence_skill_result.v1",
        "action": "show" | "update",
        "dry_run": bool,
        "applied": bool,
        "scope": {...},
        "proposed_patch": {...},         # {} on show
        "validated_diff": [...],         # [] on show
        "warnings": [...],
        "errors": [...],                 # optional/empty on success
        "snapshot_hash": str | None,
        "previous_snapshot_hash": str | None,
        "version": int | None,
        "weights": {...},                # present on show; optional on update dry-run
        "source": str,
      }
    """

    skill_id: str = "skill.trading_update_decision_influence_weights"

    def _try_runtime_show(self, runtime: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Preferred read path if runtime exposes one. Returns normalized dict or None if unsupported.
        """
        try:
            # Common candidate APIs
            if hasattr(runtime, "get_weights"):
                raw = runtime.get_weights(payload)
            elif hasattr(runtime, "read_weights"):
                raw = runtime.read_weights(payload)
            elif hasattr(runtime, "show_weights"):
                raw = runtime.show_weights(payload)
            elif hasattr(runtime, "get_snapshot"):
                raw = runtime.get_snapshot(payload)
            else:
                return None
            return _normalize_runtime_output(
                raw=raw,
                action="show",
                dry_run=True,
                patch={},
                scope=_safe_dict(payload.get("scope")),
                source=str(payload.get("source") or "conversation_orchestrator"),
            )
        except Exception:
            return None

    def _try_runtime_update(self, runtime: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Preferred governed update path if runtime exposes one. Returns normalized dict or None if unsupported.
        """
        try:
            if hasattr(runtime, "update_weights"):
                raw = runtime.update_weights(payload)
            elif hasattr(runtime, "apply_update"):
                raw = runtime.apply_update(payload)
            elif hasattr(runtime, "run_update"):
                raw = runtime.run_update(payload)
            else:
                return None
            return _normalize_runtime_output(
                raw=raw,
                action="update",
                dry_run=bool(payload.get("dry_run", True)),
                patch=_safe_dict(payload.get("patch")),
                scope=_safe_dict(payload.get("scope")),
                source=str(payload.get("source") or "conversation_orchestrator"),
            )
        except Exception as e:
            return {
                "ok": False,
                "schema_version": "aion.trading.decision_influence_skill_result.v1",
                "action": "update",
                "dry_run": bool(payload.get("dry_run", True)),
                "applied": False,
                "scope": _safe_dict(payload.get("scope")),
                "proposed_patch": _safe_dict(payload.get("patch")),
                "validated_diff": [],
                "warnings": [],
                "errors": ["decision_influence_runtime_exception"],
                "error": "decision_influence_runtime_exception",
                "message": str(e),
                "source": str(payload.get("source") or "conversation_orchestrator"),
            }

    def run(self, req: SkillRunRequest) -> SkillRunResult:
        req = req.validate()

        inputs = _safe_dict(req.inputs)
        metadata = _safe_dict(req.metadata)

        action = _canonical_action(inputs.get("action"))
        dry_run = _safe_bool(inputs.get("dry_run"), True)  # hard default = True
        patch = _normalize_patch(inputs.get("patch"))
        scope = _normalize_scope(inputs.get("scope"))

        reason = str(inputs.get("reason") or metadata.get("reason") or "").strip()
        source = str(inputs.get("source") or metadata.get("source") or "conversation_orchestrator").strip()
        updated_by = str(
            inputs.get("updated_by")
            or metadata.get("updated_by")
            or source
            or "conversation_orchestrator"
        ).strip()

        runtime = get_decision_influence_runtime()

        # Normalized request payload for runtime (forward-compatible)
        payload: Dict[str, Any] = {
            "action": action,
            "dry_run": dry_run,
            "patch": patch,
            "scope": scope,
            "reason": reason,
            "source": source,
            "session_id": str(req.session_id or ""),
            "turn_id": str(req.turn_id or ""),
            "skill_id": self.skill_id,
        }

        # ------------------------------------------------------------------
        # SHOW / READ PATH
        # ------------------------------------------------------------------
        if action == "show":
            # 1) Prefer governed runtime read path if available
            out = self._try_runtime_show(runtime, payload)
            if out is None:
                # 2) Deterministic fallback snapshot
                snapshot = _default_snapshot_for_scope(scope)
                out = _build_show_output(
                    snapshot=snapshot,
                    dry_run=True,
                    scope=scope,
                    source=source,
                )

            return SkillRunResult(
                ok=bool(out.get("ok", False)),
                skill_id=self.skill_id,
                output=out,
                metadata={
                    "phase": "phase_d_sprint3_governed_influence",
                    "source": source,
                    "dry_run": True,
                    "action": "show",
                },
            ).validate()

        # ------------------------------------------------------------------
        # UPDATE PATH (dry-run default, governed runtime preferred)
        # ------------------------------------------------------------------
        out = self._try_runtime_update(runtime, payload)

        if out is None:
            # Runtime missing update API -> local fallback validation path
            current_snapshot = _default_snapshot_for_scope(scope)
            out = _build_update_output_from_fallback(
                current_snapshot=current_snapshot,
                dry_run=dry_run,
                patch=patch,
                scope=scope,
                reason=reason,
                source=source,
                updated_by=updated_by,
            )
        else:
            # Ensure stable contract fields always present, even with runtime response variance
            out = _normalize_runtime_output(
                raw=out,
                action="update",
                dry_run=dry_run,
                patch=patch,
                scope=scope,
                source=source,
            )

        return SkillRunResult(
            ok=bool(out.get("ok", False)),
            skill_id=self.skill_id,
            output=out,
            metadata={
                "phase": "phase_d_sprint3_governed_influence",
                "source": source,
                "dry_run": bool(out.get("dry_run", dry_run)),
                "action": "update",
            },
        ).validate()