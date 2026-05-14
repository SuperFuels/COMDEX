"""
SQIBeamKernel - symbolic quantum intelligence beam processing kernel.

GX1/pytest-safe goals:
- keep module import light (no UCS/QFC/ws bring-up at import-time)
- tolerate missing heavy subsystems via optional imports
- deterministic fallbacks when TESSARIS_DETERMINISTIC_TIME=1
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

USE_PARALLELISM = True


# ─────────────────────────────────────────────
# Env gates
# ─────────────────────────────────────────────
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _stable_id(prefix: str, obj: Any) -> str:
    try:
        blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        blob = repr(obj)
    h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{h}"


# ─────────────────────────────────────────────
# Optional imports (NO heavy runtime at import-time)
# ─────────────────────────────────────────────
try:
    from backend.modules.codex.beam_model import Beam  # type: ignore
except Exception:
    Beam = None  # type: ignore


def _maybe_import_runtime():
    """
    Import-heavy SQI runtime components are loaded only when we actually process beams.
    This prevents circular-import and background-thread bringup during tests.
    """
    # Collapse / mutation / scoring / validation
    try:
        from backend.modules.glyphwave.kernels.interference_kernel_core import collapse_wave_superposition  # type: ignore
    except Exception:
        def collapse_wave_superposition(beam, use_gpu: bool = True):
            return {"status": "stub", "use_gpu": bool(use_gpu)}

    try:
        from backend.modules.creative.symbolic_mutation_engine import mutate_beam  # type: ignore
    except Exception:
        def mutate_beam(beam):
            return beam

    try:
        from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container  # type: ignore
    except Exception:
        def inject_sqi_scores_into_container(container: Dict[str, Any]) -> Dict[str, Any]:
            return container

    try:
        from backend.modules.sqi.sqi_drift_analyzer import analyze_drift_patterns  # type: ignore
    except Exception:
        def analyze_drift_patterns(container: Dict[str, Any]) -> Dict[str, Any]:
            return {"signature": None, "cost": 0.0}

    try:
        from backend.modules.codex.symbolic_entropy import compute_entropy_metrics  # type: ignore
    except Exception:
        def compute_entropy_metrics(_beam) -> float:
            return 0.0

    try:
        from backend.modules.glyphvault.soul_law_validator import SoulLawValidator  # type: ignore
    except Exception:
        SoulLawValidator = None  # type: ignore

    # Side-effect-ish integrations (keep best-effort + quiet)
    try:
        from backend.modules.codex.beam_history import register_beam_collapse  # type: ignore
    except Exception:
        def register_beam_collapse(*_a, **_kw):  # noqa: ANN001
            return None

    try:
        from backend.modules.glyphvault.beam_registry import store_collapsed_beam  # type: ignore
    except Exception:
        def store_collapsed_beam(*_a, **_kw):  # noqa: ANN001
            return None

    try:
        from backend.modules.codex.symbolic_metadata import attach_symbolic_metadata  # type: ignore
    except Exception:
        def attach_symbolic_metadata(*_a, **_kw):  # noqa: ANN001
            return None

    try:
        from backend.modules.codex.symbolic_qscore_hooks import apply_qscore_hooks  # type: ignore
    except Exception:
        def apply_qscore_hooks(*_a, **_kw):  # noqa: ANN001
            return None

    try:
        from backend.modules.qfield.qfc_ws_broadcast import broadcast_beam_event  # type: ignore
    except Exception:
        def broadcast_beam_event(*_a, **_kw):  # noqa: ANN001
            return None

    return {
        "collapse_wave_superposition": collapse_wave_superposition,
        "mutate_beam": mutate_beam,
        "inject_sqi_scores_into_container": inject_sqi_scores_into_container,
        "analyze_drift_patterns": analyze_drift_patterns,
        "compute_entropy_metrics": compute_entropy_metrics,
        "SoulLawValidator": SoulLawValidator,
        "register_beam_collapse": register_beam_collapse,
        "store_collapsed_beam": store_collapsed_beam,
        "attach_symbolic_metadata": attach_symbolic_metadata,
        "apply_qscore_hooks": apply_qscore_hooks,
        "broadcast_beam_event": broadcast_beam_event,
    }


# ──────────────────────────────────────────────
# Class Wrapper for QQC Integration
# ──────────────────────────────────────────────
class SQIBeamKernel:
    """
    Manages SQI beam lifecycle:
    collapse -> mutate -> score -> validate -> broadcast.

    Import-time safety:
    - no WaveState import
    - no QFC/ws import at module load
    """

    def __init__(self, parallel: bool = True):
        self.parallel = bool(parallel)
        self.reasoner = None

        # Reasoner is optional + heavy; import lazily.
        try:
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import (  # type: ignore
                SQIReasoningEngine,
            )
            self.reasoner = SQIReasoningEngine()
        except Exception:
            self.reasoner = None

        if not _quiet_enabled():
            logger.info(f"[SQIBeamKernel] Initialized (parallel={self.parallel})")

    def propagate(self, beam_data: Dict[str, Any], sqi_score: Optional[float] = None) -> Dict[str, Any]:
        """
        QQC interface method.
        Accepts a symbolic beam dict, processes it internally, returns summarized state.
        """
        try:
            data = dict(beam_data or {})

            # --- Auto-wrap legacy telemetry into physics ---
            if any(k in data for k in ["beam_id", "coherence", "phase_shift", "entropy_drift", "gain", "timestamp"]):
                physics_block = {
                    "beam_id": data.pop("beam_id", None),
                    "coherence": data.pop("coherence", None),
                    "phase_shift": data.pop("phase_shift", None),
                    "entropy_drift": data.pop("entropy_drift", None),
                    "gain": data.pop("gain", None),
                    "timestamp": data.pop("timestamp", None),
                }
                data["physics"] = physics_block

            # --- Safe Beam construction (deterministic fallback id) ---
            beam_obj = None
            if Beam is not None:
                try:
                    if hasattr(Beam, "from_dict"):
                        beam_obj = Beam.from_dict(data)
                    else:
                        beam_obj = Beam(
                            id=data.get("id") or _stable_id("beam", data),
                            logic_tree=data.get("logic_tree") or {},
                            glyphs=data.get("glyphs") or [],
                            phase=float(data.get("phase") or 0.0),
                            amplitude=float(data.get("amplitude") or 1.0),
                            coherence=float(data.get("coherence") or 1.0),
                            origin_trace=str(data.get("origin_trace") or "kernel:init"),
                        )
                except Exception:
                    beam_obj = None

            if beam_obj is None:
                # Minimal stub shape if Beam model unavailable
                beam_obj = type("BeamStub", (), {})()
                setattr(beam_obj, "id", data.get("id") or _stable_id("beam", data))
                setattr(beam_obj, "to_dict", lambda: dict(data))
                setattr(beam_obj, "status", "init")

            # --- Attach avatar + container context for SoulLaw (best-effort) ---
            ctx = data.get("context", {})
            if not isinstance(ctx, dict):
                ctx = {}

            meta = data.get("metadata", {})
            if isinstance(meta, dict) and isinstance(meta.get("context"), dict):
                ctx = {**ctx, **meta["context"]}

            try:
                from backend.modules.aion_core.avatar_state import AVATAR_STATE as CORE_AVATAR_STATE  # type: ignore
            except Exception:
                CORE_AVATAR_STATE = {"id": "AION_CORE", "role": "root_cognitive_agent"}

            avatar_state = {
                **(CORE_AVATAR_STATE if isinstance(CORE_AVATAR_STATE, dict) else {}),
                "id": ctx.get("avatar_id")
                or (CORE_AVATAR_STATE.get("id") if isinstance(CORE_AVATAR_STATE, dict) else "AION_CORE"),
                "avatar_state": ctx.get("avatar_state"),
                "avatar_state_ts": ctx.get("avatar_state_ts"),
                "container_id": ctx.get("container_id"),
            }

            container_metadata = ctx.get("container_meta") if isinstance(ctx.get("container_meta"), dict) else {}
            if not container_metadata and ctx.get("container_id"):
                container_metadata = {
                    "id": ctx.get("container_id"),
                    "kind": ctx.get("container_kind", "qqc"),
                    "source": ctx.get("container_source", "qqc_kernel_boot"),
                }

            setattr(beam_obj, "avatar_state", avatar_state)
            setattr(beam_obj, "container_metadata", container_metadata)

            # --- Process as usual ---
            results = self.process_batch([beam_obj])
            processed = results[0] if results else None
            if not processed:
                return {"status": "empty"}

            beam_state = processed.to_dict() if hasattr(processed, "to_dict") else vars(processed)

            # Strip heavy/internal physics for Codex export; keep snapshot
            codex_payload = dict(beam_state) if isinstance(beam_state, dict) else {"beam": beam_state}
            codex_payload.pop("physics", None)
            for k in ("amplitude", "coherence", "entropy", "phase", "drift_cost", "drift_signature"):
                codex_payload.pop(k, None)
            if isinstance(beam_state, dict):
                codex_payload["_physics_snapshot"] = beam_state.get("physics", {})

            if sqi_score is not None:
                codex_payload["sqi_score"] = float(sqi_score)

            return codex_payload

        except Exception as e:
            logger.error(f"[SQIBeamKernel] Beam propagation failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def process_batch(self, beams: List["Beam"]) -> List["Beam"]:
        """
        Main batch-processing logic for a list of beams.
        """
        rt = _maybe_import_runtime()

        processed_beams: List["Beam"] = []
        for beam in beams:
            try:
                bid = getattr(beam, "id", "unknown")
                logger.debug(f"[SQI] Processing beam: {bid}")

                # Collapse
                collapse_result = rt["collapse_wave_superposition"](beam, use_gpu=self.parallel)
                setattr(beam, "collapsed_state", collapse_result)
                setattr(beam, "status", "collapsed")

                # Mutation
                mutated = rt["mutate_beam"](beam)
                setattr(mutated, "status", "mutated")

                # Scoring
                bdict = mutated.to_dict() if hasattr(mutated, "to_dict") else vars(mutated)
                updated_container = rt["inject_sqi_scores_into_container"](bdict if isinstance(bdict, dict) else {})
                glyphs = updated_container.get("glyphs", []) if isinstance(updated_container, dict) else []
                setattr(mutated, "glyphs", glyphs)
                setattr(mutated, "sqi_score", self._average_sqi(glyphs))

                # Drift + Entropy
                drift_report = rt["analyze_drift_patterns"](mutated.to_dict() if hasattr(mutated, "to_dict") else {})
                setattr(mutated, "drift_signature", drift_report.get("signature"))
                setattr(mutated, "drift_cost", drift_report.get("cost"))
                setattr(mutated, "entropy", float(rt["compute_entropy_metrics"](mutated)))

                # SoulLaw
                self._validate_soullaw(mutated, SoulLawValidator=rt["SoulLawValidator"])

                # Metadata + Hooks (best-effort)
                rt["attach_symbolic_metadata"](mutated.to_dict() if hasattr(mutated, "to_dict") else {})
                rt["apply_qscore_hooks"](mutated.to_dict() if hasattr(mutated, "to_dict") else {})

                # Logging + Registry (best-effort)
                rt["register_beam_collapse"](mutated, getattr(mutated, "collapsed_state", None))
                rt["store_collapsed_beam"](mutated, mutated.to_dict() if hasattr(mutated, "to_dict") else {})

                # HUD + Broadcast (skip in quiet/deterministic)
                if not _quiet_enabled() and not _deterministic_time_enabled():
                    rt["broadcast_beam_event"](mutated)

                processed_beams.append(mutated)

            except Exception as e:
                bid = getattr(beam, "id", "unknown")
                logger.error(f"[SQI] Beam processing failed: {bid} - {e}", exc_info=True)
                setattr(beam, "status", "error")
                processed_beams.append(beam)

        return processed_beams

    # ──────────────────────────────
    # Internal Utility Methods
    # ──────────────────────────────
    def _average_sqi(self, glyphs: List[Dict[str, Any]]) -> float:
        scores = [float(g.get("sqi_score", 0.0)) for g in glyphs if isinstance(g, dict) and g.get("type") == "electron"]
        return sum(scores) / len(scores) if scores else 0.0

    def _validate_soullaw(self, beam: Any, *, SoulLawValidator: Any = None) -> None:
        # Dev-mode: always allow
        if os.getenv("SOULLAW_DEV_MODE") == "1":
            setattr(beam, "soullaw_status", "allowed")
            setattr(beam, "soullaw_violations", [])
            return

        if SoulLawValidator is None:
            setattr(beam, "soullaw_status", "allowed")
            setattr(beam, "soullaw_violations", [])
            return

        validator = SoulLawValidator()

        avatar_state = getattr(beam, "avatar_state", {})
        if not isinstance(avatar_state, dict):
            avatar_state = {}

        container_metadata = getattr(beam, "container_metadata", {})
        if not isinstance(container_metadata, dict):
            container_metadata = {}

        avatar_ok = True
        container_ok = True

        try:
            avatar_ok = bool(
                validator.validate_avatar_with_context(
                    avatar_state,
                    context={"beam_id": getattr(beam, "id", ""), "container_id": container_metadata.get("id")},
                )
            )
        except Exception:
            avatar_ok = True

        try:
            container_ok = bool(validator.validate_container(container_metadata))
        except Exception:
            container_ok = True

        status = "allowed" if (avatar_ok and container_ok) else "blocked"
        setattr(beam, "soullaw_status", status)
        setattr(beam, "soullaw_violations", [] if status == "allowed" else ["avatar", "container"])


# ──────────────────────────────────────────────
# Lazy singleton + back-compat proxy
# (NO import-time SQIBeamKernel() construction)
# ──────────────────────────────────────────────
_KERNEL: Optional[SQIBeamKernel] = None


def get_kernel(*, parallel: bool = USE_PARALLELISM) -> SQIBeamKernel:
    global _KERNEL
    if _KERNEL is None:
        _KERNEL = SQIBeamKernel(parallel=bool(parallel))
    return _KERNEL


class _KernelProxy:
    def __getattr__(self, name: str):
        return getattr(get_kernel(), name)


# Back-compat: callers that expect a module-level kernel can use KERNEL.* lazily
KERNEL = _KernelProxy()


# ──────────────────────────────────────────────
# Functional implementation (backward compat)
# ──────────────────────────────────────────────
def process_beams(beams: List["Beam"]) -> List["Beam"]:
    # Lazy init (and uses module constant for default parallelism)
    return get_kernel(parallel=USE_PARALLELISM).process_batch(beams)
