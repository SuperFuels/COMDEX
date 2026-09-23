"""Freeze and verify AION's simulator-disjoint embodied cloud programme.

This module does not claim an NVIDIA result on non-NVIDIA hardware.  It binds
the retained local skill ancestry into a content-addressed Isaac Lab expedition
contract, validates cloud receipts fail-closed, and separates AION, cold,
Cosmos-assisted and GR00T teacher arms without transferring authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.hexcore.persistent_learning import _canonical_hash


SCHEMA_VERSION = "aion.simulator_disjoint_embodied_contract.v2"
RECEIPT_SCHEMA = "aion.isaac_lab_outcome_receipt.v1"
PROCEDURE_ID = "procedure_simulator_disjoint_embodied_scaleup_handoff_v1"
PARENT_PROCEDURE_ID = "procedure_rgb_articulated_sequence_skill_v4"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def valid_sha256(value: Any) -> bool:
    try:
        return isinstance(value, str) and len(value) == 64 and int(value, 16) >= 0
    except (TypeError, ValueError):
        return False


def _skill_ancestry(root: Path) -> list[dict[str, Any]]:
    definitions = (
        ("rgb_belief_state_physical_planning", "procedure_rgb_belief_state_mujoco_planning_v2",
         root / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json", None),
        ("rgb_contact_occlusion_skill_composition", "procedure_rgb_contact_occlusion_skill_composition_v3",
         root / "backend/modules/hexcore/data/rgb_contact_occlusion/state.json",
         root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_contact_occlusion.json"),
        ("rgb_articulated_sequence_tool_use", PARENT_PROCEDURE_ID,
         root / "backend/modules/hexcore/data/rgb_articulated_sequence/state.json",
         root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_articulated_sequence.json"),
    )
    ancestry = []
    for goal, procedure, state_path, capsule_path in definitions:
        state = json.loads(state_path.read_text())
        if state.get("champions", {}).get(goal) != procedure:
            raise RuntimeError(f"retained_champion_missing:{procedure}")
        row = {"goal": goal, "procedure_id": procedure,
               "state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
               "verified_at": state.get("updated_at") or state.get("last_commit", {}).get("timestamp")}
        if capsule_path is not None:
            capsule = json.loads(capsule_path.read_text())
            expected = _canonical_hash({k: v for k, v in capsule.items() if k != "capsule_digest"})
            if capsule.get("capsule_digest") != expected or capsule.get("procedure_id") != procedure:
                raise RuntimeError(f"retained_capsule_tampered:{procedure}")
            row.update({"capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
                        "capsule_digest": capsule["capsule_digest"],
                        "verified_at": capsule.get("verified_at") or row["verified_at"]})
        ancestry.append(row)
    return ancestry


def build_contract(root: Path) -> dict[str, Any]:
    ancestry = _skill_ancestry(root)
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": "aion_embodied_expedition_isaac_lab_v1",
        "frozen_at": max(str(row.get("verified_at") or "") for row in ancestry),
        "authority": {
            "required_backend": "NVIDIA Isaac Lab",
            "required_physics": "PhysX",
            "required_container_family": "nvcr.io/nvidia/isaac-lab",
            "required_container_digest": "sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4",
            "official_asset_recovery": {
                "reason": "NVIDIA Isaac 6.0 Franka key returned HTTP 404 during pre-cohort authority probe",
                "only_permitted_missing_asset": "IsaacLab/Robots/FrankaEmika/panda_instanceable.usd",
                "fallback_root_version": "5.1",
                "same_authority_required": "omniverse-content-production.s3-us-west-2.amazonaws.com",
                "availability_check_required": True,
                "must_be_reported_in_receipt": True,
            },
            "permitted_environment_ids": [
                "Isaac-Lift-Cube-Franka-v0",
                "Isaac-Stack-Cube-Franka-v0",
                "Isaac-Open-Drawer-Franka-v0",
            ],
            "prohibited_authority_claims": ["MuJoCo_as_Isaac", "locally_fabricated_GPU_receipt", "proposal_model_as_physics"],
        },
        "mission": {
            "broad_objective": "Inspect an unfamiliar manipulation scene, discover how the embodiment acts, move required objects into stable target arrangements, recover from changed dynamics, and preserve safety.",
            "task_family": "contact_rich_object_manipulation",
            "minimum_subtasks": ["lift", "place", "stack_or_drawer"],
            "workflow_supplied": False,
            "object_roles_supplied": False,
        },
        "observation_contract": {
            "required": ["rgb", "timestamp", "episode_id", "observation_sha256"],
            "optional": ["depth", "proprioception_bounded", "acoustic"],
            "prohibited": ["privileged_object_pose", "privileged_target_pose", "simulator_reward", "ground_truth_contact_graph", "future_outcome"],
            "rgb_minimum_shape": [64, 64, 3],
        },
        "action_contract": {
            "type": "bounded_robot_action",
            "required_fields": ["values", "action_space_digest", "prediction", "precommitment_sha256"],
            "finite_only": True,
            "bounds_required": True,
            "commit_before_act": True,
            "shell_network_file_actions_prohibited": True,
        },
        "randomization": {
            "sealed_dimensions": ["mass", "friction", "restitution", "lighting", "camera_pose", "sensor_noise", "motor_strength", "object_geometry", "object_placement"],
            "development_seeds": 6,
            "sealed_seeds": 24,
            "seed_commitment_required": True,
        },
        "experimental_arms": [
            {"arm_id": "aion_retained", "role": "candidate", "memory": True, "proposal_models": []},
            {"arm_id": "aion_cold", "role": "cold_control", "memory": False, "proposal_models": []},
            {"arm_id": "aion_cosmos", "role": "proposal_challenger", "memory": True,
             "proposal_models": ["Cosmos-Predict2.5-2B/robot/action-cond"], "physics_authority": False},
            {"arm_id": "gr00t_teacher", "role": "teacher_baseline", "memory": False,
             "proposal_models": ["GR00T"], "champion_authority": False},
        ],
        "matched_budget": {"environment_steps": 50000, "wall_seconds": 14400, "GPU_hours": 4.0,
                           "reset_budget": 48, "intervention_budget": 5000},
        "promotion_gates": {
            "sealed_success_minimum": .70,
            "weakest_task_success_minimum": .50,
            "lift_over_cold_minimum": .20,
            "unsafe_actions": 0,
            "all_privileged_fields_absent": True,
            "later_reconstruction_required": True,
            "cross_backend_method_reuse_required": True,
            "cosmos_help_and_harm_reported": True,
            "teacher_independence_required": True,
        },
        "skill_ancestry": ancestry,
        "claim_boundary": "Package readiness and signed-receipt verification do not establish Isaac Lab competence until an NVIDIA authority executes the frozen contract.",
    }
    contract["contract_sha256"] = sha256({k: v for k, v in contract.items() if k != "contract_sha256"})
    return contract


def verify_receipt(receipt: Mapping[str, Any], contract: Mapping[str, Any],
                   public_key_pem: bytes) -> dict[str, Any]:
    errors: list[str] = []
    unsigned = {k: v for k, v in receipt.items() if k != "signature_ed25519_base64"}
    signature_valid = False
    try:
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            errors.append("KEY_NOT_ED25519")
        else:
            key.verify(base64.b64decode(receipt.get("signature_ed25519_base64", ""), validate=True), canonical_bytes(unsigned))
            signature_valid = True
    except (ValueError, TypeError, InvalidSignature):
        errors.append("SIGNATURE_INVALID")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        errors.append("SCHEMA_INVALID")
    if receipt.get("contract_sha256") != contract.get("contract_sha256"):
        errors.append("CONTRACT_MISMATCH")
    runtime = receipt.get("runtime") or {}
    if runtime.get("backend") != "NVIDIA Isaac Lab" or runtime.get("physics") != "PhysX":
        errors.append("NVIDIA_AUTHORITY_NOT_ATTESTED")
    if not runtime.get("gpu_name") or runtime.get("cuda_available") is not True:
        errors.append("CUDA_AUTHORITY_NOT_ATTESTED")
    for field in ("isaac_lab_version", "isaac_sim_version", "container_digest", "driver_version"):
        if not runtime.get(field):
            errors.append("MISSING_RUNTIME_" + field.upper())
    if runtime.get("container_digest") != contract.get("authority", {}).get("required_container_digest"):
        errors.append("CONTAINER_DIGEST_MISMATCH")
    asset = receipt.get("asset_authority") or {}
    recovery = contract.get("authority", {}).get("official_asset_recovery") or {}
    if recovery.get("must_be_reported_in_receipt"):
        expected_host = recovery.get("same_authority_required")
        if asset.get("recovery_applied") is not True or expected_host not in str(asset.get("selected_url", "")):
            errors.append("OFFICIAL_ASSET_RECOVERY_UNATTESTED")
    audit = receipt.get("audit") or {}
    required_true = ("seed_commitment_verified", "commit_before_act_verified", "privileged_fields_absent",
                     "matched_budget_verified", "skill_ancestry_verified", "baseline_isolation_verified")
    for field in required_true:
        if audit.get(field) is not True:
            errors.append("AUDIT_FAILED_" + field.upper())
    logs = receipt.get("logs") or {}
    for field in ("seed_commitment_sha256", "observation_chain_sha256", "action_chain_sha256",
                  "outcome_chain_sha256", "artifact_bundle_sha256"):
        if not valid_sha256(logs.get(field)):
            errors.append("INVALID_" + field.upper())
    metrics = receipt.get("metrics") or {}
    gates = contract["promotion_gates"]
    if float(metrics.get("sealed_success", 0)) < gates["sealed_success_minimum"]:
        errors.append("SEALED_SUCCESS_LOW")
    if float(metrics.get("weakest_task_success", 0)) < gates["weakest_task_success_minimum"]:
        errors.append("WEAKEST_TASK_LOW")
    if float(metrics.get("lift_over_cold", 0)) < gates["lift_over_cold_minimum"]:
        errors.append("COLD_LIFT_LOW")
    if int(metrics.get("unsafe_actions", 1)) != 0:
        errors.append("UNSAFE_ACTIONS")
    if metrics.get("cross_backend_method_reuse") is not True:
        errors.append("CROSS_BACKEND_REUSE_MISSING")
    if metrics.get("later_reconstruction") is not True:
        errors.append("LATER_RECONSTRUCTION_MISSING")
    arms = receipt.get("experimental_arms") or {}
    for arm in ("aion_retained", "aion_cold", "aion_cosmos", "gr00t_teacher"):
        if arm not in arms:
            errors.append("MISSING_ARM_" + arm.upper())
    return {"schema_version": "aion.isaac_lab_outcome_verdict.v1",
            "accepted": signature_valid and not errors, "signature_valid": signature_valid,
            "errors": errors,
            "boundary": "A valid signed receipt demonstrates execution of the frozen contract; scientific standing still depends on operator identity and reproducible artifacts."}


def _signed_fixture(contract: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    """A local verifier test fixture; explicitly not external evidence."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA, "contract_sha256": contract["contract_sha256"],
        "runtime": {"backend": "NVIDIA Isaac Lab", "physics": "PhysX", "gpu_name": "LOCAL_TEST_FIXTURE",
                    "cuda_available": True, "isaac_lab_version": "fixture", "isaac_sim_version": "fixture",
                    "container_digest": contract["authority"]["required_container_digest"], "driver_version": "fixture"},
        "asset_authority": {"recovery_applied": True,
                            "selected_url": "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Robots/FrankaEmika/panda_instanceable.usd"},
        "audit": {"seed_commitment_verified": True, "commit_before_act_verified": True,
                  "privileged_fields_absent": True, "matched_budget_verified": True,
                  "skill_ancestry_verified": True, "baseline_isolation_verified": True},
        "logs": {field: "a" * 64 for field in ("seed_commitment_sha256", "observation_chain_sha256",
                  "action_chain_sha256", "outcome_chain_sha256", "artifact_bundle_sha256")},
        "metrics": {"sealed_success": .8, "weakest_task_success": .6, "lift_over_cold": .3,
                    "unsafe_actions": 0, "cross_backend_method_reuse": True, "later_reconstruction": True},
        "experimental_arms": {arm["arm_id"]: {"episodes": 1} for arm in contract["experimental_arms"]},
        "local_test_fixture": True,
    }
    receipt["signature_ed25519_base64"] = base64.b64encode(private.sign(canonical_bytes(receipt))).decode()
    return receipt, public


def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)); json.loads(temporary.read_text()); os.replace(temporary, path)


def run(*, repo_root: Path, result_path: Path | None = None,
        handoff_path: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    result_path = result_path or root / "results/hexcore_simulator_disjoint_embodied_scaleup.json"
    handoff_path = handoff_path or root / "results/aion_isaac_lab_embodied_handoff.json"
    contract = build_contract(root)
    _atomic(handoff_path, contract)
    reloaded = json.loads(handoff_path.read_text())
    contract_reconstructed = reloaded["contract_sha256"] == sha256({k: v for k, v in reloaded.items() if k != "contract_sha256"})
    fixture, public = _signed_fixture(contract)
    fixture_verdict = verify_receipt(fixture, contract, public)
    tampered = json.loads(json.dumps(fixture)); tampered["metrics"]["sealed_success"] = 1.0
    tampered_verdict = verify_receipt(tampered, contract, public)
    unsigned = dict(fixture); unsigned.pop("signature_ed25519_base64")
    unsigned_verdict = verify_receipt(unsigned, contract, public)
    environment = {"machine": platform.machine(), "system": platform.system(),
                   "nvidia_credentials_present": any(bool(os.getenv(name)) for name in ("NGC_API_KEY", "NVIDIA_API_KEY")),
                   "cloud_credentials_present": any(bool(os.getenv(name)) for name in ("AWS_ACCESS_KEY_ID", "GCP_PROJECT", "AZURE_SUBSCRIPTION_ID"))}
    package_ready = bool(contract_reconstructed and fixture_verdict["accepted"] and not tampered_verdict["accepted"]
                         and not unsigned_verdict["accepted"] and len(contract["skill_ancestry"]) == 3)
    external_execution_complete = False
    result = {"schema_version": "aion.simulator_disjoint_scaleup_handoff_result.v1",
              "procedure_id": PROCEDURE_ID, "created_at": datetime.now(timezone.utc).isoformat(),
              "package_ready": package_ready, "external_execution_complete": external_execution_complete,
              "status": "READY_FOR_NVIDIA_EXECUTION" if package_ready else "REJECTED",
              "promoted": False, "contract_sha256": contract["contract_sha256"],
              "skill_ancestry_count": len(contract["skill_ancestry"]),
              "experimental_arms": [row["arm_id"] for row in contract["experimental_arms"]],
              "fixture_verifier_passed": fixture_verdict["accepted"],
              "tamper_rejected": not tampered_verdict["accepted"], "unsigned_rejected": not unsigned_verdict["accepted"],
              "environment": environment,
              "blockers": ["NVIDIA Linux GPU authority", "NGC/cloud credentials", "signed non-fixture outcome receipt"],
              "handoff_path": str(handoff_path),
              "claim_boundary": "The cloud contract and verifier are complete, but no Isaac Lab capability is promoted until NVIDIA physics executes the frozen package."}
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(repo_root=Path(__file__).resolve().parents[3]), indent=2, sort_keys=True))
