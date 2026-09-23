from pathlib import Path


def test_phase22b26_full_chess_rating_benchmark_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b26_full_chess_rating_benchmark_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.26: Full Chess Rating Benchmark Kernel Lock" in text
    assert "benchmark\\_match\\_count" in text
    assert "completed\\_match\\_count" in text
    assert "win\\_count" in text
    assert "draw\\_count" in text
    assert "loss\\_count" in text
    assert "score\\_total" in text
    assert "score\\_percentage" in text
    assert "lowest\\_opponent\\_rating" in text
    assert "highest\\_opponent\\_rating" in text
    assert "estimated\\_rating\\_floor" in text
    assert "estimated\\_rating\\_ceiling" in text
    assert "estimated\\_rating\\_band\\_label" in text
    assert "benchmark\\_passed" in text
    assert "rating\\_benchmark\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B26-FULL-CHESS-RATING-BENCHMARK-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
