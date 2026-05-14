#!/usr/bin/env python3
"""
ElevenLabs TTS helper for Phase 6 demo.

Writes an MP3 narration (DATA_ROOT aware).
Non-fatal if ELEVENLABS_API_KEY is missing.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import urllib.request


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or default).strip()


def _post_tts_mp3(
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.35,
    similarity_boost: float = 0.75,
    style: float = 0.2,
    use_speaker_boost: bool = True,
    timeout_s: int = 60,
) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        },
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def build_phase6_narration(demo_summary: Dict[str, Any]) -> str:
    # Keep it short, screen-record friendly.
    # You can tweak tone later.
    parts = []
    parts.append("Phase six demo complete. Here is the audit summary.")
    session = demo_summary.get("session") or ""
    if session:
        parts.append(f"Session: {session}.")
    parts.append("We proved tests green, ran C E E playback, and generated read-only predictive telemetry.")

    # counts
    n_turns = demo_summary.get("n_turns")
    n_denies = demo_summary.get("n_denies")
    n_corr = demo_summary.get("n_corrections")
    n_forecasts = demo_summary.get("n_forecasts")
    n_misses = demo_summary.get("n_prediction_miss")
    n_risk = demo_summary.get("n_risk_awareness")

    def say_count(label: str, v: Any) -> Optional[str]:
        try:
            if v is None:
                return None
            return f"{label}: {int(v)}."
        except Exception:
            return None

    for s in [
        say_count("Turns", n_turns),
        say_count("Learning denials", n_denies),
        say_count("Corrections", n_corr),
        say_count("Forecast records", n_forecasts),
        say_count("Prediction miss events", n_misses),
        say_count("Risk awareness events", n_risk),
    ]:
        if s:
            parts.append(s)

    parts.append("A per-session rollup file was written: forecast report dot json.")
    parts.append("End of demo.")
    return " ".join(parts)


def main() -> int:
    api_key = _env("ELEVENLABS_API_KEY", "")
    voice_id = _env("ELEVENLABS_VOICE_ID", "C9fbwSpEaejywLWx722Z")  # your provided voice
    model_id = _env("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    root = _data_root()
    summary_path = root / "telemetry" / "demo_summary.json"
    out_path = root / "sessions" / "phase6_voiceover.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        print("[VOICE] Missing ELEVENLABS_API_KEY; skipping voice generation (non-fatal).")
        return 0

    demo_summary = _read_json(summary_path)
    text = build_phase6_narration(demo_summary)

    try:
        mp3 = _post_tts_mp3(
            api_key=api_key,
            voice_id=voice_id,
            text=text,
            model_id=model_id,
        )
        out_path.write_bytes(mp3)
        print(f"[VOICE] Wrote: {out_path}")
        return 0
    except Exception as e:
        print(f"[VOICE] Failed (non-fatal): {e}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())