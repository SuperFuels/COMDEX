# File: backend/modules/glyphnet/glyphwave_encoder.py

import wave
import numpy as np
from typing import List, Union, Sequence, Dict, Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

# Mapping glyphs to frequencies (Hz)
GLYPH_TONE_MAP: Dict[str, float] = {
    "✦": 440.0,    # A4
    "⚛": 523.3,    # C5
    "🧠": 659.3,    # E5
    "🜂": 783.9,    # G5
    "↔": 880.0,    # A5
    "🪞": 987.8,   # B5
    "🧬": 1046.5,  # C6
    "⌘": 1174.7,  # D6
    "∅": 0.0,      # explicit silence
    "_": 300.0,    # fallback
}

SAMPLE_RATE = 44100
DURATION = 0.2  # seconds per glyph
DEFAULT_VOLUME = 1.0


# ──────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────
def register_glyph_tone(glyph: str, frequency: float) -> None:
    GLYPH_TONE_MAP[glyph] = frequency
    logger.info(f"[GlyphWave] Registered tone for glyph '{glyph}' at {frequency} Hz")


# ──────────────────────────────────────────────
# Encoder
# ──────────────────────────────────────────────
def generate_tone(freq: float, duration: float = DURATION, volume: float = DEFAULT_VOLUME) -> np.ndarray:
    if freq <= 0.0:  # treat as silence
        return np.zeros(int(SAMPLE_RATE * duration), dtype=np.int16)
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = np.sin(freq * t * 2 * np.pi) * volume
    return (tone * 32767).astype(np.int16)


def glyphs_to_waveform(
    glyphs: Union[str, List[str]],
    stereo: bool = False,
    volume: float = DEFAULT_VOLUME
) -> bytes:
    if isinstance(glyphs, str):
        glyphs = list(glyphs)

    tones = []
    for glyph in glyphs:
        freq = GLYPH_TONE_MAP.get(glyph, GLYPH_TONE_MAP["_"])
        if glyph not in GLYPH_TONE_MAP:
            logger.warning(f"[GlyphWave] ⚠️ Unmapped glyph '{glyph}', using fallback tone.")
        tones.append(generate_tone(freq, volume=volume))

    audio = np.concatenate(tones)
    if stereo:
        audio = np.column_stack((audio, audio)).ravel()

    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(2 if stereo else 1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()


def save_wavefile(path: str, glyphs: Union[str, List[str]], stereo: bool = False, volume: float = DEFAULT_VOLUME) -> None:
    waveform = glyphs_to_waveform(glyphs, stereo=stereo, volume=volume)
    with open(path, "wb") as f:
        f.write(waveform)
    logger.info(f"[GlyphWave] Saved waveform to {path} (stereo={stereo}, volume={volume})")


def glyph_phrase_to_waveform(
    phrase: Sequence[Union[str, Dict[str, Union[str, float]]]],
    default_duration: float = DURATION,
    stereo: bool = False,
    volume: float = DEFAULT_VOLUME,
    rest_symbol: str = "-"
) -> bytes:
    tones: List[np.ndarray] = []
    for item in phrase:
        if isinstance(item, dict):
            glyph = item.get("glyph")
            duration = item.get("duration", default_duration)
            vol = item.get("volume", volume)
        else:
            glyph, duration, vol = item, default_duration, volume

        if glyph == rest_symbol or glyph == "∅":
            tones.append(generate_tone(0.0, duration=duration, volume=0.0))
        else:
            freq = GLYPH_TONE_MAP.get(glyph, GLYPH_TONE_MAP["_"])
            tones.append(generate_tone(freq, duration=duration, volume=vol))

    audio = np.concatenate(tones)
    if stereo:
        audio = np.column_stack((audio, audio)).ravel()

    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(2 if stereo else 1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()


# ──────────────────────────────────────────────
# Decoder
# ──────────────────────────────────────────────
def decode_waveform_to_glyphs(
    wav_bytes: bytes,
    segment_duration: float = DURATION,
    tolerance: float = 20.0
) -> List[str]:
    """
    Decode a WAV file back into glyphs by analyzing frequency peaks.

    Args:
        wav_bytes: WAV audio as bytes.
        segment_duration: Duration of each glyph segment (sec).
        tolerance: Frequency tolerance in Hz for matching.

    Returns:
        List of decoded glyphs.
    """
    with BytesIO(wav_bytes) as buffer:
        with wave.open(buffer, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()

            raw = wf.readframes(n_frames)
            dtype = np.int16 if sampwidth == 2 else np.int8
            audio = np.frombuffer(raw, dtype=dtype)

            if n_channels == 2:  # stereo -> take one channel
                audio = audio[::2]

    segment_len = int(framerate * segment_duration)
    glyphs: List[str] = []

    for i in range(0, len(audio), segment_len):
        segment = audio[i:i + segment_len]
        if len(segment) == 0:
            break

        # FFT
        fft = np.fft.fft(segment)
        freqs = np.fft.fftfreq(len(fft), 1 / framerate)
        magnitude = np.abs(fft)

        peak_index = np.argmax(magnitude[: len(magnitude) // 2])
        peak_freq = abs(freqs[peak_index])

        if peak_freq < 1.0:
            glyphs.append("∅")
            continue

        # Find nearest glyph frequency
        nearest = min(GLYPH_TONE_MAP.items(), key=lambda kv: abs(kv[1] - peak_freq))
        glyph, freq = nearest
        if abs(freq - peak_freq) <= tolerance:
            glyphs.append(glyph)
        else:
            glyphs.append("_")  # fallback

    return glyphs