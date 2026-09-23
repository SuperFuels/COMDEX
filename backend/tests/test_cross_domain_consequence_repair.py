import json
import hashlib
from pathlib import Path

from backend.modules.hexcore.cross_domain_consequence_repair import (
    _failure_episodes,
    _historical_blocker_episodes,
    _pending_failure_runs,
    run_once,
)


def test_resolved_blocker_is_recovered_only_from_intact_later_evidence(tmp_path: Path):
    data = tmp_path / "backend/modules/hexcore/data/progressive_competency"
    results = tmp_path / "results/progressive_competency"
    data.mkdir(parents=True)
    results.mkdir(parents=True)
    authority = tmp_path / "backend/modules/hexcore/progressive_competency_executor.py"
    authority.write_text("authority evolved after resolution")
    evidence = []
    for index in range(4):
        artifact = results / f"contract-{index}.json"
        artifact.write_text(json.dumps({"contract": {"contract_id": f"c{index}"}}))
        evidence.append({
            "evidence_id": f"e{index}", "subject_id": "software_engineering",
            "verified": True, "independent_outcome": True,
            "recorded_epoch": 20 + index,
            "artifact": str(artifact.relative_to(tmp_path)),
            "artifact_hash": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        })
    (data / "state.json").write_text(json.dumps({
        "blockers": [{
            "blocker_id": "b1", "blocker_type": "executor_capability",
            "status": "resolved", "subject_id": "software_engineering",
            "created_at": 10, "resolved_at": 15,
            "authority_artifact": str(authority.relative_to(tmp_path)),
            "artifact_hash": "resolution-time-authority-hash",
        }],
        "evidence": evidence,
    }))
    recovered = _historical_blocker_episodes(tmp_path)
    assert len(recovered) == 1
    assert recovered[0]["subject_id"] == "software_engineering"
    assert recovered[0]["later_distinct_contracts"] == ["e1", "e2", "e3"]

    (results / "contract-0.json").write_text("tampered")
    assert _historical_blocker_episodes(tmp_path) == []


def test_failure_episode_requires_failure_then_later_executor_success():
    rows = [
        {"subject_id": "software_engineering", "contract_id": "c1", "status": "rejected", "recorded_epoch": 1},
        {"subject_id": "software_engineering", "contract_id": "c1", "status": "rejected_and_parked", "recorded_epoch": 2},
        {"subject_id": "software_engineering", "contract_id": "c1", "status": "verified_and_recorded", "recorded_epoch": 3},
        {"subject_id": "software_engineering", "contract_id": "c2", "status": "verified_and_recorded", "recorded_epoch": 4},
    ]
    episodes = _failure_episodes(rows)
    assert len(episodes) == 1
    assert episodes[0]["failure_count"] == 2
    assert episodes[0]["later_distinct_contracts"] == ["c2"]


def test_unconfirmed_failure_is_routed_to_pending_not_counted_as_repaired():
    rows = [
        {"subject_id": "software_engineering", "contract_id": "open", "status": "rejected", "recorded_epoch": 1},
        {"subject_id": "software_engineering", "contract_id": "open", "status": "rejected_and_parked", "recorded_epoch": 2},
    ]
    assert _failure_episodes(rows) == []
    pending = _pending_failure_runs(rows)
    assert len(pending) == 1
    assert pending[0]["failure_count"] == 2


def test_confirmed_episode_survives_executor_attempt_window_rollover(tmp_path: Path, monkeypatch):
    import backend.modules.hexcore.cross_domain_consequence_repair as repair

    repo_root = tmp_path
    executor_path = repo_root / "backend/modules/hexcore/data/progressive_competency/executor.json"
    executor_path.parent.mkdir(parents=True)
    executor_path.write_text(json.dumps({"attempts": []}))
    (repo_root / "results").mkdir()
    (repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl").write_text("")
    state_path = repo_root / "backend/modules/hexcore/data/cross_domain_consequence_repair/state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    retained = {
        "episode_id": "natural_failure_retained",
        "subject_id": "software_engineering",
        "contract_id": "old-contract",
        "later_consequence_confirmed": True,
        "later_distinct_contracts": ["later-contract"],
        "private_trial": {"passed": True},
    }
    state_path.write_text(json.dumps({
        "schema_version": "aion.hexcore.cross_domain_consequence_repair.v1",
        "episodes": {retained["episode_id"]: retained}, "pending_repairs": {},
        "external_outcomes": {}, "rejected_repairs": [],
    }))
    monkeypatch.setattr(repair, "HexCorePersistentLearningRuntime", _FakeRuntime)
    result = repair.run_once(repo_root=repo_root, state_path=state_path,
                             result_path=repo_root / "results/result.json")
    rebuilt = json.loads(state_path.read_text())
    assert retained["episode_id"] in rebuilt["episodes"]
    assert result["gate"]["consequence_confirmed_repairs"] == 1


class _FakeSkills:
    def promote(self, candidate):
        return {"promoted": True, "champion_id": candidate.procedure_id}

    def record_outcome(self, **kwargs):
        return None

    def champion(self, goal):
        return {"procedure_id": "procedure_cross_domain_consequence_confirmed_self_repair_v1"}


class _FakeStore:
    def commit(self, **kwargs):
        return None


class _FakeRuntime:
    def __init__(self, **kwargs):
        self.skills = _FakeSkills()
        self.store = _FakeStore()


def test_live_operational_ledgers_report_only_current_reconstructable_repairs(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    result = run_once(
        repo_root=repo_root,
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
    )
    assert result["gate"]["external_changes_misrouted_to_repair"] == 0
    assert result["gate"]["unsafe_live_writes"] == 0
    rebuilt = json.loads((tmp_path / "state.json").read_text())
    assert len(rebuilt["episodes"]) == result["gate"]["natural_internal_failure_episodes"]
    assert result["passed"] is bool(result["gate"]["accepted"])
