import hashlib
import json
from pathlib import Path

from backend.modules.hexcore.simulator_disjoint_embodied_scaleup import (
    _signed_fixture,
    build_contract,
    run,
    sha256,
    verify_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_frozen_cloud_contract_binds_retained_skill_ancestry() -> None:
    contract = build_contract(REPO_ROOT)
    repeated = build_contract(REPO_ROOT)
    assert contract["contract_sha256"] == sha256({k: v for k, v in contract.items() if k != "contract_sha256"})
    assert repeated["contract_sha256"] == contract["contract_sha256"]
    assert repeated["frozen_at"] == contract["frozen_at"]
    assert [row["procedure_id"] for row in contract["skill_ancestry"]] == [
        "procedure_rgb_belief_state_mujoco_planning_v2",
        "procedure_rgb_contact_occlusion_skill_composition_v3",
        "procedure_rgb_articulated_sequence_skill_v4",
    ]
    assert {row["arm_id"] for row in contract["experimental_arms"]} == {
        "aion_retained", "aion_cold", "aion_cosmos", "gr00t_teacher"
    }
    assert "privileged_object_pose" in contract["observation_contract"]["prohibited"]
    assert contract["authority"]["required_container_digest"].startswith("sha256:")
    assert contract["authority"]["official_asset_recovery"]["fallback_root_version"] == "5.1"


def test_signed_receipt_verifier_fails_closed_on_tamper_and_missing_authority() -> None:
    contract = build_contract(REPO_ROOT)
    receipt, public_key = _signed_fixture(contract)
    assert verify_receipt(receipt, contract, public_key)["accepted"] is True

    altered = json.loads(json.dumps(receipt))
    altered["metrics"]["sealed_success"] = .99
    verdict = verify_receipt(altered, contract, public_key)
    assert verdict["accepted"] is False
    assert "SIGNATURE_INVALID" in verdict["errors"]

    unsigned = dict(receipt)
    unsigned.pop("signature_ed25519_base64")
    assert verify_receipt(unsigned, contract, public_key)["accepted"] is False


def test_local_handoff_is_ready_but_cannot_self_promote(tmp_path: Path) -> None:
    outcome = run(repo_root=REPO_ROOT, result_path=tmp_path / "result.json",
                  handoff_path=tmp_path / "handoff.json")
    assert outcome["package_ready"] is True
    assert outcome["external_execution_complete"] is False
    assert outcome["promoted"] is False
    assert outcome["status"] == "READY_FOR_NVIDIA_EXECUTION"
    assert outcome["tamper_rejected"] is True
    assert outcome["unsigned_rejected"] is True
    assert "NVIDIA Linux GPU authority" in outcome["blockers"]


def test_real_rgb_authority_probe_is_hash_bound_and_does_not_overclaim() -> None:
    probe = json.loads((REPO_ROOT / "results/aion_isaac_lab_rgb_authority_probe.json").read_text())
    assert probe["verified_properties"]["rgb_to_action_to_physx_consequence"] is True
    assert probe["verified_properties"]["unsafe_actions"] == 0
    assert probe["promotion"]["execution_adapter"] == "POSITIVE"
    assert probe["promotion"]["manipulation_competence"] is False
    assert probe["promotion"]["cosmos_mastery"] is False
    assert probe["promotion"]["gr00t_mastery"] is False
    for arm in ("retained", "cold"):
        row = probe["matched_probe"][arm]
        path = REPO_ROOT / row["receipt"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["receipt_sha256"]
        receipt = json.loads(path.read_text())
        assert receipt["failure"] is None
        assert receipt["audit"]["completed_without_failure"] is True
        assert receipt["contract_sha256"] == probe["contract_sha256"]
