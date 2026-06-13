from pathlib import Path


def test_phase22d8_sqi_failure_patch_selector_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d8_full_chess_sqi_failure_patch_selector_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.8: SQI Failure Patch Selector Kernel Lock" in text
    assert "SQI selector patched against level 2 failure modes" in text
    assert "full_chess_sqi_failure_patch_selector_kernel.py" in text
    assert "repetition loops" in text
    assert "king shuffling" in text
    assert "negative SQI spiral" in text
    assert "22E.1 -- Positional Strategy Features" in text
    assert "Lock ID: AION-PHASE22D8-SQI-FAILURE-PATCH-SELECTOR-KERNEL-LOCK" in text
