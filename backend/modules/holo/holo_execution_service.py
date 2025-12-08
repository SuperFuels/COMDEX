# backend/modules/holo/holo_execution_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.QQC.holo_runtime import execute_holo_program

# Optional: live QWave beam collector – not strictly used yet, but kept for future wiring
try:
    from backend.modules.glyphwave.qwave.qwave_writer import (
        collect_qwave_beams as _collect_qwave_beams,
    )
except Exception:  # pragma: no cover
    _collect_qwave_beams = None

# Optional: .holo persistence – we fail soft if it's missing
try:
    from backend.modules.holo.holo_service import (
        save_holo_from_dict as _save_holo_from_dict,
    )
except Exception:  # pragma: no cover
    _save_holo_from_dict = None


@dataclass
class RunHoloResult:
    """
    Structured result for run_holo_snapshot, but we still return dicts
    outward (FastAPI / JSON). This just keeps the shape explicit.
    """
    status: str
    message: Optional[str]
    container_id: str
    holo_id: Optional[str]
    tick: Optional[int]
    beams: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    output: Dict[str, Any]
    updated_holo: Optional[Dict[str, Any]]
    # NEW: persistence info (U4D)
    new_holo_id: Optional[str] = None
    new_revision: Optional[int] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_container_and_tick(
    holo: Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]],
) -> tuple[str, Optional[int]]:
    """
    Pull container_id + tick out of the holo / input_ctx in a tolerant way.
    """
    container_id = str(holo.get("container_id") or "unknown")

    tick: Optional[int] = None
    # Prefer timefold.tick if present
    tf = holo.get("timefold") or {}
    if "tick" in tf:
        try:
            tick = int(tf.get("tick"))
        except Exception:
            tick = None

    # Fallback: input_ctx.tick
    if tick is None and input_ctx is not None:
        try:
            if "tick" in input_ctx:
                tick = int(input_ctx.get("tick"))
        except Exception:
            tick = None

    return container_id, tick


def emit_beams_from_holo(holo: Dict[str, Any], mode: str = "qqc") -> List[Dict[str, Any]]:
    """
    VERY MINIMAL placeholder:

    Look at holo.ghx.edges (or links) and synthesise QWave-like beams so the
    DevTools / QFC field can visualise *something* when you press ▶ Run .holo.

    This does NOT hit the real QWave / BeamRuntime stack yet – it’s just a
    structural bridge: GHX edge → beam dict.
    """
    ghx = holo.get("ghx") or {}
    edges = ghx.get("edges") or ghx.get("links") or []
    if not isinstance(edges, list):
        return []

    beams: List[Dict[str, Any]] = []

    for idx, raw in enumerate(edges):
        e = raw or {}

        # Tolerate all the usual GHX endpoint shapes
        src_id = (
            e.get("source")
            or e.get("src")
            or e.get("from")
            or e.get("src_id")
            or None
        )
        dst_id = (
            e.get("target")
            or e.get("dst")
            or e.get("to")
            or e.get("dst_id")
            or None
        )

        if not src_id or not dst_id:
            continue

        beam_id = e.get("id") or f"holo-beam-{idx}"

        beams.append(
            {
                "id": beam_id,
                "source": src_id,
                "target": dst_id,
                "carrier_type": "HOLO_SYNTH",
                "modulation": mode or "qqc",
                "coherence": 1.0,
                "collapse_state": "original",
                "entangled_path": [src_id, dst_id],
                "mutation_trace": [],
                "metadata": {
                    "from_holo": True,
                    "edge_kind": e.get("kind"),
                },
            }
        )

    return beams


def _collect_beams_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Optional live beam collection via qwave_writer.

    Right now we don't rely on this for the ▶ Run .holo UX, but keep it
    around so we can blend real beams in later.
    """
    if not _collect_qwave_beams:
        return []

    try:
        raw_beams = _collect_qwave_beams(container_id) or []
    except Exception as e:
        print(f"[HOLO-RUN] collect_qwave_beams failed for {container_id}: {e}")
        return []

    shaped: List[Dict[str, Any]] = []
    for b in raw_beams:
        shaped.append(
            {
                "id": b.get("id"),
                "source": b.get("source") or b.get("source_id"),
                "target": b.get("target") or b.get("target_id"),
                "carrier_type": b.get("carrier_type", "SIMULATED"),
                "modulation": b.get("modulation") or b.get("modulation_strategy", "SimPhase"),
                "coherence": b.get("coherence", 1.0),
                "entangled_path": b.get("entangled_path", []),
                "mutation_trace": b.get("mutation_trace", []),
                "collapse_state": b.get("collapse_state", "original"),
                "metadata": b.get("metadata", {}),
            }
        )
    return shaped


async def run_holo_snapshot(
    holo: Dict[str, Any],
    input_ctx: Optional[Dict[str, Any]] = None,
    mode: str = "qqc",
) -> Dict[str, Any]:
    """
    Minimal, fail-soft holo runner used by the Dev Tools “▶ Run .holo” button.

    NEW: this now calls the Symatics/SLE pipeline via execute_holo_program,
    while still:
      - synthesising beams from GHX edges for the Field Lab UI
      - bumping run_count / last_run_at
      - bumping revision and persisting via save_holo_from_dict (if wired)

    Contract:

      .holo + input_ctx + mode
        → {
              status, message,
              container_id, holo_id, tick,
              beams[], metrics{},
              output{},
              updated_holo?,
              new_holo_id?, new_revision?
           }
    """
    input_ctx = input_ctx or {}
    container_id, tick = _derive_container_and_tick(holo, input_ctx)

    try:
        # ------------------------------------------------------------------
        # 1) Run real SLE / Symatics engine (backend/QQC/holo_runtime.py)
        # ------------------------------------------------------------------
        sle_result: Dict[str, Any] = {}
        try:
            sle_result = execute_holo_program(holo, input_ctx, mode=mode)
        except Exception as e:
            # Don't break DevTools if SLE is misconfigured – just log and
            # fall back to synthetic-only behaviour.
            print(f"[HOLO-RUN] SLE execution failed, continuing with synthetic beams: {e!r}")
            sle_result = {}

        sle_output = sle_result.get("output") or {}
        sle_metrics = sle_result.get("metrics") or {}
        sle_status = sle_result.get("sle_status") or "ok"

        # ------------------------------------------------------------------
        # 2) Synthesise beams from GHX edges for the mini-program rail
        # ------------------------------------------------------------------
        beams = emit_beams_from_holo(holo, mode=mode)

        if beams:
            status = sle_status or "ok"
            message: Optional[str] = None
        else:
            # Engine may still have run, but there were no GHX edges to beam.
            status = sle_status or "no_beams"
            message = "No GHX edges found to synthesise beams from."

        # Base metrics (beam count, tick, mode)
        metrics: Dict[str, Any] = {
            "num_beams": len(beams),
            "mode": mode,
            "tick": tick,
        }
        # Overlay SLE metrics on top
        metrics.update(sle_metrics)

        # ------------------------------------------------------------------
        # 3) Build updated_holo with run metadata + bump revision
        # ------------------------------------------------------------------
        updated_holo: Optional[Dict[str, Any]] = None
        new_holo_id: Optional[str] = None
        new_revision: Optional[int] = None

        try:
            updated = dict(holo)  # shallow clone is fine for metadata
            extra = dict(updated.get("extra") or {})
            run_count = int(extra.get("run_count", 0)) + 1

            extra.update(
                {
                    "run_count": run_count,
                    "last_run_at": _utc_now_iso(),
                    "last_run_mode": mode,
                    "last_run_metrics": metrics,
                }
            )
            updated["extra"] = extra

            # Bump revision if a version block exists
            version = updated.get("version")
            if isinstance(version, dict):
                try:
                    rev = int(version.get("revision", 0))
                    rev = rev + 1
                    version["revision"] = rev
                    new_revision = rev
                except Exception:
                    # If it looks weird, just leave it alone
                    pass

            # Persist via save_holo_from_dict if available
            if _save_holo_from_dict is not None:
                try:
                    saved = _save_holo_from_dict(updated)  # type: ignore[call-arg]

                    # Normalise saved → dict + pull id/revision
                    if hasattr(saved, "__dict__"):
                        saved_dict = dict(saved.__dict__)
                    elif isinstance(saved, dict):
                        saved_dict = saved
                    else:
                        saved_dict = updated

                    updated_holo = saved_dict

                    # Pull holo_id + revision if present
                    new_holo_id = (
                        saved_dict.get("holo_id")
                        or getattr(saved, "holo_id", None)
                    )
                    if new_revision is None:
                        # revision may live either at top-level or under version
                        new_revision = (
                            saved_dict.get("revision")
                            or getattr(saved, "revision", None)
                        )
                        if new_revision is None:
                            version_block = saved_dict.get("version") or {}
                            if isinstance(version_block, dict):
                                new_revision = version_block.get("revision")
                except Exception as e:
                    print(f"[HOLO-RUN] save_holo_from_dict failed: {e}")
                    updated_holo = updated
                    new_holo_id = updated.get("holo_id")
            else:
                # No saver wired – still return the updated blob to the UI
                updated_holo = updated
                new_holo_id = updated.get("holo_id")

        except Exception as e:
            print(f"[HOLO-RUN] failed to build updated_holo: {e}")
            updated_holo = None
            new_holo_id = None
            new_revision = None

        # ------------------------------------------------------------------
        # 4) Choose output payload (prefer SLE, fall back to echo)
        # ------------------------------------------------------------------
        output = sle_output or {"echo_input_ctx": input_ctx}

        result = RunHoloResult(
            status=status,
            message=message,
            container_id=container_id,
            holo_id=holo.get("holo_id"),
            tick=tick,
            beams=beams,
            metrics=metrics,
            output=output,
            updated_holo=updated_holo,
            new_holo_id=new_holo_id,
            new_revision=new_revision,
        )
        # We still return a plain dict to FastAPI / callers
        return result.__dict__

    except Exception as e:
        # Fail-soft: NEVER throw; route will still return 200 with status="error"
        print(f"[HOLO-RUN] unexpected error while running holo: {e}")
        error_result = RunHoloResult(
            status="error",
            message=f"run_holo_snapshot failed: {e}",
            container_id=container_id,
            holo_id=holo.get("holo_id"),
            tick=tick,
            beams=[],
            metrics={},
            output={},
            updated_holo=None,
            new_holo_id=None,
            new_revision=None,
        )
        return error_result.__dict__