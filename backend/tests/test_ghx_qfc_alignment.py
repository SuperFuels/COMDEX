# -*- coding: utf-8 -*-
"""
GHX/QFC Overlay Alignment Validation - Tessaris / CFE v0.3.x
Replays GWV session and compares overlay frames with telemetry.

Enhancements (v0.3.2):
    * Adds fallback to mock telemetry logs (/telemetry/logs/mock_telem.json)
    * Maintains compatibility with both legacy and modern TelemetryHandler APIs
    * Writes Δt / Δcoherence summary to telemetry/reports/
"""
import json
import os
import sys
from backend.modules.glyphwave.telemetry_handler import TelemetryHandler
from backend.modules.glyphwave.wavescope import WaveScope


def _find_telemetry_entry(telem: TelemetryHandler, beam_id: str):
    """
    Compatibility helper for old 'lookup' -> new buffer-based telemetry.
    """
    # Try modern interface first
    if hasattr(telem, "get_entry_by_id"):
        return telem.get_entry_by_id(beam_id)

    # Fallback: scan buffer or internal records
    if hasattr(telem, "records"):
        for rec in telem.records:
            if rec.get("beam_id") == beam_id:
                return rec
    elif hasattr(telem, "buffer"):
        for rec in telem.buffer:
            if rec.get("beam_id") == beam_id:
                return rec
    return None


def validate_overlay(source_path: str):
    telem = TelemetryHandler()
    scope = WaveScope()

    if not os.path.exists(source_path):
        print(f"⚠️ Source GWV file not found: {source_path}")
        return

    with open(source_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    # 🧩 Load mock telemetry as fallback
    mock_telem_path = "/workspaces/COMDEX/backend/telemetry/logs/mock_telem.json"
    mock_data = []
    if os.path.exists(mock_telem_path):
        with open(mock_telem_path, "r", encoding="utf-8") as tf:
            mock_data = json.load(tf)

    results = []
    for frame in session.get("frames", []):
        beam_id = frame.get("beam_id")

        # Try live telemetry first
        tele_entry = _find_telemetry_entry(telem, beam_id)

        # Fallback to mock telemetry if needed
        if not tele_entry and mock_data:
            tele_entry = next((m for m in mock_data if m["beam_id"] == beam_id), None)

        if not tele_entry:
            continue

        dt = abs(frame["timestamp"] - tele_entry.get("timestamp", 0))
        dc = abs(frame["coherence"] - tele_entry.get("coherence", 0))
        results.append({"beam_id": beam_id, "dt": dt, "d_coherence": dc})

    out = "/workspaces/COMDEX/backend/telemetry/reports/GHX_QFC_alignment_validation.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    if results:
        avg_dt = sum(r["dt"] for r in results) / len(results)
        avg_dc = sum(r["d_coherence"] for r in results) / len(results)
        print(f"✅ Overlay validated: Δt≈{avg_dt:.3f}s, Δcoherence≈{avg_dc:.3f} -> {out}")
    else:
        print(f"⚠️ No matching telemetry entries found for frames in {source_path}")


if __name__ == "__main__":
    src = os.getenv(
        "GWV_SOURCE",
        "/workspaces/COMDEX/backend/telemetry/last_session.gwv"
    )
    validate_overlay(src)