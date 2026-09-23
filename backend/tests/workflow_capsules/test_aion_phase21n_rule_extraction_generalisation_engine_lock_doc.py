from pathlib import Path


def test_phase21n_rule_extraction_generalisation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21n_rule_extraction_generalisation_engine_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21N: Rule Extraction and Generalisation Engine Lock" in text
    assert "remembered\\_outcome \\rightarrow extracted\\_rule" in text
    assert "prefer\\_reward\\_action" in text
    assert "avoid\\_penalty\\_action" in text
    assert "generalisation\\_score" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21N-RULE-EXTRACTION-GENERALISATION-ENGINE-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
