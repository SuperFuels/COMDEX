# backend/modules/glyphnet/glyphwave_encoder.py

import wave
import numpy as np
from typing import List, Union
from io import BytesIO

# Mapping glyphs to frequencies (Hz)
GLYPH_TONE_MAP = {
    "✦": 440.0,   # A4
    "⚛": 523.3,   # C5
    "🧠": 659.3,   # E5
    "🜂": 783.9,   # G5
    "↔": 880.0,   # A5
    "🪞": 987.8,   # B5
    "🧬": 1046.5,  # C6
    "⌘": 1174.7,  # D6
    # fallback
    "_": 300.0,
}

SAMPLE_RATE = 44100
DURATION = 0.2  # seconds per glyph

def generate_tone(freq: float, duration: float = DURATION) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = np.sin(freq * t * 2 * np.pi)
    return (tone * 32767).astype(np.int16)

def glyphs_to_waveform(glyphs: Union[str, List[str]]) -> bytes:
    if isinstance(glyphs, str):
        glyphs = list(glyphs)

    tones = []
    for glyph in glyphs:
        freq = GLYPH_TONE_MAP.get(glyph, GLYPH_TONE_MAP["_"])
        tones.append(generate_tone(freq))

    audio = np.concatenate(tones)
    with BytesIO() as buffer:
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buffer.getvalue()

def save_wavefile(path: str, glyphs: Union[str, List[str]]):
    waveform = glyphs_to_waveform(glyphs)
    with open(path, 'wb') as f:
        f.write(waveform)