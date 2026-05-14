from __future__ import annotations

from typing import Any, Dict, List, Optional
import hashlib

from .stable_json import stable_stringify


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _trace_events_of_kinds(trace: Any, *, kinds: List[str]) -> List[Dict[str, Any]]:
    if not isinstance(trace, list):
        return []
    out: List[Dict[str, Any]] = []
    for ev in trace:
        if isinstance(ev, dict) and str(ev.get("trace_kind") or "") in kinds:
            out.append(ev)
    return out


def _trace_events_with_kind_prefix(trace: Any, *, prefix: str) -> List[Dict[str, Any]]:
    if not isinstance(trace, list):
        return []
    out: List[Dict[str, Any]] = []
    for ev in trace:
        if not isinstance(ev, dict):
            continue
        tk = str(ev.get("trace_kind") or "")
        if tk.startswith(prefix):
            out.append(ev)
    return out


def _count_trace_kind(trace: Any, kind: str) -> int:
    if not isinstance(trace, list):
        return 0
    return sum(1 for ev in trace if isinstance(ev, dict) and ev.get("trace_kind") == kind)


def _first_str_in_trace(trace: Any, *, kind: str, keys: List[str]) -> str:
    """
    Best-effort helper to extract a string anchor from the first matching trace record.
    """
    if not isinstance(trace, list):
        return ""
    for ev in trace:
        if not isinstance(ev, dict):
            continue
        if ev.get("trace_kind") != kind:
            continue

        # flat keys
        for k in keys:
            v = ev.get(k)
            if isinstance(v, str) and v:
                return v

        # nested plan/result objects
        plan = ev.get("plan")
        if isinstance(plan, dict):
            for k in keys:
                v = plan.get(k)
                if isinstance(v, str) and v:
                    return v

        res = ev.get("result")
        if isinstance(res, dict):
            for k in keys:
                v = res.get(k)
                if isinstance(v, str) and v:
                    return v
    return ""


def _first_int_in_trace(trace: Any, *, kind: str, keys: List[str]) -> int:
    """
    Best-effort helper to extract an int anchor from the first matching trace record.
    """
    if not isinstance(trace, list):
        return 0
    for ev in trace:
        if not isinstance(ev, dict):
            continue
        if ev.get("trace_kind") != kind:
            continue

        # flat keys
        for k in keys:
            v = ev.get(k)
            if isinstance(v, int):
                return int(v)

        # nested result object
        res = ev.get("result")
        if isinstance(res, dict):
            for k in keys:
                v = res.get(k)
                if isinstance(v, int):
                    return int(v)

            # last-resort derived count (if result contains kg_writes list)
            kg_writes = res.get("kg_writes")
            if isinstance(kg_writes, list):
                return int(len(kg_writes))
    return 0


def make_replay_bundle(
    *,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    trace: Any,
    git_rev: str,
    run_id: str,
    ledger: Optional[Dict[str, Any]] = None,  # ✅ NEW
) -> Dict[str, Any]:
    created_utc = str(config.get("created_utc", "0000-00-00T00:00:00Z"))

    # ---- SQI enablement + level (pipeline-friendly) ----
    sqi_cfg = config.get("sqi") or {}
    sqi_enabled = bool(config.get("export_sqi_bundle")) or bool(sqi_cfg.get("enabled"))
    sqi_level = str(sqi_cfg.get("level") or ("bundle" if bool(config.get("export_sqi_bundle")) else "off"))
    if not sqi_enabled:
        sqi_level = "off"
    if sqi_level not in ("off", "bundle", "fabric"):
        sqi_level = "bundle" if sqi_enabled else "off"

    # ---- SQI digest: only sqi_* trace records ----
    sqi_events = _trace_events_with_kind_prefix(trace, prefix="sqi_")
    sqi_digest = sha256_bytes(stable_stringify(sqi_events).encode("utf-8"))

    # ---- SQI fabric anchors ----
    sqi_plan_id = _first_str_in_trace(trace, kind="sqi_fabric_plan", keys=["plan_id"])

    # accept both legacy + pluralized key spellings
    sqi_kg_writes_count = _first_int_in_trace(
        trace,
        kind="sqi_fabric_result",
        keys=["kg_writes_count", "kg_write_count"],
    )
    sqi_kg_writes_path = _first_str_in_trace(
        trace,
        kind="sqi_fabric_result",
        keys=["kg_writes_path"],
    )

    # ---- LEDGER exports (provided by caller; path SHOULD be run-dir relative) ----
    ledger = ledger or {}
    ledger_enabled = bool(ledger.get("enabled"))
    ledger_path = str(ledger.get("ledger_path") or "")
    ledger_count = int(ledger.get("ledger_count") or 0)
    ledger_digest = str(ledger.get("ledger_digest") or "")

    if not ledger_enabled:
        ledger_path = ""
        ledger_count = 0
        ledger_digest = ""

    return {
        "schemaVersion": "GX1_REPLAY_BUNDLE_V0",
        "run_id": run_id,
        "git_rev": git_rev,
        "created_utc": created_utc,

        "dataset_id": str(config.get("dataset_id", "")),
        "dataset_sha256": str(config.get("dataset_sha256", "")),
        "preprocess_sha256": config.get("preprocess_sha256", None),

        "config": config,
        "metrics": metrics,
        "trace_digest": sha256_bytes(stable_stringify(trace).encode("utf-8")),

        "exports": {
            "sqi": {
                "enabled": bool(sqi_enabled),
                "level": sqi_level,
                "plan_id": str(sqi_plan_id),
                "sqi_digest": str(sqi_digest),

                # keep existing name (back-compat)
                "kg_write_count": int(sqi_kg_writes_count),

                # add plural alias + path for audits/tests
                "kg_writes_count": int(sqi_kg_writes_count),
                "kg_writes_path": str(sqi_kg_writes_path),

                "sqi_bundle_count_in_trace": int(_count_trace_kind(trace, "sqi_bundle")),
            },
            "ledger": {  # ✅ NEW
                "enabled": bool(ledger_enabled),
                "ledger_path": ledger_path,     # e.g. "LEDGER.jsonl"
                "ledger_count": int(ledger_count),
                "ledger_digest": ledger_digest,
            },
        },
    }