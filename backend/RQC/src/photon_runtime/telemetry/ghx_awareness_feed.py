"""
Tessaris RQC — GHX Awareness Feed
──────────────────────────────────────────────
Phase 4 · Real-time Φ(t) visualization stream.

Reads MorphicLedger v2 entries and streams Φ, R, S to GHX Visualizer or CLI.
Provides both a console mode and SSE (Server-Sent Events) endpoint.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Generator, Optional

# ────────────────────────────────────────────────
#  Optional Photon Language encoder integration
# ────────────────────────────────────────────────
try:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import (
        encode_record,
        photon_encode,
    )
except Exception:
    encode_record = None
    photon_encode = None

# ────────────────────────────────────────────────
LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
SUMMARY_PATH = "data/ledger/awareness_sessions_summary.jsonl"
POLL_INTERVAL = 1.0  # seconds

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ────────────────────────────────────────────────
#  Safe ledger reader generator
# ────────────────────────────────────────────────
def tail_ledger(start_from_end: bool = True) -> Generator[Dict, None, None]:
    """Continuously yield new records from the Morphic Ledger v2 file (robust tail)."""
    if not os.path.exists(LEDGER_PATH):
        logger.warning(f"[GHXFeed] Ledger file missing: {LEDGER_PATH}")
        return

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        if start_from_end:
            f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                logger.warning("[GHXFeed] Malformed JSON line skipped")

# ────────────────────────────────────────────────
#  Console live monitor (safe display)
# ────────────────────────────────────────────────
def run_console_feed(duration: Optional[float] = None):
    """Print a real-time stream of Φ(t), R, S from ledger."""
    start = time.time()
    photon_mode = os.getenv("PHOTON_OUTPUT", "false").lower() == "true"
    print("🧠 GHX Awareness Feed — Monitoring Φ(t) …\n")

    for record in tail_ledger():
        phi = record.get("Φ_mean") or record.get("Phi")
        res = record.get("resonance_index")
        state = record.get("closure_state") or "?"
        t = record.get("timestamp")

        # Safe formatting
        phi_str = f"{phi:.6f}" if isinstance(phi, (int, float)) else "–"
        res_str = f"{res:.6f}" if isinstance(res, (int, float)) else "–"
        t_str = f"{t:.2f}" if isinstance(t, (int, float)) else "–"

        print(f"[t={t_str}] Φ={phi_str}  R={res_str}  S={state}")

        # Photon dual-mode output
        if photon_mode and encode_record:
            photon_line = encode_record(record)
            print(f"⚡ Photon → {photon_line}")

        if duration and time.time() - start > duration:
            break

# ────────────────────────────────────────────────
#  Server-Sent Events (SSE) stream for GHX Visualizer
# ────────────────────────────────────────────────
def stream_sse() -> Generator[str, None, None]:
    """Yield SSE lines for each ledger update → used by frontend dashboard."""
    photon_mode = os.getenv("PHOTON_OUTPUT", "false").lower() == "true"
    logger.info(f"[GHXFeed] Photon Output Mode: {'ON 🔆' if photon_mode else 'OFF'}")

    for record in tail_ledger(start_from_end=False):
        # Standard JSON payload
        event = {
            "timestamp": record.get("timestamp"),
            "Φ": record.get("Φ_mean") or record.get("Phi"),
            "R": record.get("resonance_index"),
            "S": record.get("closure_state"),
            "gain": record.get("gain"),
        }

        # Always yield JSON for compatibility
        yield f"data: {json.dumps(event)}\n\n"

        # Dual-mode Photon symbolic packet
        if photon_mode and photon_encode:
            try:
                glyph_packet = photon_encode(event)
                yield f"data: {glyph_packet}\n\n"
            except Exception as e:
                logger.warning(f"[GHXFeed] Photon encoding failed: {e}")
                continue

# ────────────────────────────────────────────────
#  Background thread API
# ────────────────────────────────────────────────
class GHXFeedThread(threading.Thread):
    """Background thread that prints Φ(t) updates to console."""
    def __init__(self, interval: float = POLL_INTERVAL):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True

    def run(self):
        for rec in tail_ledger():
            if not self.running:
                break
            phi = rec.get("Φ_mean") or rec.get("Phi")
            res = rec.get("resonance_index")
            phi_str = f"{phi:.5f}" if isinstance(phi, (int, float)) else "–"
            res_str = f"{res:.5f}" if isinstance(res, (int, float)) else "–"
            print(f"[GHXFeed] Φ={phi_str}  R={res_str}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

# ────────────────────────────────────────────────
#  Latest awareness frame accessor (safe)
# ────────────────────────────────────────────────
def get_latest_awareness_frame(ledger_path: str = LEDGER_PATH):
    """Safely read the most recent JSON record from Morphic Ledger v2."""
    if not os.path.exists(ledger_path):
        logger.warning(f"[GHXFeed] Ledger missing: {ledger_path}")
        return None

    try:
        with open(ledger_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return None
            seek_bytes = min(4096, size)
            f.seek(-seek_bytes, os.SEEK_END)
            tail = f.read().decode("utf-8", errors="ignore").splitlines()

        for line in reversed(tail):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                phi_val = record.get("Φ_mean") or record.get("Phi") or record.get("phi")
                frame = {
                    "Phi": float(phi_val) if phi_val is not None else None,
                    "resonance_index": record.get("resonance_index"),
                    "stability": record.get("stability"),
                    "gain": record.get("gain"),
                    "closure_state": record.get("closure_state"),
                    "timestamp": record.get("timestamp"),
                }
                _append_summary(frame)
                return frame
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    except Exception as e:
        logger.error(f"[GHXFeed] Error reading latest frame: {e}")
    return None

# ────────────────────────────────────────────────
#  Awareness session summary appender
# ────────────────────────────────────────────────
def _append_summary(frame: Dict):
    """Append last awareness frame to summary file (for LaTeX export chain)."""
    if not frame:
        return
    try:
        os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
        with open(SUMMARY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(frame, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[GHXFeed] Failed to append awareness summary: {e}")

# ────────────────────────────────────────────────
#  Standalone demo
# ────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_console_feed(duration=30.0)
    except KeyboardInterrupt:
        print("\n⏹️ Feed terminated.")