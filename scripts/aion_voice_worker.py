from __future__ import annotations


# AION O23H: apply no-hidden-downloads policy before provider imports.
try:
    from backend.modules.aion_voice.voice_download_policy import apply_voice_download_policy
    apply_voice_download_policy()
except Exception:
    pass

import argparse
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_RATE = 24000
DEFAULT_KOKORO_REPO = "hexgrad/Kokoro-82M"
DEFAULT_KOKORO_VOICE = "af_heart"
DEFAULT_WHISPER_MODEL = "base"

_KOKORO_PIPELINE = None
_KOKORO_PIPELINE_KEY = None
_WHISPER_MODEL = None
_WHISPER_MODEL_KEY = None


def get_whisper_model(model_name: str, device: str, compute_type: str):
    """Return the process-local Whisper model, loading it only when settings change."""
    global _WHISPER_MODEL, _WHISPER_MODEL_KEY
    key = (str(model_name), str(device), str(compute_type))
    if _WHISPER_MODEL is None or _WHISPER_MODEL_KEY != key:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel(key[0], device=key[1], compute_type=key[2])
        _WHISPER_MODEL_KEY = key
    return _WHISPER_MODEL



def aion_o23i_bundle_probe() -> int:
    import importlib.util
    import json
    import os
    import sys
    from pathlib import Path

    required_env_paths = {
        "AION_VOICE_BUNDLE_ROOT": os.environ.get("AION_VOICE_BUNDLE_ROOT", ""),
        "AION_KOKORO_MODEL_PATH": os.environ.get("AION_KOKORO_MODEL_PATH", ""),
        "AION_KOKORO_CONFIG_PATH": os.environ.get("AION_KOKORO_CONFIG_PATH", ""),
        "AION_KOKORO_VOICE_PATH": os.environ.get("AION_KOKORO_VOICE_PATH", ""),
        "AION_SPACY_MODEL_PATH": os.environ.get("AION_SPACY_MODEL_PATH", ""),
        "AION_WHISPER_MODEL_PATH": os.environ.get("AION_WHISPER_MODEL_PATH", ""),
    }

    required_imports = [
        "kokoro",
        "soundfile",
        "faster_whisper",
        "ctranslate2",
        "av",
        "torch",
        "spacy",
        "numpy",
    ]

    imports = {}
    for name in required_imports:
        spec = importlib.util.find_spec(name)
        imports[name] = {
            "found": spec is not None,
            "origin": getattr(spec, "origin", None) if spec else None,
        }

    paths = {}
    for key, raw in required_env_paths.items():
        path = Path(raw) if raw else None
        paths[key] = {
            "path": raw,
            "exists": bool(path and path.exists()),
            "is_dir": bool(path and path.is_dir()),
            "is_file": bool(path and path.is_file()),
        }

    offline_env = {
        "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE", ""),
        "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE", ""),
        "HF_DATASETS_OFFLINE": os.environ.get("HF_DATASETS_OFFLINE", ""),
        "AION_VOICE_NO_HIDDEN_DOWNLOADS": os.environ.get("AION_VOICE_NO_HIDDEN_DOWNLOADS", ""),
        "AION_ELEVENLABS_ENABLED": os.environ.get("AION_ELEVENLABS_ENABLED", ""),
        "AION_BROWSER_SPEECH_FALLBACK_ENABLED": os.environ.get("AION_BROWSER_SPEECH_FALLBACK_ENABLED", ""),
    }

    ok = (
        sys.version_info[:2] == (3, 12)
        and all(item["found"] for item in imports.values())
        and all(item["exists"] for item in paths.values())
        and offline_env["HF_HUB_OFFLINE"] == "1"
        and offline_env["TRANSFORMERS_OFFLINE"] == "1"
        and offline_env["HF_DATASETS_OFFLINE"] == "1"
        and offline_env["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
        and offline_env["AION_ELEVENLABS_ENABLED"] == "false"
        and offline_env["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"
    )

    print(json.dumps({
        "ok": ok,
        "phase": "O23I",
        "purpose": "prove_worker_runs_from_staged_bundle_paths",
        "python": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "imports": imports,
        "paths": paths,
        "offline_env": offline_env,
        "business_context_hardcoded": False,
    }, indent=2))

    return 0 if ok else 2



def _json_out(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _audio_len(audio) -> int:
    if audio is None:
        return 0
    try:
        return int(len(audio))
    except Exception:
        pass
    try:
        return int(audio.numel())
    except Exception:
        return 0


def _to_numpy_audio(audio):
    if audio is None:
        return None
    try:
        import torch
        if isinstance(audio, torch.Tensor):
            return audio.detach().cpu().numpy()
    except Exception:
        pass
    return audio


def _extract_kokoro_item(item):
    if isinstance(item, (tuple, list)) and len(item) >= 3:
        return item[0], item[1], item[2]

    if isinstance(item, dict):
        audio = _first_present(item.get("audio"), item.get("wav"), item.get("samples"))
        gs = _first_present(item.get("graphemes"), item.get("text"), item.get("gs"), "")
        ps = _first_present(item.get("phonemes"), item.get("ps"), "")
        return gs, ps, audio

    audio = _first_present(
        getattr(item, "audio", None),
        getattr(item, "wav", None),
        getattr(item, "samples", None),
    )
    gs = _first_present(
        getattr(item, "graphemes", None),
        getattr(item, "text", None),
        getattr(item, "gs", None),
        "",
    )
    ps = _first_present(
        getattr(item, "phonemes", None),
        getattr(item, "ps", None),
        "",
    )
    return gs, ps, audio


def run_tts(request: dict[str, Any]) -> dict[str, Any]:
    global _KOKORO_PIPELINE, _KOKORO_PIPELINE_KEY
    started = time.time()
    text = str(request.get("text") or "").strip()
    voice = str(request.get("voice") or DEFAULT_KOKORO_VOICE).strip()
    sample_rate = int(request.get("sample_rate") or DEFAULT_SAMPLE_RATE)
    repo_id = str(request.get("repo_id") or DEFAULT_KOKORO_REPO).strip()

    if not text:
        return {
            "ok": False,
            "provider": "kokoro",
            "stage": "validate",
            "error": "Missing text for TTS.",
        }

    try:
        from kokoro import KPipeline
        import numpy as np
        import soundfile as sf
    except Exception as exc:
        return {
            "ok": False,
            "provider": "kokoro",
            "stage": "import",
            "error": repr(exc),
        }

    try:
        pipeline_key = ("a", repo_id)
        if _KOKORO_PIPELINE is None or _KOKORO_PIPELINE_KEY != pipeline_key:
            _KOKORO_PIPELINE = KPipeline(lang_code="a", repo_id=repo_id)
            _KOKORO_PIPELINE_KEY = pipeline_key
        pipeline = _KOKORO_PIPELINE
        generator = pipeline(text, voice=voice)

        chunks = []
        debug_items = []

        for index, item in enumerate(generator):
            gs, ps, audio = _extract_kokoro_item(item)
            audio_np = _to_numpy_audio(audio)

            debug_items.append({
                "index": index,
                "item_type": type(item).__name__,
                "audio_type": type(audio).__name__ if audio is not None else None,
                "audio_len": _audio_len(audio),
                "numpy_audio_type": type(audio_np).__name__ if audio_np is not None else None,
                "numpy_audio_len": _audio_len(audio_np),
                "graphemes_preview": str(gs)[:160],
                "phonemes_preview": str(ps)[:160],
            })

            if audio_np is not None and _audio_len(audio_np) > 0:
                chunks.append(audio_np)

        if not chunks:
            return {
                "ok": False,
                "provider": "kokoro",
                "stage": "synthesis",
                "error": "Kokoro returned no extractable audio chunks.",
                "debug": debug_items,
            }

        audio = chunks[0] if len(chunks) == 1 else np.concatenate(chunks)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            sf.write(str(tmp_path), audio, sample_rate)
            wav_bytes = tmp_path.read_bytes()
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

        if len(wav_bytes) < 1000:
            return {
                "ok": False,
                "provider": "kokoro",
                "stage": "synthesis",
                "error": f"Generated WAV too small: {len(wav_bytes)} bytes.",
            }

        return {
            "ok": True,
            "provider": "kokoro",
            "voice": voice,
            "sample_rate": sample_rate,
            "mime_type": "audio/wav",
            "audio_base64": base64.b64encode(wav_bytes).decode("ascii"),
            "size_bytes": len(wav_bytes),
            "elapsed_seconds": round(time.time() - started, 3),
            "business_context_hardcoded": False,
            "debug": {
                "chunks": len(chunks),
                "items": debug_items,
            },
        }

    except Exception as exc:
        return {
            "ok": False,
            "provider": "kokoro",
            "stage": "synthesis",
            "error": repr(exc),
        }


def run_stt(request: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    audio_b64 = str(request.get("audio_base64") or "")
    filename = str(request.get("filename") or "audio.wav")
    model_name = str(request.get("model") or DEFAULT_WHISPER_MODEL)

    if not audio_b64:
        return {
            "ok": False,
            "provider": "faster-whisper",
            "stage": "validate",
            "error": "Missing audio_base64 for STT.",
        }

    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        return {
            "ok": False,
            "provider": "faster-whisper",
            "stage": "import",
            "error": repr(exc),
        }

    try:
        suffix = Path(filename).suffix or ".wav"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(base64.b64decode(audio_b64))

        try:
            model = get_whisper_model(
                model_name,
                device=str(request.get("device") or "auto"),
                compute_type=str(request.get("compute_type") or "int8"),
            )

            segments_iter, info = model.transcribe(
                str(tmp_path),
                beam_size=int(request.get("beam_size") or 5),
                vad_filter=bool(request.get("vad_filter") or False),
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

            return {
                "ok": True,
                "provider": "faster-whisper",
                "model": model_name,
                "language": getattr(info, "language", None),
                "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
                "duration": round(float(getattr(info, "duration", 0.0)), 3),
                "text": transcript,
                "segments": segments,
                "elapsed_seconds": round(time.time() - started, 3),
                "business_context_hardcoded": False,
            }
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

    except Exception as exc:
        return {
            "ok": False,
            "provider": "faster-whisper",
            "stage": "transcription",
            "error": repr(exc),
        }


def run_persistent_server() -> int:
    """Serve newline-delimited requests while retaining loaded voice models."""
    import sys

    for raw_line in sys.stdin:
        try:
            request = json.loads(raw_line)
            mode = str(request.get("mode") or request.get("operation") or "tts")
            if mode == "tts":
                payload = run_tts(request)
            elif mode == "stt":
                payload = run_stt(request)
            else:
                payload = {"ok": False, "stage": "mode", "error": f"Unsupported mode: {mode}"}
        except Exception as exc:
            payload = {"ok": False, "stage": "persistent_worker", "error": repr(exc)}

        print(json.dumps(payload, separators=(",", ":")), flush=True)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AION local voice worker")
    parser.add_argument("mode", choices=["tts", "stt", "serve"])
    parser.add_argument("--request", help="Path to JSON request")
    args = parser.parse_args()

    if args.mode == "serve":
        return run_persistent_server()

    if not args.request:
        return _json_out({"ok": False, "stage": "request", "error": "--request is required"})

    request_path = Path(args.request)
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _json_out({
            "ok": False,
            "stage": "request",
            "error": repr(exc),
            "request_path": str(request_path),
        })

    if args.mode == "tts":
        return _json_out(run_tts(request))

    if args.mode == "stt":
        return _json_out(run_stt(request))

    return _json_out({
        "ok": False,
        "stage": "mode",
        "error": f"Unsupported mode: {args.mode}",
    })


if len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "aion-o23i-bundle-probe":
    raise SystemExit(aion_o23i_bundle_probe())


if __name__ == "__main__":
    raise SystemExit(main())
