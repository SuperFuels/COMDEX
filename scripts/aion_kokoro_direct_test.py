from __future__ import annotations

from pathlib import Path
import json
import time


def first_present(*values):
    """
    Return first value that is not None.
    Do NOT use Python `or` here because torch tensors cannot be truth-tested.
    """
    for value in values:
        if value is not None:
            return value
    return None


def extract_kokoro_item(item):
    """
    Kokoro versions may yield:
      - tuple/list: (graphemes, phonemes, audio)
      - object with .graphemes/.phonemes/.audio
      - dict with graphemes/phonemes/audio
    """
    if isinstance(item, (tuple, list)) and len(item) >= 3:
        return item[0], item[1], item[2]

    if isinstance(item, dict):
        audio = first_present(item.get("audio"), item.get("wav"), item.get("samples"))
        gs = first_present(item.get("graphemes"), item.get("text"), item.get("gs"), "")
        ps = first_present(item.get("phonemes"), item.get("ps"), "")
        return gs, ps, audio

    audio = first_present(
        getattr(item, "audio", None),
        getattr(item, "wav", None),
        getattr(item, "samples", None),
    )
    gs = first_present(
        getattr(item, "graphemes", None),
        getattr(item, "text", None),
        getattr(item, "gs", None),
        "",
    )
    ps = first_present(
        getattr(item, "phonemes", None),
        getattr(item, "ps", None),
        "",
    )

    return gs, ps, audio


def audio_len(audio) -> int:
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


def to_numpy_audio(audio):
    if audio is None:
        return None

    try:
        import torch
        if isinstance(audio, torch.Tensor):
            return audio.detach().cpu().numpy()
    except Exception:
        pass

    return audio


def main() -> int:
    out_dir = Path(".runtime/voice_runtime_tests/o22b")
    out_dir.mkdir(parents=True, exist_ok=True)

    wav_path = out_dir / "kokoro_direct_test.wav"
    manifest_path = out_dir / "kokoro_direct_test_manifest.json"
    debug_path = out_dir / "kokoro_direct_debug.json"

    text = (
        "AION local voice runtime test. "
        "This is a generic business onboarding voice check."
    )

    started = time.time()

    try:
        from kokoro import KPipeline
        import soundfile as sf
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "stage": "import",
            "error": repr(exc),
        }, indent=2))
        return 1

    debug_items = []

    try:
        pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        generator = pipeline(text, voice="af_heart")

        audio_chunks = []
        graphemes = []
        phonemes = []

        for index, item in enumerate(generator):
            gs, ps, audio = extract_kokoro_item(item)
            audio_np = to_numpy_audio(audio)

            item_info = {
                "index": index,
                "type": type(item).__name__,
                "repr_preview": repr(item)[:500],
                "audio_type": type(audio).__name__ if audio is not None else None,
                "audio_len": audio_len(audio),
                "numpy_audio_type": type(audio_np).__name__ if audio_np is not None else None,
                "numpy_audio_len": audio_len(audio_np),
                "graphemes_preview": str(gs)[:160],
                "phonemes_preview": str(ps)[:160],
            }
            debug_items.append(item_info)

            if audio_np is None or audio_len(audio_np) <= 0:
                continue

            graphemes.append(str(gs))
            phonemes.append(str(ps))
            audio_chunks.append(audio_np)

        debug_path.write_text(json.dumps(debug_items, indent=2), encoding="utf-8")

        if not audio_chunks:
            raise RuntimeError(
                "Kokoro returned no extractable audio chunks. "
                f"Debug written to {debug_path}"
            )

        if len(audio_chunks) == 1:
            final_audio = audio_chunks[0]
        else:
            import numpy as np
            final_audio = np.concatenate(audio_chunks)

        sf.write(str(wav_path), final_audio, 24000)

        size = wav_path.stat().st_size
        if size < 1000:
            raise RuntimeError(f"Generated WAV is too small: {size} bytes")

        manifest = {
            "ok": True,
            "phase": "O22B.3",
            "provider": "kokoro",
            "voice": "af_heart",
            "sample_rate": 24000,
            "output_path": str(wav_path),
            "debug_path": str(debug_path),
            "size_bytes": size,
            "elapsed_seconds": round(time.time() - started, 3),
            "business_context_hardcoded": False,
            "text_kind": "generic_runtime_check",
            "audio_chunks": len(audio_chunks),
            "grapheme_chunks": len(graphemes),
            "phoneme_chunks": len(phonemes),
        }

        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0

    except Exception as exc:
        debug_path.write_text(json.dumps(debug_items, indent=2), encoding="utf-8")
        print(json.dumps({
            "ok": False,
            "stage": "synthesis",
            "error": repr(exc),
            "output_path": str(wav_path),
            "debug_path": str(debug_path),
        }, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
