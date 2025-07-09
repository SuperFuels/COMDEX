# File: backend/tests/test_trigger_engine.py

from backend.modules.dna_chain.trigger_engine import check_glyph_triggers

def test_trigger_check():
    print("🧠 Running trigger engine on sample container...")
    check_glyph_triggers("test_trigger")

if __name__ == "__main__":
    test_trigger_check()