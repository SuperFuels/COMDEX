from __future__ import annotations

import base64
import json
from pathlib import Path

from backend.modules.aion_voice.voice_worker_bridge import synthesize_with_worker, transcribe_with_worker


def main() -> int:
    out_dir = Path(".runtime/voice_runtime_tests/o22d")
    out_dir.mkdir(parents=True, exist_ok=True)

    wav_path = out_dir / "worker_bridge_tts.wav"
    manifest_path = out_dir / "worker_bridge_manifest.json"

    tts = synthesize_with_worker(
        "AION local voice worker bridge test. This is a generic runtime check.",
        voice="af_heart",
        sample_rate=24000,
    )

    if not tts.ok:
        print(json.dumps({
            "ok": False,
            "stage": "tts",
            "payload": tts.payload,
        }, indent=2))
        return 1

    audio_b64 = tts.payload.get("audio_base64") or ""
    audio_bytes = base64.b64decode(audio_b64)
    wav_path.write_bytes(audio_bytes)

    stt = transcribe_with_worker(audio_bytes, filename="worker_bridge_tts.wav")

    if not stt.ok:
        print(json.dumps({
            "ok": False,
            "stage": "stt",
            "payload": stt.payload,
        }, indent=2))
        return 1

    manifest = {
        "ok": True,
        "phase": "O22D",
        "tts_provider": tts.payload.get("provider"),
        "stt_provider": stt.payload.get("provider"),
        "voice": tts.payload.get("voice"),
        "sample_rate": tts.payload.get("sample_rate"),
        "wav_path": str(wav_path),
        "wav_size_bytes": len(audio_bytes),
        "transcript": stt.payload.get("text"),
        "language": stt.payload.get("language"),
        "business_context_hardcoded": False,
        "packaging_pattern": "main_backend_calls_isolated_or_bundled_voice_worker",
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
