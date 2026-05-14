import random, string
from backend.modules.glyphos.glyph_synthesis_engine import generate_unique_symbol

def test_mass_uniqueness_scaling():
    words = [f"w{i}" for i in range(50000)]
    syms = [generate_unique_symbol(w, context="test", min_len=1, max_len=4) for w in words]
    assert len(syms) == len(set(syms))