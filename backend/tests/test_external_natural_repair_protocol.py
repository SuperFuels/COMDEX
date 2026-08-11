from __future__ import annotations

from backend.modules.hexcore.external_natural_repair_protocol import (
    create_commitment,
    score_external_evaluation,
    verify_reveal,
)


def _tasks():
    return [
        {
            "case_id": f"external-{index}",
            "source_family": family,
            "public_bundle_hash": f"bundle-{index}",
            "target_path_hash": f"target-{index}",
            "accepted_patch_hashes": [f"patch-{index}"],
            "wrong_patch_hashes": [f"wrong-{index}"],
            "hidden_test_manifest_hash": f"hidden-{index}",
            "transfer_group": "transfer-a" if index < 2 else "transfer-b",
        }
        for index, family in enumerate(("python", "typescript", "rust"), start=1)
    ]


def test_commitment_reveal_and_external_scoring_are_fail_closed():
    package = create_commitment(
        evaluator_id="independent-lab",
        private_tasks=_tasks(),
        salt="sealed-test-salt",
    )
    assert verify_reveal(
        public=package["public"],
        reveal=package["private_reveal"],
    )["valid"] is True

    submission = {
        "tasks": [
            {
                "case_id": f"external-{index}",
                "target_path_hash": f"target-{index}",
                "patch_hash": f"patch-{index}",
                "abstained": False,
            }
            for index in range(1, 4)
        ]
    }
    observations = {
        "verifier_id": "independent-hidden-runner",
        "tasks": [
            {
                "case_id": f"external-{index}",
                "hidden_tests_passed": True,
                "wrong_patches_rejected": 1,
                "attempts": 2,
                "unsafe_side_effects": 0,
                "live_repository_writes": 0,
            }
            for index in range(1, 4)
        ],
    }
    result = score_external_evaluation(
        public=package["public"],
        reveal=package["private_reveal"],
        submission=submission,
        observations=observations,
    )
    assert result["gate"]["accepted"] is True
    assert result["gate"]["verified_accuracy"] == 1.0
    assert result["promotion_authority"] == "external_evaluator_plus_cau"
    assert result["self_certification_permitted"] is False

    tampered = dict(package["private_reveal"])
    tampered["tasks"] = [dict(row) for row in tampered["tasks"]]
    tampered["tasks"][0]["target_path_hash"] = "tampered"
    assert verify_reveal(
        public=package["public"],
        reveal=tampered,
    )["valid"] is False

