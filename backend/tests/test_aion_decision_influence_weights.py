# /workspaces/COMDEX/backend/tests/test_aion_decision_influence_weights.py
from __future__ import annotations

from backend.modules.aion_trading.decision_influence_weights import (
    DEFAULT_WEIGHTS,
    apply_patch_dry_run,
    default_weights_snapshot,
    validate_weights_snapshot,
)


def test_default_snapshot_validates_and_has_hash():
    snap = default_weights_snapshot()
    vr = validate_weights_snapshot(snap)

    assert vr.ok is True
    assert isinstance(vr.snapshot_hash, str)
    assert len(vr.snapshot_hash) == 64
    assert abs(sum(vr.normalized_weights.values()) - 1.0) < 1e-6


def test_unknown_key_rejected():
    snap = default_weights_snapshot()
    bad = dict(snap)
    bad["weights"] = dict(snap["weights"])
    bad["weights"]["unknown_factor"] = 0.123

    vr = validate_weights_snapshot(bad)
    assert vr.ok is False
    assert any("unknown_weight_keys" in e for e in vr.errors)


def test_missing_key_rejected():
    snap = default_weights_snapshot()
    bad = dict(snap)
    bad["weights"] = dict(snap["weights"])
    bad["weights"].pop(next(iter(DEFAULT_WEIGHTS.keys())))

    vr = validate_weights_snapshot(bad)
    assert vr.ok is False
    assert any("missing_weight_keys" in e for e in vr.errors)


def test_patch_delta_dry_run_changes_weight_and_returns_diff():
    snap = default_weights_snapshot(version=3)
    vr, diff = apply_patch_dry_run(
        snap,
        patch={"ops": [{"op": "delta", "key": "liquidity_sweep", "value": 0.05}]},
        reason="test increase liquidity sweep",
        updated_by="pytest",
    )

    assert vr.ok is True
    assert "liquidity_sweep" in diff.changed
    ch = diff.changed["liquidity_sweep"]
    assert "before" in ch
    assert "after_raw" in ch
    assert "after_normalized" in ch
    assert abs(diff.sum_after_normalized - 1.0) < 1e-6


def test_patch_unknown_key_fails():
    snap = default_weights_snapshot()
    vr, diff = apply_patch_dry_run(
        snap,
        patch={"ops": [{"op": "delta", "key": "fake_key", "value": 0.05}]},
        reason="bad key",
        updated_by="pytest",
    )

    assert vr.ok is False
    assert any("unknown_weight_key" in e for e in vr.errors)


def test_per_key_clamp_emits_warning():
    snap = default_weights_snapshot()
    vr, diff = apply_patch_dry_run(
        snap,
        patch={"ops": [{"op": "set", "key": "news_risk_filter", "value": 0.99}]},
        reason="overset",
        updated_by="pytest",
    )

    # Should still validate via clamp + normalize
    assert vr.ok is True
    assert any("clamped:news_risk_filter" in w for w in vr.warnings)