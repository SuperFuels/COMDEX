from __future__ import annotations
import json
import time
import uuid
from typing import Any, Dict, List, TYPE_CHECKING, Tuple
from pathlib import Path
from backend.modules.aion_trading.knowledge_runtime import get_forex_curriculum_v1
from backend.modules.aion_trading.strategy_registry import list_strategy_specs, get_strategy_spec
from backend.modules.aion_trading.dmip_runtime import run_dmip_checkpoint
from backend.modules.aion_trading.risk_rules import validate_trade_proposal
from backend.modules.aion_trading.contracts import TradeProposal

# ✅ Import contracts directly (safe)
from backend.modules.aion_skills.contracts import SkillSpec

# ✅ Type-only import to avoid circular import at runtime
if TYPE_CHECKING:
    from backend.modules.aion_skills.registry import SkillRegistry


# ---------------------------------------------------------------------
# Small safe coercion helpers
# ---------------------------------------------------------------------

def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _safe_float_or_none(value: Any) -> Any:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return value

# ---------------------------------------------------------------------
# Decision-influence capture / journal integration (P3O/P3P/P3Q)
# ---------------------------------------------------------------------

_DECISION_INFLUENCE_JOURNAL_PATH = Path(
    ".runtime/COMDEX_MOVE/data/trading/decision_influence_journal.jsonl"
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def _atomic_append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    """
    Simple append-safe JSONL write.
    If directory does not exist, create it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def _normalize_validated_diff_rows_for_capture(value: Any) -> List[Dict[str, Any]]:
    """
    Accept list-style or dict-style diff payloads and normalize to a list of rows.
    Keeps capture contract stable even if underlying diff shape evolves.
    """
    # Newer path: list[dict]
    if isinstance(value, list):
        rows: List[Dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                rows.append(dict(item))
        return rows

    # Older/alternate path: {"changed": {...}} or generic dict
    if isinstance(value, dict):
        changed = value.get("changed")
        if isinstance(changed, dict):
            rows = []
            for k in sorted(changed.keys()):
                ch = changed.get(k)
                if not isinstance(ch, dict):
                    continue
                rows.append(
                    {
                        "key": str(k),
                        "old": ch.get("before"),
                        "new": ch.get("after_normalized", ch.get("after")),
                        "after_raw": ch.get("after_raw"),
                        "delta": ch.get("delta"),
                    }
                )
            return rows
        # generic dict fallback: preserve as one object row for traceability
        return [dict(value)]

    return []


def _build_decision_influence_journal_artifacts(
    *,
    normalized_output: Dict[str, Any],
    requested_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build stable capture artifacts for decision influence weight show/update skill.
    Returns:
      {
        "trading_journal": [...],
        "journal_summary": {...},
        "trading_capture_result": {...}
      }

    Never raises; caller expects non-breaking behavior.
    """
    now_ts = time.time()
    req_inputs = _safe_dict(requested_inputs)
    out = _safe_dict(normalized_output)

    action = str(out.get("action") or "show").strip().lower()
    dry_run = _safe_bool(out.get("dry_run"), default=True)
    ok = _safe_bool(out.get("ok"), default=False)
    applied = _safe_bool(out.get("applied"), default=False)

    patch = _safe_dict(out.get("proposed_patch") or req_inputs.get("patch"))
    scope = _safe_dict(out.get("scope") or req_inputs.get("scope"))
    warnings = _safe_str_list(out.get("warnings"))
    validated_diff_rows = _normalize_validated_diff_rows_for_capture(out.get("validated_diff"))

    changed_keys: List[str] = []

    # 1) Preferred path: derive from validated diff rows
    for row in validated_diff_rows:
        k = row.get("key")
        if k is not None and str(k).strip():
            changed_keys.append(str(k).strip())

    # 2) Fallback: passthrough changed_keys from normalized/runtime output
    if not changed_keys:
        changed_keys.extend(
            [s for s in _safe_str_list(out.get("changed_keys")) if str(s).strip()]
        )

    # 3) Final fallback (dry-run safe): infer intent from patch ops
    #    This preserves useful journal summaries even if runtime omits diff rows.
    if not changed_keys:
        ops = patch.get("ops")
        if isinstance(ops, list):
            for op in ops:
                if not isinstance(op, dict):
                    continue
                k = op.get("key")
                if k is not None and str(k).strip():
                    changed_keys.append(str(k).strip())

    changed_keys = sorted(set(changed_keys))

    snapshot_hash = out.get("snapshot_hash")
    previous_snapshot_hash = out.get("previous_snapshot_hash")
    version = out.get("version")

    source = str(out.get("source") or req_inputs.get("source") or "skill_pack_adapter")
    reason = str(out.get("reason") or req_inputs.get("reason") or "").strip()

    event_id = f"diw_{uuid.uuid4().hex[:16]}"
    event_type = "decision_influence_weights_show" if action == "show" else "decision_influence_weights_update"

    journal_row: Dict[str, Any] = {
        "schema_version": "aion.trading_journal_entry.v1",
        "entry_id": event_id,
        "timestamp_unix": now_ts,
        "event_type": event_type,
        "ok": ok,
        "action": action,
        "dry_run": dry_run,
        "applied": applied,
        "source": source,
        "reason": reason,
        "scope": scope,
        "patch": patch if action == "update" else {},
        "validated_diff": validated_diff_rows,
        "changed_keys": changed_keys,
        "warnings": warnings,
        "snapshot_hash": str(snapshot_hash) if snapshot_hash is not None else None,
        "previous_snapshot_hash": str(previous_snapshot_hash) if previous_snapshot_hash is not None else None,
        "version": version,
        "metadata": {
            "skill_id": "skill.trading_update_decision_influence_weights",
            "capture_layer": "skill_pack_adapter",
        },
    }

    summary: Dict[str, Any] = {
        "event_type": event_type,
        "ok": ok,
        "action": action,
        "dry_run": dry_run,
        "applied": applied,
        "changed_count": len(changed_keys),
        "changed_keys": changed_keys,
        "warning_count": len(warnings),
        "version": version,
        "snapshot_hash": str(snapshot_hash) if snapshot_hash is not None else None,
        "previous_snapshot_hash": str(previous_snapshot_hash) if previous_snapshot_hash is not None else None,
    }

    capture_result: Dict[str, Any] = {
        "ok": False,  # set true only after append succeeds
        "capture_type": "decision_influence_journal_append",
        "non_blocking": True,
        "path": str(_DECISION_INFLUENCE_JOURNAL_PATH),
        "entry_id": event_id,
        "journal_summary": dict(summary),
        "error": None,
        "message": None,
    }

    try:
        _atomic_append_jsonl(_DECISION_INFLUENCE_JOURNAL_PATH, journal_row)
        capture_result["ok"] = True
    except Exception as e:
        # Non-breaking by design (P3P)
        capture_result["ok"] = False
        capture_result["error"] = "decision_influence_capture_append_failed"
        capture_result["message"] = str(e)

    return {
        "trading_journal": [journal_row],  # returned row for immediate audit/debug visibility
        "journal_summary": summary,
        "trading_capture_result": capture_result,
    }


def _attach_decision_influence_capture_artifacts(
    *,
    normalized_output: Dict[str, Any],
    requested_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fail-open wrapper. Never raises; returns enriched output.
    """
    out = dict(normalized_output or {})
    try:
        artifacts = _build_decision_influence_journal_artifacts(
            normalized_output=out,
            requested_inputs=requested_inputs,
        )
        out.update(artifacts)
        return out
    except Exception as e:
        # Absolute fallback: preserve primary skill success/failure and add capture failure metadata
        out["trading_capture_result"] = {
            "ok": False,
            "capture_type": "decision_influence_journal_append",
            "non_blocking": True,
            "error": "decision_influence_capture_wrapper_exception",
            "message": str(e),
        }
        out.setdefault("journal_summary", {
            "event_type": "decision_influence_weights_unknown",
            "ok": _safe_bool(out.get("ok"), default=False),
        })
        out.setdefault("trading_journal", [])
        return out
        
# ---------------------------------------------------------------------
# Decision-influence output normalization (drop-in contract shape)
# ---------------------------------------------------------------------

def _normalize_decision_influence_skill_output(
    raw: Any,
    *,
    requested_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize any underlying runtime/skill return into a stable dict contract for:
    skill.trading_update_decision_influence_weights

    Target contract (for both show and update):
      {
        "ok": bool,
        "skill_id": "skill.trading_update_decision_influence_weights",
        "schema_version": "aion.trading_decision_influence_update_result.v1",
        "action": "show" | "update",
        "dry_run": bool,
        "applied": bool,
        "proposed_patch": {...},
        "validated_diff": [...] | {...},
        "warnings": [...],
        "snapshot_hash": str|None,
        "weights": {...}|None,
        "version": int|str|None,
        "previous_snapshot_hash": str|None,
        ...
      }
    """
    req_inputs = _safe_dict(requested_inputs)
    out = raw.to_dict() if hasattr(raw, "to_dict") else raw
    d = _safe_dict(out)

    # If this is a SkillRunResult.to_dict() shape, the actual payload may be nested under output
    payload = _safe_dict(d.get("output")) if isinstance(d.get("output"), dict) else d

    # Preserve top-level ok if available (prefer explicit)
    ok_val = d.get("ok", payload.get("ok", True))
    ok = _safe_bool(ok_val, default=True)

    # Infer action
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"show", "update"}:
        # heuristic: if patch exists or update-like phrasing present, call it update, else show
        has_patch = bool(_safe_dict(payload.get("proposed_patch") or payload.get("patch")))
        requested_patch = bool(_safe_dict(req_inputs.get("patch")))
        action = "update" if (has_patch or requested_patch) else "show"

    # Dry-run/applied semantics
    requested_dry_run = _safe_bool(req_inputs.get("dry_run"), default=True)
    dry_run = _safe_bool(payload.get("dry_run", d.get("dry_run", requested_dry_run)), default=requested_dry_run)

    # applied=false for show and dry-runs unless explicitly true from runtime
    applied_default = False if (action == "show" or dry_run) else False
    applied = _safe_bool(payload.get("applied", d.get("applied", applied_default)), default=applied_default)

    # Patch + diff + warnings
    proposed_patch = _safe_dict(
        payload.get("proposed_patch")
        or payload.get("patch")
        or req_inputs.get("patch")
    )

    # validated_diff may be list[rows] (newer path) OR dict (older path)
    _validated_diff_raw = payload.get("validated_diff", payload.get("diff"))
    if isinstance(_validated_diff_raw, list):
        validated_diff = [dict(x) for x in _validated_diff_raw if isinstance(x, dict)]
    elif isinstance(_validated_diff_raw, dict):
        validated_diff = dict(_validated_diff_raw)
    else:
        # keep contract stable: list for new path, but empty dict also accepted by older schema.
        # choose [] so capture layer can compute changed_keys consistently.
        validated_diff = []

    warnings_raw = payload.get("warnings", d.get("warnings", []))
    warnings = [str(x) for x in _safe_list(warnings_raw)]

    # Snapshot identifiers
    snapshot_hash = payload.get("snapshot_hash", d.get("snapshot_hash"))
    if snapshot_hash is not None:
        snapshot_hash = str(snapshot_hash)

    previous_snapshot_hash = payload.get("previous_snapshot_hash", d.get("previous_snapshot_hash"))
    if previous_snapshot_hash is not None:
        previous_snapshot_hash = str(previous_snapshot_hash)

    # Optional useful fields
    version = payload.get("version", d.get("version"))
    weights = payload.get("weights", d.get("weights"))
    weights = _safe_dict(weights) if isinstance(weights, dict) else None

    # Optional passthroughs for richer UX/debug
    scope = _safe_dict(payload.get("scope") or req_inputs.get("scope"))
    reason = str(payload.get("reason") or req_inputs.get("reason") or "").strip()
    source = str(payload.get("source") or req_inputs.get("source") or "").strip()

    normalized: Dict[str, Any] = {
        "ok": ok,
        "skill_id": "skill.trading_update_decision_influence_weights",
        "schema_version": "aion.trading_decision_influence_update_result.v1",
        "action": action,
        "dry_run": dry_run,
        "applied": applied,
        "proposed_patch": proposed_patch,
        "validated_diff": validated_diff,
        "warnings": warnings,
        "snapshot_hash": snapshot_hash,
        "weights": weights,
        "version": version,
        "previous_snapshot_hash": previous_snapshot_hash,
    }

    # Include optional fields only when present/useful
    if scope:
        normalized["scope"] = scope
    if reason:
        normalized["reason"] = reason
    if source:
        normalized["source"] = source

    # Carry forward common error/message fields if present
    if "error" in payload or "error" in d:
        normalized["error"] = str(payload.get("error") or d.get("error"))
    if "message" in payload or "message" in d:
        normalized["message"] = str(payload.get("message") or d.get("message"))

    # If underlying result had extra trace fields, keep them without overwriting contract keys
    for extra_key in (
        "validation",
        "snapshot",
        "storage",
        "governance",
        "can_apply_live",
        "env_write_enabled",
        "rollback_pointer",
        "changed_keys",
    ):
        if extra_key in payload and extra_key not in normalized:
            normalized[extra_key] = payload.get(extra_key)

    return normalized


# ---------------------------------------------------------------------
# Trading skill handlers
# ---------------------------------------------------------------------

def skill_trading_get_curriculum(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return get_forex_curriculum_v1()


def skill_trading_list_strategies(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "aion.trading_strategy_list_result.v1",
        "strategies": list_strategy_specs(),
    }


def skill_trading_get_strategy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    tier = str((inputs or {}).get("strategy_tier") or "").strip()
    spec = get_strategy_spec(tier)
    if spec is None:
        return {"ok": False, "error": "strategy_not_found", "strategy_tier": tier}
    return {"ok": True, "strategy": spec.to_dict()}


def skill_trading_run_dmip_checkpoint(inputs: Dict[str, Any]) -> Dict[str, Any]:
    checkpoint = str((inputs or {}).get("checkpoint") or "pre_market")
    market_snapshot = dict((inputs or {}).get("market_snapshot") or {})
    llm_consultation = dict((inputs or {}).get("llm_consultation") or {})
    return run_dmip_checkpoint(
        checkpoint=checkpoint,
        market_snapshot=market_snapshot,
        llm_consultation=llm_consultation,
    )


def skill_trading_validate_risk(inputs: Dict[str, Any]) -> Dict[str, Any]:
    proposal = TradeProposal(
        pair=str((inputs or {}).get("pair") or ""),
        strategy_tier=str((inputs or {}).get("strategy_tier") or "tier3_smc_intraday"),
        direction=str((inputs or {}).get("direction") or "BUY"),
        account_mode=str((inputs or {}).get("account_mode") or "paper"),
        entry=(inputs or {}).get("entry"),
        stop_loss=(inputs or {}).get("stop_loss"),
        take_profit=(inputs or {}).get("take_profit"),
        account_equity=float((inputs or {}).get("account_equity") or 0.0),
        risk_pct=float((inputs or {}).get("risk_pct") or 0.0),
        pip_value=float((inputs or {}).get("pip_value") or 0.0),
        stop_pips=float((inputs or {}).get("stop_pips") or 0.0),
        size=(inputs or {}).get("size"),
        thesis=str((inputs or {}).get("thesis") or ""),
        setup_tags=list((inputs or {}).get("setup_tags") or []),
        metadata=dict((inputs or {}).get("metadata") or {}),
    ).validate()

    session_stats = dict((inputs or {}).get("session_stats") or {})
    account_stats = dict((inputs or {}).get("account_stats") or {})

    result = validate_trade_proposal(
        proposal,
        session_stats=session_stats,
        account_stats=account_stats,
    )
    return {
        "ok": bool(result.ok),
        "result": result.to_dict(),
        "proposal": proposal.to_dict(),
    }


def _load_decision_influence_skill_runner() -> Tuple[str, Any]:
    """
    Lazy-load the governed Phase D skill implementation without creating hard
    startup dependency/circular import issues.

    Supports either:
      - a function named `skill_trading_update_decision_influence_weights(req_or_inputs?)`
      - a class exposing `.run(req)` (common pattern in aion_trading/skills)
    """
    from backend.modules.aion_trading.skills import skill_trading_update_decision_influence_weights as mod

    # Function-style export (preferred simplest path)
    fn = getattr(mod, "skill_trading_update_decision_influence_weights", None)
    if callable(fn):
        return ("function", fn)

    # Class-style exports (try common names)
    for attr_name in (
        "SkillTradingUpdateDecisionInfluenceWeights",
        "TradingUpdateDecisionInfluenceWeightsSkill",
        "SkillTradingUpdateDecisionInfluenceWeightsRuntime",
    ):
        cls = getattr(mod, attr_name, None)
        if cls is not None:
            return ("class", cls)

    # Fallback: find any class with .run
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and callable(getattr(obj, "run", None)):
            return ("class", obj)

    raise ImportError(
        "Could not find decision influence trading skill callable/class in "
        "backend.modules.aion_trading.skills.skill_trading_update_decision_influence_weights"
    )


def skill_trading_update_decision_influence_weights(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter to expose the Phase D governed decision-influence writer as a normal
    dict-in/dict-out trading skill for the existing skill_pack registry.

    Non-breaking behavior:
      - If the underlying runtime returns SkillRunResult, convert to dict.
      - Normalize output to a stable contract shape for orchestrator/UI.
      - If import/runtime fails, return an error-shaped dict (no exception leak).
    """
    req_inputs = dict(inputs or {})
    try:
        mode, target = _load_decision_influence_skill_runner()

        # If the module exported a plain function, try direct dict call first.
        if mode == "function":
            try:
                out = target(req_inputs)
                normalized = _normalize_decision_influence_skill_output(out, requested_inputs=req_inputs)
                return _attach_decision_influence_capture_artifacts(
                    normalized_output=normalized,
                    requested_inputs=req_inputs,
                )
            except TypeError:
                # Might be a function expecting SkillRunRequest
                pass

        # Build SkillRunRequest for class-style or function(req)-style implementations
        from backend.modules.aion_skills.contracts import SkillRunRequest

        req = SkillRunRequest(
            skill_id="skill.trading_update_decision_influence_weights",
            inputs=req_inputs,
        ).validate()

        if mode == "class":
            runner = target()
            res = runner.run(req)
        else:
            # function exported but expects req object
            res = target(req)

        normalized = _normalize_decision_influence_skill_output(res, requested_inputs=req_inputs)
        return _attach_decision_influence_capture_artifacts(
            normalized_output=normalized,
            requested_inputs=req_inputs,
        )

    except Exception as e:
        # Keep registry/runtime startup non-breaking; surface structured error
        # in the SAME contract shape so orchestrator/UI parsing remains stable.
        dry_run = _safe_bool(req_inputs.get("dry_run"), default=True)

        error_out = {
            "ok": False,
            "skill_id": "skill.trading_update_decision_influence_weights",
            "schema_version": "aion.trading_decision_influence_update_result.v1",
            "action": "update" if _safe_dict(req_inputs.get("patch")) else "show",
            "dry_run": dry_run,
            "applied": False,
            "proposed_patch": _safe_dict(req_inputs.get("patch")),
            "validated_diff": {},
            "warnings": ["underlying_runtime_exception"],
            "snapshot_hash": None,
            "weights": None,
            "version": None,
            "previous_snapshot_hash": None,
            "error": "decision_influence_skill_runtime_error",
            "message": str(e),
            "source": str(req_inputs.get("source") or "skill_registry_adapter"),
        }
        return _attach_decision_influence_capture_artifacts(
            normalized_output=error_out,
            requested_inputs=req_inputs,
        )


def register_aion_trading_skills(registry: "SkillRegistry") -> "SkillRegistry":
    """
    Register AION trading skills as experimental, paper-first primitives.
    Runtime-safe import pattern (no circular import with aion_skills.registry).
    Idempotent registration: skips skills already present.
    """
    specs = [
        SkillSpec(
            skill_id="skill.trading_get_curriculum",
            name="Trading Curriculum (Forex v1)",
            description="Returns the AION forex trading knowledge curriculum and starting plan.",
            safety_class="read_only",  # legacy SkillSpec safety label; registry maps this
            status="experimental",
            timeout_ms=1500,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            retry_policy={"max_retries": 0},
            tags=["trading", "forex", "curriculum", "aion"],
            metadata={"module": "aion_trading", "paper_only": True},
        ).validate(),
        SkillSpec(
            skill_id="skill.trading_list_strategies",
            name="Trading Strategy Registry",
            description="Lists strategy tiers and specs for AION trading intelligence.",
            safety_class="read_only",
            status="experimental",
            timeout_ms=1500,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            retry_policy={"max_retries": 0},
            tags=["trading", "strategy", "registry", "aion"],
            metadata={"module": "aion_trading", "paper_only": True},
        ).validate(),
        SkillSpec(
            skill_id="skill.trading_get_strategy",
            name="Trading Strategy Spec",
            description="Gets a single strategy spec by tier.",
            safety_class="read_only",
            status="experimental",
            timeout_ms=1500,
            input_schema={
                "type": "object",
                "properties": {"strategy_tier": {"type": "string"}},
            },
            output_schema={"type": "object"},
            retry_policy={"max_retries": 0},
            tags=["trading", "strategy", "lookup", "aion"],
            metadata={"module": "aion_trading", "paper_only": True},
        ).validate(),
        SkillSpec(
            skill_id="skill.trading_run_dmip_checkpoint",
            name="DMIP Checkpoint (Read-only)",
            description="Runs a deterministic daily market intelligence checkpoint scaffold.",
            safety_class="internal_safe",  # transform but local-only scaffold
            status="experimental",
            timeout_ms=3000,
            input_schema={
                "type": "object",
                "properties": {
                    "checkpoint": {"type": "string"},
                    "market_snapshot": {"type": "object"},
                    "llm_consultation": {"type": "object"},
                },
            },
            output_schema={"type": "object"},
            retry_policy={"max_retries": 0},
            tags=["trading", "dmip", "intelligence", "aion"],
            metadata={"module": "aion_trading", "paper_only": True},
        ).validate(),
        SkillSpec(
            skill_id="skill.trading_validate_risk",
            name="Trading Risk Validation",
            description="Validates trade proposal against non-negotiable risk invariants (paper-first).",
            safety_class="internal_safe",
            status="experimental",
            timeout_ms=1500,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            retry_policy={"max_retries": 0},
            tags=["trading", "risk", "validation", "aion"],
            metadata={"module": "aion_trading", "paper_only": True},
        ).validate(),
        SkillSpec(
            skill_id="skill.trading_update_decision_influence_weights",
            name="Trading Decision Influence Weights (Governed)",
            description=(
                "Governed Phase D writer for decision influence weights "
                "(confidence/stand-down/session preferences/LLM trust), "
                "with hard safety boundaries and no risk invariant mutation."
            ),
            safety_class="internal_safe",
            status="experimental",
            timeout_ms=3000,
            input_schema={
                "type": "object",
                "properties": {
                    "dry_run": {"type": "boolean"},
                    "patch": {"type": "object"},
                    "scope": {"type": "object"},
                    "reason": {"type": "string"},
                    "source": {"type": "string"},
                },
                "additionalProperties": True,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "skill_id": {"type": "string"},
                    "schema_version": {"type": "string"},
                    "action": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                    "applied": {"type": "boolean"},
                    "proposed_patch": {"type": "object"},
                    "validated_diff": {"type": "object"},
                    "warnings": {"type": "array"},
                    "snapshot_hash": {"type": ["string", "null"]},
                    "weights": {"type": ["object", "null"]},
                    "version": {},
                    "previous_snapshot_hash": {"type": ["string", "null"]},
                },
                "required": [
                    "ok",
                    "skill_id",
                    "schema_version",
                    "action",
                    "dry_run",
                    "applied",
                    "proposed_patch",
                    "validated_diff",
                    "warnings",
                    "snapshot_hash",
                ],
                "additionalProperties": True,
            },
            retry_policy={"max_retries": 0},
            tags=["trading", "learning", "decision_influence", "phase_d", "governed", "aion"],
            metadata={
                "module": "aion_trading",
                "paper_only": True,
                "governed_write": True,
                "phase": "D",
            },
        ).validate(),
    ]

    handlers = {
        "skill.trading_get_curriculum": skill_trading_get_curriculum,
        "skill.trading_list_strategies": skill_trading_list_strategies,
        "skill.trading_get_strategy": skill_trading_get_strategy,
        "skill.trading_run_dmip_checkpoint": skill_trading_run_dmip_checkpoint,
        "skill.trading_validate_risk": skill_trading_validate_risk,
        "skill.trading_update_decision_influence_weights": skill_trading_update_decision_influence_weights,
    }

    for spec in specs:
        if not registry.has(spec.skill_id):
            registry.register(spec, handlers[spec.skill_id])

    return registry