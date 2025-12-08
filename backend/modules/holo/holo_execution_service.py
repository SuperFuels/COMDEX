# backend/modules/holo/holo_execution_service.py

from __future__ import annotations

from typing import Any, Dict, Optional

from .holo_ir import HoloIR

try:
    # Beam engine + capsule wrapper
    from backend.modules.glyphwave.beam.beam_runtime import BeamRuntime
    from backend.modules.glyphwave.core.wave_capsule import WaveCapsule  # adjust path if needed

    HAVE_BEAM_ENGINE = True
except Exception:  # pragma: no cover
    BeamRuntime = None  # type: ignore
    WaveCapsule = None  # type: ignore
    HAVE_BEAM_ENGINE = False


# Single shared runtime for this process
_beam_runtime: Optional["BeamRuntime"] = None


def get_beam_runtime() -> Optional["BeamRuntime"]:
    """
    Lazy singleton around BeamRuntime.

    If BeamRuntime isn't importable (e.g. tests / stripped build),
    returns None and callers can gracefully degrade.
    """
    global _beam_runtime
    if not HAVE_BEAM_ENGINE:
        return None
    if _beam_runtime is None:
        _beam_runtime = BeamRuntime()
    return _beam_runtime


def _as_holo_dict(holo: HoloIR | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(holo, HoloIR):
        return dict(getattr(holo, "__dict__", {}))
    return dict(holo)


def build_wavecapsule_for_holo(
    holo: HoloIR | Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]] = None,
    mode: str = "qqc",
) -> "WaveCapsule":
    """
    Minimal .holo → WaveCapsule adapter for U4:

      .holo + input_ctx → WaveCapsule("holo.run", ...)

    The capsule payload is intentionally generic so you can evolve the
    internal engine without changing this border.
    """
    if not HAVE_BEAM_ENGINE or WaveCapsule is None:  # type: ignore
        raise RuntimeError("Beam engine not available")

    holo_dict = _as_holo_dict(holo)
    container_id = holo_dict.get("container_id") or "unknown"

    args: Dict[str, Any] = {
        "holo": holo_dict,
        "input_ctx": input_ctx or {},
        "run_mode": mode,
    }

    metadata: Dict[str, Any] = {
        "kind": "holo_program",
        "holo_id": holo_dict.get("holo_id"),
        "container_id": container_id,
        "source": "holo_run_api",
    }

    capsule = WaveCapsule(
        opcode="holo.run",
        args=args,
        metadata=metadata,
        container_id=container_id,
    )
    return capsule


def run_holo_snapshot(
    holo: HoloIR | Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]] = None,
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Primary execution contract for U4:

      run_holo(holo, input_ctx) ->
        {
          "holo_id": ...,
          "container_id": ...,
          "mode": "qqc" | "sle" | "dry_run" | ...,
          "status": "...",
          "output": {...} | null,
          "updated_holo": {...},
          "metrics": {...}
        }

    Internally this wraps:
      .holo → WaveCapsule → BeamRuntime.execute_capsule(...)
    and optionally persists an updated .holo via holo_service.save_holo_from_dict.
    """
    holo_dict = _as_holo_dict(holo)
    container_id = holo_dict.get("container_id") or "unknown"

    rt = get_beam_runtime()
    if rt is None:
        # graceful degradation if beam engine isn't wired yet
        return {
            "holo_id": holo_dict.get("holo_id"),
            "container_id": container_id,
            "mode": mode,
            "status": "beam_runtime_unavailable",
            "output": None,
            "updated_holo": holo_dict,
            "metrics": {},
        }

    try:
        capsule = build_wavecapsule_for_holo(holo_dict, input_ctx=input_ctx, mode=mode)
        result: Dict[str, Any] = rt.execute_capsule(capsule, mode=mode)
    except Exception as e:  # pragma: no cover
        return {
            "holo_id": holo_dict.get("holo_id"),
            "container_id": container_id,
            "mode": mode,
            "status": "execution_error",
            "error": str(e),
            "output": None,
            "updated_holo": holo_dict,
            "metrics": {},
        }

    # --- Extract metrics / coherence from BeamRuntime result ---------------
    metrics = dict(result.get("metrics") or {})
    coherence = (
        metrics.get("coherence_score")
        or metrics.get("coherence")
        or result.get("coherence_score")
    )

    # --- Build an updated Holo snapshot (ψκT metrics, etc.) ----------------
    updated_holo = dict(holo_dict)
    field = dict(updated_holo.get("field") or {})
    field_metrics = dict(field.get("metrics") or {})

    if coherence is not None:
        field_metrics["coherence"] = coherence

    # merge any beam_runtime metrics under a nested key
    if metrics:
        field_metrics.setdefault("beam_runtime", {})
        field_metrics["beam_runtime"].update(metrics)

    field["metrics"] = field_metrics
    updated_holo["field"] = field

    # Optional: persist via holo_service.save_holo_from_dict
    try:
        from backend.modules.holo.holo_service import save_holo_from_dict  # type: ignore

        saved = save_holo_from_dict(updated_holo)
        updated_holo = getattr(saved, "__dict__", saved)
    except Exception:
        # fine to skip persist if writer isn't wired yet
        pass

    return {
        "holo_id": updated_holo.get("holo_id", holo_dict.get("holo_id")),
        "container_id": updated_holo.get("container_id", container_id),
        "mode": mode,
        "status": result.get("status", "ok"),
        "output": result.get("output"),
        "updated_holo": updated_holo,
        "metrics": {
            "coherence": coherence,
            **metrics,
        },
    }