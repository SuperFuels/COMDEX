# /workspaces/COMDEX/backend/modules/aion_trading/decision_influence_weights.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import copy
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "aion.trading.decision_influence_weights.v1"


# Keep this explicit/locked. Add fields carefully and version when needed.
DEFAULT_WEIGHTS: Dict[str, float] = {
    # Price action / structure
    "market_structure": 0.20,
    "liquidity_sweep": 0.15,
    "displacement": 0.15,
    "fvg": 0.10,
    "order_block": 0.08,

    # Context / regime
    "session_timing": 0.10,
    "htf_bias_alignment": 0.10,
    "news_risk_filter": 0.05,

    # Execution / risk quality
    "rr_quality": 0.04,
    "spread_slippage_risk": 0.03,
}

# Allowed domains/ranges for raw weights before normalization.
# You can widen later, but keep strict now.
MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0

# Optional per-key clamps (lets you constrain unstable factors harder)
PER_KEY_LIMITS: Dict[str, Tuple[float, float]] = {
    "news_risk_filter": (0.0, 0.20),
    "spread_slippage_risk": (0.0, 0.15),
}

# Explicit allowed keys set for patch validation / parser integration
_ALLOWED_WEIGHT_KEYS = set(DEFAULT_WEIGHTS.keys())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round6(x: float) -> float:
    return round(float(x), 6)


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_snapshot_hash(weights_or_snapshot: Dict[str, Any]) -> str:
    """
    Stable hash helper for orchestrator/skill use.

    Accepts either:
      - raw weights dict: {"market_structure": 0.2, ...}
      - full snapshot dict: {"schema_version": ..., "weights": {...}, ...}

    Hash is always derived from a canonicalized *snapshot-like* payload.
    Returns sha256:<hex> to make the format explicit in traces.
    """
    data = dict(weights_or_snapshot or {})

    if "weights" in data and isinstance(data.get("weights"), dict):
        # Snapshot-like input: normalize by removing self-hash before hashing.
        payload = copy.deepcopy(data)
        payload.pop("snapshot_hash", None)
        digest = _sha256_hex(_canonical_json(payload))
        return f"sha256:{digest}"

    # Raw weights dict path (use canonicalized weights object wrapper)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "weights": {str(k): _round6(float(v)) for k, v in sorted(data.items())},
    }
    digest = _sha256_hex(_canonical_json(payload))
    return f"sha256:{digest}"


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        # fallback to defaults if a bad patch zeroes everything
        return copy.deepcopy(DEFAULT_WEIGHTS)
    out = {k: _round6(max(0.0, float(v)) / total) for k, v in weights.items()}

    # fix rounding drift so sum ~= 1 exactly by adjusting largest bucket
    drift = _round6(1.0 - sum(out.values()))
    if abs(drift) > 0:
        kmax = max(out, key=lambda k: out[k])
        out[kmax] = _round6(out[kmax] + drift)
    return out


def _apply_clamp(key: str, value: float) -> Tuple[float, Optional[str]]:
    lo, hi = PER_KEY_LIMITS.get(key, (MIN_WEIGHT, MAX_WEIGHT))
    clamped = min(max(float(value), lo), hi)
    if clamped != float(value):
        return clamped, f"clamped:{key}:{value}->{clamped}"
    return clamped, None


@dataclass
class DecisionInfluenceValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_weights: Dict[str, float] = field(default_factory=dict)
    snapshot_hash: Optional[str] = None
    canonical_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionInfluenceDiff:
    changed: Dict[str, Dict[str, float]] = field(default_factory=dict)
    sum_before: float = 0.0
    sum_after_raw: float = 0.0
    sum_after_normalized: float = 0.0
    warnings: List[str] = field(default_factory=list)


def default_weights_snapshot(
    *,
    profile_id: str = "default",
    environment: str = "paper",
    version: int = 1,
    updated_by: str = "system",
    reason: str = "bootstrap defaults",
) -> Dict[str, Any]:
    raw = copy.deepcopy(DEFAULT_WEIGHTS)
    normalized = _normalize_weights(raw)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "environment": environment,  # paper/live
        "version": int(version),
        "updated_at": _utc_now_iso(),
        "updated_by": updated_by,
        "reason": reason,
        "weights": normalized,
        "normalization": {
            "method": "sum_to_one",
            "target_sum": 1.0,
        },
    }
    # Keep historical format (hex only) for snapshot payload field
    payload["snapshot_hash"] = _sha256_hex(_canonical_json(payload))
    return payload


def validate_weights_snapshot(snapshot: Dict[str, Any]) -> DecisionInfluenceValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(snapshot, dict):
        return DecisionInfluenceValidationResult(ok=False, errors=["snapshot_not_dict"])

    if snapshot.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported_schema_version:{snapshot.get('schema_version')}")

    weights = snapshot.get("weights")
    if not isinstance(weights, dict) or not weights:
        errors.append("weights_missing_or_invalid")
        return DecisionInfluenceValidationResult(ok=False, errors=errors)

    allowed_keys = set(DEFAULT_WEIGHTS.keys())
    incoming_keys = set(weights.keys())

    unknown = sorted(incoming_keys - allowed_keys)
    missing = sorted(allowed_keys - incoming_keys)

    if unknown:
        errors.append(f"unknown_weight_keys:{','.join(unknown)}")
    if missing:
        errors.append(f"missing_weight_keys:{','.join(missing)}")

    if errors:
        return DecisionInfluenceValidationResult(ok=False, errors=errors)

    clamped_raw: Dict[str, float] = {}
    for k in sorted(weights.keys()):
        v = weights.get(k)
        try:
            fv = float(v)
        except Exception:
            errors.append(f"weight_not_numeric:{k}")
            continue
        clamped, warn = _apply_clamp(k, fv)
        clamped_raw[k] = clamped
        if warn:
            warnings.append(warn)

    if errors:
        return DecisionInfluenceValidationResult(ok=False, errors=errors, warnings=warnings)

    normalized = _normalize_weights(clamped_raw)

    canonical_payload = dict(snapshot)
    canonical_payload["weights"] = normalized
    canonical_payload["normalization"] = {"method": "sum_to_one", "target_sum": 1.0}
    canonical_payload.pop("snapshot_hash", None)
    snapshot_hash = _sha256_hex(_canonical_json(canonical_payload))
    canonical_payload["snapshot_hash"] = snapshot_hash

    return DecisionInfluenceValidationResult(
        ok=True,
        errors=[],
        warnings=warnings,
        normalized_weights=normalized,
        snapshot_hash=snapshot_hash,
        canonical_payload=canonical_payload,
    )


def apply_patch_dry_run(
    snapshot: Dict[str, Any],
    *,
    patch: Dict[str, Any],
    reason: str,
    updated_by: str,
    increment_version: bool = True,
) -> Tuple[DecisionInfluenceValidationResult, DecisionInfluenceDiff]:
    """
    Supported patch format (v1):
    {
      "ops": [
        {"op": "set", "key": "liquidity_sweep", "value": 0.20},
        {"op": "delta", "key": "liquidity_sweep", "value": 0.05},
      ]
    }
    """
    diff = DecisionInfluenceDiff()
    base = copy.deepcopy(snapshot if isinstance(snapshot, dict) else {})
    base_weights = dict(base.get("weights") or {})
    diff.sum_before = _round6(sum(float(v) for v in base_weights.values())) if base_weights else 0.0

    if not isinstance(patch, dict):
        return (
            DecisionInfluenceValidationResult(ok=False, errors=["patch_not_dict"]),
            diff,
        )

    ops = patch.get("ops")
    if not isinstance(ops, list) or not ops:
        return (
            DecisionInfluenceValidationResult(ok=False, errors=["patch_ops_missing_or_invalid"]),
            diff,
        )

    raw_after = dict(base_weights)
    errors: List[str] = []
    warnings: List[str] = []

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            errors.append(f"op_not_dict:{i}")
            continue

        kind = str(op.get("op") or "").strip().lower()
        key = str(op.get("key") or "").strip()

        if key not in DEFAULT_WEIGHTS:
            errors.append(f"unknown_weight_key:{key}")
            continue

        try:
            val = float(op.get("value"))
        except Exception:
            errors.append(f"op_value_not_numeric:{i}:{key}")
            continue

        before = float(raw_after.get(key, 0.0))
        if kind == "set":
            after = val
        elif kind == "delta":
            after = before + val
        else:
            errors.append(f"unsupported_op:{kind}")
            continue

        raw_after[key] = after
        diff.changed[key] = {"before": _round6(before), "after_raw": _round6(after)}

    if errors:
        return DecisionInfluenceValidationResult(ok=False, errors=errors, warnings=warnings), diff

    diff.sum_after_raw = _round6(sum(float(v) for v in raw_after.values()))

    candidate = copy.deepcopy(base)
    candidate["weights"] = raw_after
    candidate["updated_at"] = _utc_now_iso()
    candidate["updated_by"] = updated_by
    candidate["reason"] = reason
    if increment_version:
        try:
            candidate["version"] = int(base.get("version") or 0) + 1
        except Exception:
            candidate["version"] = 1

    vr = validate_weights_snapshot(candidate)
    diff.warnings.extend(vr.warnings)
    diff.sum_after_normalized = _round6(sum(vr.normalized_weights.values())) if vr.normalized_weights else 0.0

    if vr.ok:
        for k, ch in list(diff.changed.items()):
            ch["after_normalized"] = _round6(vr.normalized_weights.get(k, 0.0))
            # also expose normalized delta for skill/orchestrator display
            ch["delta_normalized"] = _round6(ch["after_normalized"] - ch["before"])

    return vr, diff


# ---------------------------------------------------------------------
# Orchestrator/skill-facing helpers (Sprint 3 Phase A/B groundwork)
# ---------------------------------------------------------------------

def _diff_to_validated_diff_rows(diff: DecisionInfluenceDiff) -> List[Dict[str, Any]]:
    """
    Convert internal DecisionInfluenceDiff.changed dict into stable list rows for
    skill outputs / UI traces.
    """
    rows: List[Dict[str, Any]] = []
    for key in sorted(diff.changed.keys()):
        ch = dict(diff.changed.get(key) or {})
        before = _round6(float(ch.get("before", 0.0)))
        after_raw = _round6(float(ch.get("after_raw", before)))
        after_normalized = _round6(float(ch.get("after_normalized", after_raw)))
        rows.append(
            {
                "key": key,
                "op": "set_or_delta",  # exact op is in proposed patch; diff is normalized result view
                "old": before,
                "new_raw": after_raw,
                "new": after_normalized,
                "delta": _round6(after_normalized - before),
                "delta_raw": _round6(after_raw - before),
            }
        )
    return rows


def build_validated_diff_from_patch(
    snapshot: Dict[str, Any],
    *,
    patch: Dict[str, Any],
    reason: str = "decision influence patch evaluation",
    updated_by: str = "system",
) -> Tuple[bool, List[Dict[str, Any]], List[str], Optional[Dict[str, Any]]]:
    """
    Convenience wrapper for skills:
      returns (ok, validated_diff, warnings, next_snapshot_or_none)
    """
    vr, diff = apply_patch_dry_run(
        snapshot,
        patch=patch,
        reason=reason,
        updated_by=updated_by,
        increment_version=True,
    )

    warnings = list(diff.warnings or [])
    warnings.extend(list(vr.warnings or []))

    # dedupe preserve order
    dedup_warnings: List[str] = []
    for w in warnings:
        if w not in dedup_warnings:
            dedup_warnings.append(w)

    if not vr.ok:
        # include errors in warnings list for skill display if caller wants a single list
        for e in vr.errors:
            msg = f"error:{e}"
            if msg not in dedup_warnings:
                dedup_warnings.append(msg)
        return False, [], dedup_warnings, None

    next_snapshot = dict(vr.canonical_payload or {})
    validated_diff = _diff_to_validated_diff_rows(diff)
    return True, validated_diff, dedup_warnings, next_snapshot


def evaluate_patch_against_snapshot(
    snapshot: Dict[str, Any],
    *,
    patch: Dict[str, Any],
    dry_run: bool = True,
    reason: str = "User-requested decision influence update.",
    updated_by: str = "conversation_orchestrator",
    action: str = "update",
) -> Dict[str, Any]:
    """
    Skill-friendly result shape (show/update) without performing persistent writes.

    This gives your governed skill a clean, stable contract now, while Phase B
    persistence/governance writes are added later.
    """
    current_snapshot = copy.deepcopy(snapshot if isinstance(snapshot, dict) else {})
    if not current_snapshot:
        current_snapshot = default_weights_snapshot(updated_by=updated_by, reason="auto-bootstrap default snapshot")

    # validate current snapshot first (self-healing fallback to defaults if invalid)
    current_vr = validate_weights_snapshot(current_snapshot)
    warnings: List[str] = []
    if not current_vr.ok:
        warnings.append("current_snapshot_invalid_fallback_to_defaults")
        current_snapshot = default_weights_snapshot(updated_by=updated_by, reason="fallback after invalid snapshot")
        current_vr = validate_weights_snapshot(current_snapshot)

    current_weights = dict((current_vr.canonical_payload or current_snapshot).get("weights") or {})
    current_hash = _stable_snapshot_hash(current_vr.canonical_payload or current_snapshot)

    # SHOW action
    if str(action or "update").strip().lower() == "show":
        return {
            "ok": True,
            "action": "show",
            "dry_run": True,
            "applied": False,
            "weights": current_weights,
            "proposed_patch": {"ops": []},
            "validated_diff": [],
            "warnings": warnings,
            "snapshot_hash": current_hash,
            "previous_snapshot_hash": current_hash,
            "version": int((current_vr.canonical_payload or current_snapshot).get("version") or 1),
        }

    # UPDATE action (still dry-run unless caller later persists)
    ok, validated_diff, patch_warnings, next_snapshot = build_validated_diff_from_patch(
        current_vr.canonical_payload or current_snapshot,
        patch=dict(patch or {}),
        reason=reason,
        updated_by=updated_by,
    )

    warnings.extend(patch_warnings)

    if not ok or not isinstance(next_snapshot, dict):
        return {
            "ok": False,
            "action": "update",
            "dry_run": bool(dry_run),
            "applied": False,
            "weights": current_weights if bool(dry_run) else None,
            "proposed_patch": dict(patch or {}),
            "validated_diff": [],
            "warnings": warnings,
            "snapshot_hash": current_hash,
            "previous_snapshot_hash": current_hash,
            "version": int((current_vr.canonical_payload or current_snapshot).get("version") or 1),
        }

    next_hash = _stable_snapshot_hash(next_snapshot)
    next_weights = dict(next_snapshot.get("weights") or {})

    applied = False
    version: Optional[int] = None

    # Phase B will replace this with real governed write + versioned storage.
    # For now we expose the exact contract and keep dry-run safe by default.
    if not bool(dry_run):
        warnings.append("apply_live_not_enabled_in_this_runtime")
        applied = False
        version = None

    return {
        "ok": True,
        "action": "update",
        "dry_run": bool(dry_run),
        "applied": applied,
        "weights": next_weights if bool(dry_run) else None,
        "proposed_patch": dict(patch or {}),
        "validated_diff": validated_diff,
        "warnings": warnings,
        "snapshot_hash": next_hash,
        "previous_snapshot_hash": current_hash,
        "version": version,
    }


# ---------------------------------------------------------------------
# Current snapshot loading (Phase B persistence hook point)
# ---------------------------------------------------------------------

def load_current_weights_snapshot(
    *,
    profile_id: str = "default",
    environment: str = "paper",
) -> Dict[str, Any]:
    """
    Current safe loader stub.

    Today: returns defaults (paper-first, non-breaking).
    Phase B: replace with versioned JSON storage lookup.
    """
    return default_weights_snapshot(
        profile_id=profile_id,
        environment=environment,
        version=1,
        updated_by="system",
        reason="load current snapshot (default stub)",
    )