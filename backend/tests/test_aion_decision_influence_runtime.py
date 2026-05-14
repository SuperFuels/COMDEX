from __future__ import annotations

import copy

from backend.modules.aion_learning.contracts_decision_influence import DecisionInfluenceUpdate
from backend.modules.aion_learning.decision_influence_runtime import DecisionInfluenceRuntime


def _make_update(**kwargs) -> DecisionInfluenceUpdate:
    base = dict(
        session_id="sess-1",
        turn_id="turn-1",
        source="learning_runtime",
        reason="cluster review adjustment",
        confidence=0.82,
        updates={
            "setup_confidence_weights": {
                "tier3_smc_intraday": 1.15,
            }
        },
        metadata={"test": True},
    )
    base.update(kwargs)
    return DecisionInfluenceUpdate(**base)


def test_valid_update_accepted_and_persisted():
    rt = DecisionInfluenceRuntime()
    upd = _make_update(
        updates={
            "setup_confidence_weights": {"tier3_smc_intraday": 1.2},
            "stand_down_sensitivity": {"red_event_days": 1.35},
        }
    )

    out = rt.apply_update(upd, dry_run=False)

    assert out["ok"] is True
    assert out["error"] is None
    assert out["rejected"] == []
    assert "setup_confidence_weights" in out["applied"]
    assert "stand_down_sensitivity" in out["applied"]

    state = rt.state
    assert float(state["setup_confidence_weights"]["tier3_smc_intraday"]) == 1.2
    assert float(state["stand_down_sensitivity"]["red_event_days"]) == 1.35

    audit = rt.audit_log
    assert len(audit) == 1
    assert audit[0]["dry_run"] is False
    assert audit[0]["session_id"] == "sess-1"
    assert audit[0]["turn_id"] == "turn-1"
    assert audit[0]["source"] == "learning_runtime"
    assert audit[0]["reason"] == "cluster review adjustment"
    assert float(audit[0]["confidence"]) == 0.82
    assert audit[0]["applied_count"] == 2
    assert audit[0]["rejected_count"] == 0
    assert audit[0]["metadata"] == {"test": True}
    assert set(audit[0]["applied_sections"]) == {"setup_confidence_weights", "stand_down_sensitivity"}
    assert "audit_id" in audit[0]


def test_forbidden_key_rejected_by_contract_non_breaking_failure_shape():
    rt = DecisionInfluenceRuntime()
    before_state = copy.deepcopy(rt.state)
    upd = _make_update(
        updates={
            "max_risk_per_trade": 0.5,  # forbidden top-level
        }
    )

    out = rt.apply_update(upd, dry_run=False)

    assert out["ok"] is False
    assert out["applied"] == {}
    assert out["rejected"] == []
    assert out["error"] is not None
    assert out["error"]["type"] == "ValueError"
    assert "forbidden decision influence key" in out["error"]["message"]

    # runtime now seeds defaults; verify no mutation vs baseline (non-breaking failure)
    assert rt.state == before_state

    # observability may persist a denied/error audit row now (schema has no guaranteed "status")
    assert isinstance(rt.audit_log, list)
    if rt.audit_log:
        last = rt.audit_log[-1]
        assert isinstance(last, dict)
        assert "audit_id" in last
        assert last.get("applied_count") == 0
        assert last.get("rejected_count", 0) >= 0


def test_unknown_section_rejected_by_contract_non_breaking_failure_shape():
    rt = DecisionInfluenceRuntime()
    before_state = copy.deepcopy(rt.state)
    upd = _make_update(
        updates={
            "mystery_section": {"x": 1.0},
        }
    )

    out = rt.apply_update(upd)

    assert out["ok"] is False
    assert out["error"] is not None
    assert out["error"]["type"] == "ValueError"
    assert "unsupported decision influence section" in out["error"]["message"]

    # state should remain unchanged on contract failure
    assert rt.state == before_state

    # runtime may now log denied validation attempts (schema has no guaranteed "status")
    assert isinstance(rt.audit_log, list)
    if rt.audit_log:
        last = rt.audit_log[-1]
        assert isinstance(last, dict)
        assert "audit_id" in last
        assert last.get("applied_count") == 0


def test_out_of_range_values_are_clamped():
    rt = DecisionInfluenceRuntime()
    upd = _make_update(
        updates={
            "setup_confidence_weights": {
                "tier3_smc_intraday": 9.9,   # clamp to 2.0
                "momentum_orb": -5.0,        # clamp to 0.0
            },
            "event_caution_multipliers": {
                "nfp": 9.0,                  # clamp to 3.0
                "cpi": 0.1,                  # clamp to 0.5
            },
            "stand_down_sensitivity": {
                "llm_disagreement": 0.1,     # clamp to 0.5
                "news_conflict": 2.8,        # clamp to 2.0
            },
        }
    )

    out = rt.apply_update(upd)

    assert out["ok"] is True
    assert out["error"] is None
    assert out["rejected"] == []

    state = rt.state
    assert float(state["setup_confidence_weights"]["tier3_smc_intraday"]) == 2.0
    assert float(state["setup_confidence_weights"]["momentum_orb"]) == 0.0
    assert float(state["event_caution_multipliers"]["nfp"]) == 3.0
    assert float(state["event_caution_multipliers"]["cpi"]) == 0.5
    assert float(state["stand_down_sensitivity"]["llm_disagreement"]) == 0.5
    assert float(state["stand_down_sensitivity"]["news_conflict"]) == 2.0

    # 6 numeric leaves applied total
    assert out["audit_entry"]["applied_count"] == 6
    assert out["audit_entry"]["rejected_count"] == 0


def test_dry_run_returns_ok_and_does_not_persist_mutation():
    rt = DecisionInfluenceRuntime()
    upd = _make_update(
        updates={
            "llm_trust_weights": {"gpt": 1.1, "claude": 0.9},
        }
    )

    before_state = copy.deepcopy(rt.state)
    out = rt.apply_update(upd, dry_run=True)
    after_state = copy.deepcopy(rt.state)

    assert out["ok"] is True
    assert out["error"] is None
    assert out["audit_entry"]["dry_run"] is True
    assert out["applied"]["llm_trust_weights"]["gpt"] == 1.1
    assert out["applied"]["llm_trust_weights"]["claude"] == 0.9
    assert out["audit_entry"]["applied_count"] == 2
    assert out["audit_entry"]["rejected_count"] == 0

    assert before_state == after_state  # no mutation

    # runtime may log dry-run events for observability (schema has no guaranteed "status")
    assert isinstance(rt.audit_log, list)
    if rt.audit_log:
        last = rt.audit_log[-1]
        assert isinstance(last, dict)
        assert last.get("dry_run") is True
        assert "audit_id" in last
        assert last.get("applied_count") == 2


def test_non_numeric_leaf_values_are_rejected_but_non_breaking():
    rt = DecisionInfluenceRuntime()
    upd = _make_update(
        updates={
            "pair_session_preferences": {
                "EURUSD": {
                    "london": 1.2,
                    "ny": "high",  # invalid leaf
                }
            }
        }
    )

    out = rt.apply_update(upd)

    assert out["ok"] is True
    assert out["error"] is None
    assert len(out["rejected"]) == 1
    rej = out["rejected"][0]
    assert rej["section"] == "pair_session_preferences"
    assert rej["path"].endswith("EURUSD.ny")
    assert "numeric" in rej["reason"]

    state = rt.state
    assert float(state["pair_session_preferences"]["EURUSD"]["london"]) == 1.2
    assert "ny" not in state["pair_session_preferences"]["EURUSD"]

    # audit persists successful partial apply
    assert len(rt.audit_log) >= 1
    last = rt.audit_log[-1]
    assert last["rejected_count"] == 1
    assert last["applied_count"] == 1
    assert "audit_id" in last


def test_non_dict_section_payload_rejected_non_breaking_with_partial_apply():
    rt = DecisionInfluenceRuntime()
    upd = _make_update(
        updates={
            "setup_confidence_weights": {"tier3_smc_intraday": 1.1},
            "llm_trust_weights": 1.2,  # invalid section payload type (must be dict)
        }
    )

    out = rt.apply_update(upd)

    assert out["ok"] is True
    assert out["error"] is None

    # valid section applied
    assert float(rt.state["setup_confidence_weights"]["tier3_smc_intraday"]) == 1.1

    # invalid section rejected, non-fatal
    assert len(out["rejected"]) == 1
    rej = out["rejected"][0]
    assert rej["section"] == "llm_trust_weights"
    assert rej["path"] == "llm_trust_weights"
    assert "must be a dict" in rej["reason"]

    assert len(rt.audit_log) >= 1
    last = rt.audit_log[-1]
    assert last["applied_count"] == 1
    assert last["rejected_count"] == 1
    assert "audit_id" in last


def test_runtime_exception_path_returns_failure_shaped_result_non_breaking(monkeypatch):
    rt = DecisionInfluenceRuntime()
    before_state = copy.deepcopy(rt.state)
    upd = _make_update()

    # Force internal error after validation to test non-breaking shape
    def _boom(*args, **kwargs):
        raise RuntimeError("forced test failure")

    monkeypatch.setattr(rt, "_apply_section", _boom)

    out = rt.apply_update(upd, dry_run=False)

    assert out["ok"] is False
    assert out["applied"] == {}
    assert out["rejected"] == []
    assert out["error"] is not None
    assert out["error"]["type"] == "RuntimeError"
    assert "forced test failure" in out["error"]["message"]

    # Failure-shaped audit entry is returned
    assert out["audit_entry"]["applied_count"] == 0
    assert out["audit_entry"]["rejected_count"] == 0
    assert out["audit_entry"]["dry_run"] is False
    assert "runtime_error" in out["audit_entry"]

    # No mutation on failure path
    assert rt.state == before_state

    # runtime may or may not persist failure audit depending on observability policy
    assert isinstance(rt.audit_log, list)
    if rt.audit_log:
        last = rt.audit_log[-1]
        assert isinstance(last, dict)
        assert "audit_id" in last
        assert last.get("applied_count") == 0


def test_nested_leaf_count_helper_counts_only_leaves():
    obj = {
        "a": 1,
        "b": {"x": 2, "y": {"z": 3}},
        "c": {},
    }
    assert DecisionInfluenceRuntime._count_leaf_values(obj) == 3