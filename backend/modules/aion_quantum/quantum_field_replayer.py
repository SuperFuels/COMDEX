# backend/modules/aion_quantum/quantum_field_replayer.py
"""
Tessaris Quantum Field Replayer (QFR)
Phase 12 - Replay recorded resonance meshes (.qrm.gz) into live feedback.

- Loads a .qrm.gz file from data/resonance_mesh/
- Reconstructs frames (Φ, ν, ψ, t) with tolerant parsing
- Replays at real-time or accelerated speed
- Emits photon patterns (optional) and logs feedback to JSONL

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import argparse
import gzip
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timezone

MESH_DIR = Path("data/resonance_mesh")
PHOTO_DIR = Path("data/qqc_field/photo_output")
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

QFR_FEEDBACK = Path("data/qfr_feedback.jsonl")
QFR_FEEDBACK.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_qrm(path: Path) -> Dict[str, Any]:
    """Load a .qrm.gz file and return decoded JSON."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _coalesce(*candidates):
    for c in candidates:
        if c is not None:
            return c
    return None

def detect_frames(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detects and reconstructs frame lists from .qrm.gz structures.
    Supports flattened dict-of-lists style (Φ_coh[], ψ2[], ν_centroid[], t[], stability[]).
    """
    # Case 1 - top-level list
    if isinstance(payload, list):
        return payload

    # Case 2 - dict with expected top-level keys
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], dict):
            data = payload["data"]
            # ✅ reconstruct frames by zipping dict-of-lists
            keys = list(data.keys())
            length = len(data[keys[0]]) if keys else 0
            frames = []
            for i in range(length):
                frame = {k: data[k][i] for k in keys if i < len(data[k])}
                frames.append(frame)
            print(f"✅ Reconstructed {len(frames)} frames from dict-of-lists format ({keys})")
            return frames

        # fallback for nested common formats
        for key in ("frames", "mesh", "samples"):
            if key in payload and isinstance(payload[key], list):
                print(f"✅ Detected {len(payload[key])} frames from '{key}' key")
                return payload[key]

    raise ValueError(
        f"Unrecognized QRM structure: expected dict-of-lists under 'data'. Got keys={list(payload.keys())}"
    )

def summarize_frame(frame: Dict[str, Any]) -> Tuple[float, float, Dict[str, Any], Dict[str, Any], Dict[str, Any], str]:
    """
    Return (phi_coherence, stability, phi, nu, psi, ts)
    with defensive defaults.
    """
    phi = _coalesce(
        frame.get("phi"),
        frame.get("Phi"),
        frame.get("delta_phi"),
        {}
    ) or {}
    nu = _coalesce(
        frame.get("nu"),
        frame.get("delta_nu"),
        {}
    ) or {}
    psi = _coalesce(
        frame.get("psi"),
        frame.get("pattern"),
        {}
    ) or {}

    # Key variants for coherence
    phi_coh = _coalesce(
        phi.get("Φ_coherence"),
        phi.get("phi_coherence"),
        phi.get("coherence"),
        0.0
    )
    stability = float(_coalesce(frame.get("stability"), psi.get("stability"), 1.0))

    # Timestamp best-effort
    ts = _coalesce(frame.get("timestamp"), frame.get("time"), _now_iso())

    # Normalize ψ if missing -> derive a neutral standing wave (~1.0)
    if not psi:
        psi = {
            "Δψ1": 1.0,
            "Δψ2": 1.0,
            "Δψ3": 1.0,
            "phase_shift": float(_coalesce(frame.get("phase"), 0.0)),
            "stability": stability,
        }

    return float(phi_coh), stability, phi, nu, psi, ts


def emit_photon(psi: Dict[str, Any], ts: str) -> Optional[Path]:
    """
    Emit a photon pattern file (.photo) compatible with the QQC Photon Interface.
    """
    try:
        payload = {
            "timestamp": ts,
            "pattern": psi,
            "source": "AION_QFR",
        }
        fname = f"photon_{ts}.photo"
        out = PHOTO_DIR / fname
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return out
    except Exception:
        return None


def log_feedback(ts: str, phi: Dict[str, Any], nu: Dict[str, Any], psi: Dict[str, Any], stability: float):
    record = {
        "timestamp": ts,
        "phi": phi,
        "nu": nu,
        "psi": psi,
        "stability": stability,
        "source": "AION_QFR",
    }
    with open(QFR_FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_latest_qrm() -> Optional[Path]:
    candidates = sorted(MESH_DIR.glob("*.qrm.gz"))
    return candidates[-1] if candidates else None


# ──────────────────────────────────────────────────────────────
# Player
# ──────────────────────────────────────────────────────────────
def replay_qrm(
    path: Path,
    fps: Optional[float] = None,
    speed: float = 1.0,
    emit_photons: bool = True,
    verbose: bool = True,
):
    """
    Replay the QRM mesh:
      - If fps provided: sleep ~1/fps / speed per frame
      - else if 'dt' in frames, we try to honor it scaled by 'speed'
      - otherwise default ~10 Hz / speed
    """
    payload = load_qrm(path)
    frames = detect_frames(payload)
    if verbose:
        print(f"🎞️  Starting Tessaris Quantum Field Replayer (QFR) ...")
        print(f"▶️  Replaying {path.name} (frames={len(frames)})")

    # Stats
    seen = 0
    t0 = time.time()
    for idx, frame in enumerate(frames):
        phi_coh, stability, phi, nu, psi, ts = summarize_frame(frame)

        # Display every N frames (or all if short)
        if verbose:
            if len(frames) <= 120 or idx % max(1, len(frames)//20) == 0:
                print(
                    f"t={idx:02d} Φ_coherence={phi_coh:.3f} stability={stability:.3f}"
                )

        # Emit photon file (optional)
        if emit_photons:
            emit_photon(psi, ts)

        # Feedback log for learning / analytics
        log_feedback(ts, phi, nu, psi, stability)

        # pacing
        if fps:
            dt = 1.0 / max(1e-6, fps * speed)
        else:
            # try honor embedded dt
            dt = float(frame.get("dt", 0.1)) / max(1e-6, speed)
        time.sleep(max(0.0, dt))
        seen += 1

    if verbose:
        dur = time.time() - t0
        print(f"🪶  Replay complete (frames={seen}, wall={dur:.1f}s)")


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
def main(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="Tessaris Quantum Field Replayer (QFR)")
    p.add_argument(
        "--file",
        "-f",
        type=str,
        help="Path to .qrm.gz (default: newest in data/resonance_mesh/)",
    )
    p.add_argument("--fps", type=float, default=None, help="Playback FPS (overrides dt)")
    p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed multiplier (e.g., 2.0 = 2x faster)",
    )
    p.add_argument(
        "--no-photons",
        action="store_true",
        help="Disable photon emission (.photo files)",
    )
    p.add_argument("--quiet", action="store_true", help="Reduce console output")

    args = p.parse_args(argv)

    if args.file:
        qrm_path = Path(args.file)
        if not qrm_path.exists():
            print(f"❌ QRM not found: {qrm_path}")
            sys.exit(1)
    else:
        qrm_path = find_latest_qrm()
        if not qrm_path:
            print("❌ No .qrm.gz found in data/resonance_mesh/")
            sys.exit(1)

    replay_qrm(
        qrm_path,
        fps=args.fps,
        speed=args.speed,
        emit_photons=not args.no_photons,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()