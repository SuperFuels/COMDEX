#!/usr/bin/env python3
# File: backend/modules/codex/beam_model.py

from __future__ import annotations

import ast
import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# In-memory beam mutation registry (can be replaced with DB or Redis)
BEAM_MUTATION_LOG: Dict[str, List[Dict[str, Any]]] = {}

# Optional file log location
MUTATION_LOG_DIR = "./logs/beam_history"
os.makedirs(MUTATION_LOG_DIR, exist_ok=True)


def _safe_dict(obj: Any) -> Dict[str, Any]:
    """
    Converts objects (like Beam) to dict if possible.
    Always returns a dict (never a list/string) to keep logs/schema stable.
    """
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            out = obj.to_dict()
            return out if isinstance(out, dict) else {"value": str(out)}
        except Exception:
            return {"value": str(obj)}
    return {"value": str(obj)}


def _coerce_dict(value: Any, *, label: str = "value") -> Dict[str, Any]:
    """
    Defensive coercion: many upstream paths pass dict-like values as strings.
    Converts:
      - dict -> dict
      - JSON str -> dict
      - python-literal str (single quotes) -> dict
      - None/other -> {}
    """
    if isinstance(value, dict):
        return value
    if value is None:
        return {}

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return {}
        # JSON first
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass
        # Python literal (handles single quotes)
        try:
            parsed = ast.literal_eval(s)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            logger.debug(f"[BeamModel] Could not coerce {label} from string: {s[:160]!r}")
            return {}

    return {}


def _coerce_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass
        try:
            parsed = ast.literal_eval(s)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return [value]
    return [value]


def _hoist_dict_string_payload(beam: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real fix: if upstream stored a dict-as-string under "glyph"/"program"/"codex"/"scroll",
    hoist context + logic_tree into proper locations BEFORE validators/hooks run.
    """
    payload_str = (
        beam.get("glyph")
        or beam.get("program")
        or beam.get("codex")
        or beam.get("scroll")
        or ""
    )

    if isinstance(payload_str, str):
        s = payload_str.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = ast.literal_eval(s)
                if isinstance(obj, dict):
                    ctx = obj.get("context")
                    if isinstance(ctx, dict):
                        beam.setdefault("metadata", {}).setdefault("context", {}).update(ctx)
                    if isinstance(obj.get("logic_tree"), dict):
                        beam.setdefault("logic_tree", obj["logic_tree"])
            except Exception:
                pass

    # ensure container_meta exists if container_id exists
    ctx = (beam.get("metadata") or {}).get("context") or {}
    cid = ctx.get("container_id")
    cm = ctx.get("container_meta")
    if cid and not isinstance(cm, dict):
        ctx["container_meta"] = {
            "id": cid,
            "kind": ctx.get("container_kind", "qqc"),
            "source": ctx.get("container_source", "qqc_kernel_boot"),
        }
        beam.setdefault("metadata", {})["context"] = ctx

    return beam


class Beam:
    """
    Beam is the canonical runtime object backing QQC/Codex/Photon pipelines.

    Key goal: NEVER allow logic_tree/context to remain as strings.
    If upstream passes shorthand strings or mismatched keys, normalize safely.
    """

    def __init__(
        self,
        *,
        id: str,
        logic_tree: Optional[Union[Dict[str, Any], str]] = None,
        glyphs: Optional[Union[List[Any], str]] = None,
        phase: float = 0.0,
        amplitude: float = 0.0,
        coherence: float = 0.0,
        origin_trace: str = "unknown",
        # Schema-friendly fields
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], str]] = None,
        _physics_snapshot: Optional[Dict[str, Any]] = None,
        # Everything else (legacy / capsule schema)
        status: str = "initial",
        sqi_score: Optional[float] = None,
        entropy: Optional[float] = None,
        drift_cost: Optional[float] = None,
        drift_signature: Optional[str] = None,
        soullaw_status: str = "unknown",
        soullaw_violations: Optional[List[str]] = None,
        **extras: Any,
    ):
        self.id = str(id)

        # Normalize critical fields
        self.logic_tree = _coerce_dict(logic_tree, label="logic_tree")
        self.glyphs = _coerce_list(glyphs)

        # Core physics-ish fields (safe defaults)
        self.phase = float(phase or 0.0)
        self.amplitude = float(amplitude or 0.0)
        self.coherence = float(coherence or 0.0)
        self.origin_trace = str(origin_trace or "unknown")

        # Schema + metadata/context (normalize)
        self.metadata: Dict[str, Any] = metadata if isinstance(metadata, dict) else {}
        ctx_dict = _coerce_dict(context, label="context")

        # If upstream incorrectly put context at root, callers may still pass it in extras
        root_ctx = extras.pop("context", None)
        if root_ctx is not None and not ctx_dict:
            ctx_dict = _coerce_dict(root_ctx, label="context(root)")

        # Always store context under metadata.context (schema-safe)
        meta_ctx = self.metadata.get("context")
        if not isinstance(meta_ctx, dict):
            meta_ctx = {}
            self.metadata["context"] = meta_ctx
        if ctx_dict:
            meta_ctx.update(ctx_dict)

        self._physics_snapshot = _physics_snapshot if isinstance(_physics_snapshot, dict) else {}

        # Additional defaults
        self.status = str(status or "initial")
        self.sqi_score = sqi_score
        self.entropy = entropy
        self.drift_cost = drift_cost
        self.drift_signature = drift_signature
        self.soullaw_status = str(soullaw_status or "unknown")
        self.soullaw_violations = list(soullaw_violations or [])

        # Store extra arbitrary fields for forward-compat (capsule schema is large)
        self.extras: Dict[str, Any] = extras

        # Final sanity: guarantee logic_tree is dict
        if not isinstance(self.logic_tree, dict):
            self.logic_tree = {}

        # Ensure container_meta exists if container_id exists (prevents invalid_container_metadata)
        try:
            c = self.metadata.get("context", {})
            if isinstance(c, dict):
                cid = c.get("container_id")
                cmeta = c.get("container_meta")
                if cid and not isinstance(cmeta, dict):
                    c["container_meta"] = {"id": cid, "kind": "qqc", "source": "qqc_kernel_boot"}
        except Exception:
            pass

    # -------------------------
    # Construction helpers
    # -------------------------
    @staticmethod
    def _extract_logic_tree(data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data.get("logic_tree"), dict):
            return data["logic_tree"]
        if isinstance(data.get("action"), dict) and isinstance(data["action"].get("logic_tree"), dict):
            return data["action"]["logic_tree"]
        lt = data.get("logic_tree")
        if isinstance(lt, str):
            return _coerce_dict(lt, label="logic_tree(str)")
        return {}

    @staticmethod
    def _extract_metadata_and_context(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns schema-safe metadata dict with context nested inside it.
        """
        meta = data.get("metadata")
        meta = meta if isinstance(meta, dict) else {}

        root_ctx = _coerce_dict(data.get("context"), label="context(root)")

        meta_ctx = meta.get("context")
        meta_ctx = meta_ctx if isinstance(meta_ctx, dict) else {}

        if root_ctx:
            meta_ctx.update(root_ctx)

        if meta_ctx:
            meta = dict(meta)
            meta["context"] = meta_ctx

        # Final guard: container_meta synthesis if missing
        ctx = meta.get("context") if isinstance(meta.get("context"), dict) else {}
        cid = ctx.get("container_id")
        cm = ctx.get("container_meta")
        if cid and not isinstance(cm, dict):
            ctx["container_meta"] = {
                "id": cid,
                "kind": ctx.get("container_kind", "qqc"),
                "source": ctx.get("container_source", "qqc_kernel_boot"),
            }
            meta = dict(meta)
            meta["context"] = ctx

        return meta

    @classmethod
    def from_any(cls, payload: Union["Beam", Dict[str, Any], str]) -> "Beam":
        """
        Accepts Beam | dict | dict-string.
        IMPORTANT: hoists dict-string payloads BEFORE normalization/validation.
        """
        if isinstance(payload, Beam):
            return payload

        # Coerce input to dict
        if isinstance(payload, str):
            d = _coerce_dict(payload, label="beam_payload(str)")
        else:
            d = payload if isinstance(payload, dict) else {}

        # 🔥 Real fix: hoist context + logic_tree out of dict-strings on common fields
        d = _hoist_dict_string_payload(dict(d or {}))

        # Handle beam_id alias
        beam_id = (
            d.get("id")
            or d.get("beam_id")
            or d.get("wave_id")
            or f"beam-{datetime.datetime.utcnow().timestamp()}"
        )

        meta = cls._extract_metadata_and_context(d)
        ctx = meta.get("context") if isinstance(meta, dict) else {}

        return cls(
            id=str(beam_id),
            logic_tree=cls._extract_logic_tree(d),
            glyphs=d.get("glyphs") or d.get("glyph_stream") or [],
            phase=d.get("phase", 0.0),
            amplitude=d.get("amplitude", 0.0),
            coherence=d.get("coherence", d.get("rho", 0.0)),
            origin_trace=d.get("origin_trace", d.get("trace", "unknown")),
            metadata=meta,
            context=ctx,
            _physics_snapshot=d.get("_physics_snapshot") if isinstance(d.get("_physics_snapshot"), dict) else {},
            status=d.get("status", "initial"),
            sqi_score=d.get("sqi_score"),
            entropy=d.get("entropy"),
            drift_cost=d.get("drift_cost"),
            drift_signature=d.get("drift_signature"),
            soullaw_status=d.get("soullaw_status", "unknown"),
            soullaw_violations=d.get("soullaw_violations") if isinstance(d.get("soullaw_violations"), list) else [],
            **{
                k: v
                for k, v in d.items()
                if k
                not in {
                    "id", "beam_id", "wave_id",
                    "logic_tree",
                    "glyphs", "glyph_stream",
                    "phase", "amplitude", "coherence", "rho",
                    "origin_trace", "trace",
                    "metadata", "context", "_physics_snapshot",
                    "status", "sqi_score", "entropy",
                    "drift_cost", "drift_signature",
                    "soullaw_status", "soullaw_violations",
                }
            },
        )

    # -------------------------
    # Serialization
    # -------------------------
    def to_dict(self) -> Dict[str, Any]:
        base = {
            "id": self.id,
            "logic_tree": self.logic_tree,
            "glyphs": self.glyphs,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "coherence": self.coherence,
            "origin_trace": self.origin_trace,
            "metadata": self.metadata,
            "_physics_snapshot": self._physics_snapshot,
            "status": self.status,
            "sqi_score": self.sqi_score,
            "entropy": self.entropy,
            "drift_cost": self.drift_cost,
            "drift_signature": self.drift_signature,
            "soullaw_status": self.soullaw_status,
            "soullaw_violations": self.soullaw_violations,
        }

        if isinstance(self.extras, dict) and self.extras:
            base.update(self.extras)

        return base


__all__ = ["Beam"]


# --- Register a beam mutation ---
def register_beam_mutation(
    beam_id: str,
    mutation: Dict[str, Any],
    container_id: Optional[str] = None,
    symbolic_context: Optional[Dict[str, Any]] = None,
    broadcast: bool = False,
) -> None:
    """
    Registers a mutation event for a beam, including full metadata.
    """
    timestamp = datetime.datetime.utcnow().isoformat()

    mutation = _safe_dict(mutation)
    symbolic_context = symbolic_context if isinstance(symbolic_context, dict) else {}

    record = {
        "timestamp": timestamp,
        "beam_id": str(beam_id),
        "container_id": container_id,
        "event": "mutation",
        "mutation": mutation,
        "symbolic_context": symbolic_context,
    }

    BEAM_MUTATION_LOG.setdefault(str(beam_id), []).append(record)

    logger.info(f"[BeamHistory] Beam '{beam_id}' mutated at {timestamp} | Type: {mutation.get('type', 'unknown')}")
    print(f"🧬 Beam '{beam_id}' mutated at {timestamp} | Type: {mutation.get('type', 'unknown')}")

    save_beam_history_to_file(str(beam_id))

    if broadcast:
        try:
            from backend.modules.hologram.ghx_replay_broadcast import broadcast_mutation_event
            broadcast_mutation_event(record)
        except Exception as e:
            logger.warning(f"[BeamHistory] Mutation broadcast failed: {e}")


# --- Register a beam collapse ---
def register_beam_collapse(
    beam_id: str,
    collapse_data: Dict[str, Any],
    container_id: Optional[str] = None,
    symbolic_context: Optional[Dict[str, Any]] = None,
    broadcast: bool = False,
) -> None:
    """
    Registers a collapse event for a beam.
    """
    timestamp = datetime.datetime.utcnow().isoformat()

    collapse_data = _safe_dict(collapse_data)
    symbolic_context = symbolic_context if isinstance(symbolic_context, dict) else {}

    record = {
        "timestamp": timestamp,
        "beam_id": str(beam_id),
        "container_id": container_id,
        "event": "collapse",
        "details": collapse_data,
        "symbolic_context": symbolic_context,
    }

    BEAM_MUTATION_LOG.setdefault(str(beam_id), []).append(record)

    logger.info(f"[BeamHistory] Beam '{beam_id}' collapsed at {timestamp}")
    print(f"💥 Beam '{beam_id}' collapsed at {timestamp}: {collapse_data}")

    save_beam_history_to_file(str(beam_id))

    if broadcast:
        try:
            from backend.modules.hologram.ghx_replay_broadcast import broadcast_mutation_event
            broadcast_mutation_event(record)
        except Exception as e:
            logger.warning(f"[BeamHistory] Collapse broadcast failed: {e}")


def get_beam_history(beam_id: str) -> List[Dict[str, Any]]:
    return BEAM_MUTATION_LOG.get(str(beam_id), [])


def summarize_beam_history(beam_id: str) -> str:
    history = get_beam_history(str(beam_id))
    if not history:
        return f"🕳️ No history found for beam '{beam_id}'."

    summary = f"📜 History for beam '{beam_id}':\n"
    for entry in history:
        ts = entry.get("timestamp", "?")
        event = entry.get("event", "unknown")
        if event == "mutation":
            mut = entry.get("mutation", {}) or {}
            summary += f" - {ts} | Mutation: {mut.get('type', '?')} -> {mut.get('details', {})}\n"
        elif event == "collapse":
            details = entry.get("details", {}) or {}
            summary += f" - {ts} | 🛑 Collapse: {details}\n"
        else:
            summary += f" - {ts} | Event: {event}\n"
    return summary


def save_beam_history_to_file(beam_id: str) -> None:
    history = get_beam_history(str(beam_id))
    if not history:
        return

    filepath = os.path.join(MUTATION_LOG_DIR, f"{beam_id}_history.json")
    try:
        with open(filepath, "w") as f:
            json.dump(history, f, indent=2)
        logger.debug(f"[BeamHistory] Saved beam history to {filepath}")
    except Exception as e:
        logger.error(f"[BeamHistory] Failed to save history file: {e}")


def load_beam_history_from_file(beam_id: str) -> List[Dict[str, Any]]:
    filepath = os.path.join(MUTATION_LOG_DIR, f"{beam_id}_history.json")
    try:
        with open(filepath, "r") as f:
            history = json.load(f)
        if isinstance(history, list):
            BEAM_MUTATION_LOG[str(beam_id)] = history
        logger.info(f"[BeamHistory] Loaded history from {filepath}")
        return history if isinstance(history, list) else []
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"[BeamHistory] Error loading history file: {e}")
        return []