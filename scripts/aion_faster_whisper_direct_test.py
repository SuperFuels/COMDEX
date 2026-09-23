from __future__ import annotations

from pathlib import Path
import json
import time


def main() -> int:
    audio_path = Path(".runtime/voice_runtime_tests/o22b/kokoro_direct_test.wav")
    out_dir = Path(".runtime/voice_runtime_tests/o22c")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "faster_whisper_direct_manifest.json"

    if not audio_path.exists():
        print(json.dumps({
            "ok": False,
            "stage": "input",
            "error": f"Missing input audio: {audio_path}",
        }, indent=2))
        return 1

    started = time.time()

    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "stage": "import",
            "error": repr(exc),
        }, indent=2))
        return 1

    try:
        model_name = "base"
        model = WhisperModel(
            model_name,
            device="auto",
            compute_type="int8",
        )

        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=False,
        )

        segments = []
        transcript_parts = []

        for segment in segments_iter:
            text = (segment.text or "").strip()
            if text:
                transcript_parts.append(text)
            segments.append({
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": text,
            })

        transcript = " ".join(transcript_parts).strip()

        if not transcript:
            raise RuntimeError("faster-whisper returned an empty transcript.")

        manifest = {
            "ok": True,
            "phase": "O22C",
            "provider": "faster-whisper",
            "model": model_name,
            "device": "auto",
            "compute_type": "int8",
            "input_audio": str(audio_path),
            "language": getattr(info, "language", None),
            "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
            "duration": round(float(getattr(info, "duration", 0.0)), 3),
            "transcript": transcript,
            "segments": segments,
            "elapsed_seconds": round(time.time() - started, 3),
            "business_context_hardcoded": False,
            "text_kind": "generic_runtime_check",
        }

        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0

    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "stage": "transcription",
            "error": repr(exc),
            "input_audio": str(audio_path),
            "manifest_path": str(manifest_path),
        }, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
