# /workspaces/COMDEX/backend/tests/test_aion_decision_influence_capture_integration.py

from __future__ import annotations

from typing import Any, Dict

import pytest

from backend.modules.aion_trading import skill_pack as trading_skill_pack


def _assert_primary_skill_fields(result: Dict[str, Any]) -> None:
    # Primary/stable fields from skill_pack adapter contract
    assert isinstance(result, dict)
    assert "ok" in result
    assert result.get("skill_id") == "skill.trading_update_decision_influence_weights"
    assert "schema_version" in result
    assert "action" in result
    assert "dry_run" in result
    assert "applied" in result
    assert "proposed_patch" in result
    assert "validated_diff" in result
    assert "warnings" in result
    assert "snapshot_hash" in result


def test_show_path_includes_capture_artifacts() -> None:
    result = trading_skill_pack.skill_trading_update_decision_influence_weights(
        {"action": "show"}
    )

    _assert_primary_skill_fields(result)

    # New non-blocking capture artifacts (must be present on show path)
    assert "trading_journal" in result
    assert "journal_summary" in result
    assert "trading_capture_result" in result

    assert isinstance(result["journal_summary"], dict)
    assert isinstance(result["trading_capture_result"], dict)


def test_update_dry_run_includes_changed_keys_summary() -> None:
    # Use a simple deterministic patch (delta + set) against known keys
    result = trading_skill_pack.skill_trading_update_decision_influence_weights(
        {
            "action": "update",
            "dry_run": True,
            "reason": "pytest dry-run capture integration",
            "patch": {
                "ops": [
                    {
                        "op": "delta",
                        "key": "llm_trust_weights.gpt4_bias",
                        "value": 0.05,
                    },
                    {
                        "op": "set",
                        "key": "setup_confidence_weights.momentum_orb",
                        "value": 1.15,
                    },
                ]
            },
        }
    )

    _assert_primary_skill_fields(result)

    # Non-blocking capture artifacts present
    assert "journal_summary" in result
    assert "trading_capture_result" in result

    journal_summary = result["journal_summary"]
    capture_result = result["trading_capture_result"]

    assert isinstance(journal_summary, dict)
    assert isinstance(capture_result, dict)

    # Requested behavior checks
    assert int(journal_summary.get("changed_count", 0)) >= 1
    assert capture_result.get("non_blocking") is True


def test_capture_failure_is_non_breaking(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force capture append/write path to fail, but skill should still return primary result.
    def _boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("forced append failure for test")

    # Patch in the module where the helper is used.
    # If your helper lives elsewhere, move this patch target accordingly.
    monkeypatch.setattr(trading_skill_pack, "_atomic_append_jsonl", _boom, raising=True)

    result = trading_skill_pack.skill_trading_update_decision_influence_weights(
        {"action": "show"}
    )

    # Overall result should not crash and should preserve primary skill fields
    _assert_primary_skill_fields(result)

    # Capture result must show failure but remain non-breaking to the skill response
    assert "trading_capture_result" in result
    assert isinstance(result["trading_capture_result"], dict)
    assert result["trading_capture_result"].get("ok") is False

    # Non-crashing behavior: result dict still returned with core fields intact
    assert result.get("skill_id") == "skill.trading_update_decision_influence_weights"