# backend/tests/test_pgc.py
from backend.modules.photonlang.pgc import tokenize_glyphs, compile_photon

def test_basic_glyph_tokenize():
    toks = tokenize_glyphs("⊕⟲μπ")
    assert toks[0]["seq"] == "⊕⟲μπ"

def test_modulation_params():
    toks = tokenize_glyphs("⧖{freq=1.02, amp=1.01}")
    assert toks[0]["params"]["freq"] == 1.02
    assert toks[0]["params"]["amp"] == 1.01

def test_compile_ast():
    prog = compile_photon("⊕⟲")
    assert len(prog.stmts) >= 1