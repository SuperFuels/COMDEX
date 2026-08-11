from pathlib import Path

from backend.modules.hexcore.open_toolchain_progressive_authority import (
    OpenToolchainProgressiveAuthority,
    SUITES,
    build_toolchain_runners,
)


ROOT = Path(__file__).resolve().parents[2]


def test_discovers_real_toolchains_and_falsifies_every_subskill(tmp_path):
    fabric = OpenToolchainProgressiveAuthority(repo_root=ROOT, state_path=tmp_path / "state.json")
    assert set(fabric.state["adapters"]) == set(SUITES)
    for adapter in fabric.state["adapters"].values():
        assert adapter["status"] == "verified_available"
        assert adapter["candidate_passed"] is True
        assert adapter["counterexamples_rejected"] == adapter["counterexamples_total"]


def test_contract_execution_uses_real_authority_and_rejects_unsafe_variants(tmp_path):
    runners = build_toolchain_runners(repo_root=ROOT, state_path=tmp_path / "state.json")
    for subject_id, (_, mutations, _) in SUITES.items():
        result = runners[subject_id]({"requirement": {"kind": "exercise", "subskills": list(mutations)[:2]}}, [])
        assert result["passed"] is True
        assert result["gate"]["counterexamples_rejected"] == 2
        assert result["gate"]["unsafe_variants_rejected"] == 6
        assert result["gate"]["source_disjoint_transfer"] is False


def test_missing_toolchain_fails_closed(monkeypatch, tmp_path):
    from backend.modules.hexcore import open_toolchain_progressive_authority as module
    original = module._toolchain
    monkeypatch.setattr(module, "_toolchain", lambda subject_id, repo_root: None if subject_id == "rust" else original(subject_id, repo_root))
    fabric = OpenToolchainProgressiveAuthority(repo_root=ROOT, state_path=tmp_path / "state.json")
    assert fabric.state["adapters"]["rust"]["status"] == "rejected"
