from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.collapse.collapse_trace_exporter import export_collapse_trace

# 🧠 Dummy glyphs
dummy_glyphs = [
    {"id": "g1", "label": "A = B", "entangled_with": ["g2"]},
    {"id": "g2", "label": "B = C", "entangled_with": ["g1"]},
]

# ✅ Create EntangledWave from dummy glyphs
entangled = EntangledWave.from_glyphs(dummy_glyphs)

# ✅ Wrap in WaveState
wave = WaveState(entangled_wave=entangled)

# 💡 Inject fake QWave metadata
wave.qwave = {
    "beams": [{"id": "b1", "source": "g1", "target": "g2"}],
    "modulation_strategy": "test_modulation",
    "multiverse_frame": "test_frame"
}

# 📝 Export trace
wave_dict = wave.to_dict()
path = export_collapse_trace(wave_dict)

print(f"✅ Exported test QWave trace: {path}")