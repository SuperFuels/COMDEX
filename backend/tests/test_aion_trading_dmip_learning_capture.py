# /workspaces/COMDEX/backend/tests/test_aion_trading_dmip_learning_capture.py

from __future__ import annotations

from pathlib import Path
import importlib

cap = importlib.import_module("backend.modules.aion_trading.dmip_learning_capture")


def test_log_llm_accuracy_stub_writes_and_returns_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cap, "_DMIP_LLM_ACCURACY_PATH", tmp_path / "dmip_llm_accuracy.jsonl")

    out = cap.log_llm_accuracy_stub(
        checkpoint="london",
        pair="EUR/USD",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BULLISH",
            "confidence": "MEDIUM",
            "key_levels": [1.0825, "1.0850", "bad"],
        },
        agreement="agree",
        selected_bias="BULLISH",
        confidence="MEDIUM",
        source="pytest",
    )

    assert isinstance(out, dict)
    assert out["ok"] is True
    assert out["non_blocking"] is True
    assert out["capture_type"] == "dmip_llm_accuracy_append"
    assert out["checkpoint"] == "london"
    assert out["pair"] == "EUR/USD"
    assert out["agreement"] == "agree"
    assert out["selected_bias"] == "BULLISH"
    assert out["confidence"] == "MEDIUM"
    assert "row" in out and isinstance(out["row"], dict)

    p = Path(out["path"])
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "EUR/USD" in text
    assert "dmip_llm_accuracy_event.v1" in text


def test_log_task_tracking_stub_writes_and_returns_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cap, "_DMIP_TASK_TRACKING_PATH", tmp_path / "dmip_task_tracking.jsonl")

    out = cap.log_task_tracking_stub(
        checkpoint="london",
        pair="GBP/USD",
        stage="dmip_llm_consultation",
        status="processed",
        details={
            "agreement": "agree",
            "bias": "BULLISH",
            "confidence": "MEDIUM",
        },
        source="pytest",
    )

    assert isinstance(out, dict)
    assert out["ok"] is True
    assert out["non_blocking"] is True
    assert out["capture_type"] == "dmip_task_tracking_append"
    assert out["checkpoint"] == "london"
    assert out["pair"] == "GBP/USD"
    assert out["stage"] == "dmip_llm_consultation"
    assert out["status"] == "processed"
    assert "row" in out and isinstance(out["row"], dict)

    p = Path(out["path"])
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "GBP/USD" in text
    assert "dmip_task_tracking_event.v1" in text


def test_capture_append_failure_is_non_blocking(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cap, "_DMIP_LLM_ACCURACY_PATH", tmp_path / "dmip_llm_accuracy.jsonl")
    monkeypatch.setattr(cap, "_DMIP_TASK_TRACKING_PATH", tmp_path / "dmip_task_tracking.jsonl")

    def _boom(path, row):
        raise RuntimeError("simulated append failure")

    monkeypatch.setattr(cap, "_atomic_append_jsonl", _boom)

    out1 = cap.log_llm_accuracy_stub(
        checkpoint="london",
        pair="USD/JPY",
        llm_pair={"claude_bias": "BEARISH", "gpt4_bias": "BULLISH", "confidence": "LOW"},
        agreement="disagree",
        selected_bias="AVOID",
        confidence="LOW",
        source="pytest",
    )
    assert isinstance(out1, dict)
    assert out1["ok"] is False
    assert out1["non_blocking"] is True
    assert out1["error"] == "dmip_llm_accuracy_append_failed"
    assert "simulated append failure" in str(out1.get("message", ""))

    out2 = cap.log_task_tracking_stub(
        checkpoint="london",
        pair="USD/JPY",
        stage="dmip_llm_consultation",
        status="processed",
        details={"agreement": "disagree", "bias": "AVOID", "confidence": "LOW"},
        source="pytest",
    )
    assert isinstance(out2, dict)
    assert out2["ok"] is False
    assert out2["non_blocking"] is True
    assert out2["error"] == "dmip_task_tracking_append_failed"
    assert "simulated append failure" in str(out2.get("message", ""))