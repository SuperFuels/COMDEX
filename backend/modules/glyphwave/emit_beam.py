import time
import logging
from typing import Optional, Dict, Any

from backend.modules.glyphwave.core.beam_logger import log_beam_prediction
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.qwave.qwave_writer import generate_qwave_id
from backend.modules.glyphvault.soul_law_validator import SoulLawValidator

logger = logging.getLogger(__name__)


def _ensure_metadata_context(wave_dict: Dict[str, Any], ctx_in: Dict[str, Any]) -> Dict[str, Any]:
    """
    SoulLawValidator extracts context from:
      (payload.metadata.context) OR (payload.meta.context) OR (payload.context)

    We always populate metadata.context (schema-safe) and ensure container_meta exists.
    """
    if not isinstance(wave_dict.get("metadata"), dict):
        wave_dict["metadata"] = {}

    meta = wave_dict["metadata"]
    if not isinstance(meta.get("context"), dict):
        meta["context"] = {}

    ctx = meta["context"]

    # Merge caller context in
    if isinstance(ctx_in, dict):
        ctx.update(ctx_in)

    # Ensure container_id is present in context (many upstream producers only set wave_dict.container_id)
    if "container_id" not in ctx and wave_dict.get("container_id"):
        ctx["container_id"] = wave_dict["container_id"]

    # Ensure container_meta exists if container_id exists (prevents invalid_container_metadata)
    cid = ctx.get("container_id")
    cm = ctx.get("container_meta")
    if cid and not isinstance(cm, dict):
        ctx["container_meta"] = {
            "id": cid,
            "kind": ctx.get("container_kind", "qqc"),
            "source": ctx.get("container_source", "qqc_kernel_boot"),
        }

    meta["context"] = ctx
    wave_dict["metadata"] = meta
    return wave_dict


def _hoist_dict_string_payload(wave_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Some adapters accidentally stuff a dict-as-string into glyph/program/codex/scroll.
    If that happens, hoist:
      - context -> metadata.context
      - logic_tree -> wave_dict.logic_tree
    """
    payload_str = (
        wave_dict.get("glyph")
        or wave_dict.get("program")
        or wave_dict.get("codex")
        or wave_dict.get("scroll")
        or ""
    )

    if isinstance(payload_str, str):
        s = payload_str.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                import ast

                obj = ast.literal_eval(s)
                if isinstance(obj, dict):
                    ctx = obj.get("context")
                    if isinstance(ctx, dict):
                        _ensure_metadata_context(wave_dict, ctx)

                    lt = obj.get("logic_tree")
                    if isinstance(lt, dict):
                        wave_dict.setdefault("logic_tree", lt)
            except Exception:
                pass

    return wave_dict


def _hoist_logic_tree_from_result(wave_dict: Dict[str, Any], result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    If the caller has a logic_tree in result, hoist it so QScore/Mutation hooks stop skipping.
    """
    if isinstance(result, dict) and isinstance(result.get("logic_tree"), dict):
        wave_dict.setdefault("logic_tree", result["logic_tree"])
    return wave_dict


def emit_qwave_beam(
    glyph_id: str,
    result: Optional[Dict[str, Any]] = None,
    source: str = "codex_executor",
    context: Optional[Dict[str, Any]] = None,
    state: Optional[str] = "predicted",  # "collapsed", "contradicted", etc.
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Emits a QWave beam event into the symbolic telemetry system.

    Key guarantees for downstream systems:
      - metadata.context is always present (SoulLaw-safe)
      - metadata.context.container_meta is synthesized if container_id exists
      - logic_tree is hoisted when present (resonance/mutation hooks)
    """

    # 🔄 Lazy import to avoid circular dependency
    from backend.modules.runtime.container_runtime import append_beam_to_container

    timestamp = time.time()
    ctx_in = context or {}
    meta_in = metadata or {}

    container_id = ctx_in.get("container_id", "unknown")
    qwave_id = generate_qwave_id(glyph_id, state=state)
    tick = ctx_in.get("tick") or int(timestamp * 1000)

    # Ensure required metadata values
    target = meta_in.get("target", "unspecified")

    wave_state = WaveState(
        wave_id=qwave_id,
        glyph_id=glyph_id,
        container_id=container_id,
        tick=tick,
        state=state,
        source=source,
        target=target,
        timestamp=timestamp,
        metadata=meta_in,
    )

    wave_dict: Dict[str, Any] = dict(vars(wave_state))

    # ✅ ALWAYS: put caller context into metadata.context (where SoulLaw actually looks)
    _ensure_metadata_context(wave_dict, ctx_in)

    # ✅ Hoist logic_tree when available (so resonance/mutation hooks don't skip)
    _hoist_logic_tree_from_result(wave_dict, result)

    # ✅ If any dict-string payload slipped in, hoist context + logic_tree out of it too
    _hoist_dict_string_payload(wave_dict)

    # Optional: keep result attached for debugging/telemetry (doesn't affect SoulLaw)
    if isinstance(result, dict):
        wave_dict.setdefault("result", result)

    # ✅ Validate via SoulLaw filter
    try:
        SoulLawValidator().validate_beam_event(wave_dict)
    except Exception as e:
        logger.warning(f"[emit_qwave_beam] SoulLaw validation failed: {e}")

    # ✅ Inject into container memory for later .dc.json export
    try:
        append_beam_to_container(container_id, wave_dict)
    except Exception as e:
        logger.warning(f"[emit_qwave_beam] Failed to append beam to container: {e}")

    # 📡 Log or broadcast beam
    try:
        log_beam_prediction(wave_dict)
    except Exception as e:
        logger.warning(f"[emit_qwave_beam] Failed to log symbolic beam: {e}")

    return wave_state