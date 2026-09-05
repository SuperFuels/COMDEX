"""Evidence-based sovereign compute recommendations without vendor or savings invention."""

from __future__ import annotations

from typing import Any, Dict

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


class SovereignCapacityPlanner:
    LEVELS = {
        "level_1_existing_machine": {
            "label": "Existing machine",
            "capacity": "one interactive user and bounded background work",
        },
        "level_2_aion_box": {
            "label": "AION Box",
            "capacity": "small team, sustained local inference and private shared services",
        },
        "level_3_single_gpu_rack": {
            "label": "Single-GPU rack",
            "capacity": "department concurrency, larger models and governed background operators",
        },
        "level_4_private_cluster": {
            "label": "Private cluster or customer cloud",
            "capacity": "multi-unit concurrency, resilience and regulated or high-volume workloads",
        },
    }

    @classmethod
    def recommend(cls, *, tenant_id: str, observation_days: int, peak_concurrency: int,
                  verified_actions_per_day: int, model_tokens_per_day: int,
                  visual_frames_per_day: int, private_data_gb: float,
                  p95_latency_ms: int, availability_target: float,
                  offline_required: bool, regulated_data: bool,
                  multi_location: bool, evidence_ref: str) -> Dict[str, Any]:
        if not tenant_id or not evidence_ref or not 1 <= int(observation_days) <= 366:
            raise ValueError("capacity_evidence_invalid")
        nonnegative = (peak_concurrency, verified_actions_per_day, model_tokens_per_day,
                       visual_frames_per_day, private_data_gb, p95_latency_ms)
        if any(float(value) < 0 for value in nonnegative):
            raise ValueError("capacity_measurement_invalid")
        if not 0.9 <= float(availability_target) <= 0.99999:
            raise ValueError("availability_target_invalid")

        score = 0
        reasons = []
        if peak_concurrency > 3:
            score += 1; reasons.append("more_than_three_concurrent_users")
        if peak_concurrency > 15:
            score += 2; reasons.append("department_scale_concurrency")
        if model_tokens_per_day > 2_000_000 or visual_frames_per_day > 20_000:
            score += 1; reasons.append("sustained_inference_workload")
        if model_tokens_per_day > 20_000_000 or visual_frames_per_day > 200_000:
            score += 2; reasons.append("high_volume_inference_workload")
        if verified_actions_per_day > 500:
            score += 1; reasons.append("sustained_operator_throughput")
        if availability_target >= 0.999:
            score += 2; reasons.append("high_availability_target")
        if regulated_data:
            score += 1; reasons.append("regulated_data_controls")
        if multi_location:
            score += 1; reasons.append("multi_location_operation")
        if private_data_gb > 1000:
            score += 1; reasons.append("large_private_data_volume")

        if score >= 6:
            level = "level_4_private_cluster"
        elif score >= 3:
            level = "level_3_single_gpu_rack"
        elif score >= 1:
            level = "level_2_aion_box"
        else:
            level = "level_1_existing_machine"
        if offline_required and level == "level_4_private_cluster":
            deployment = "customer_site_private_cluster"
        elif offline_required:
            deployment = "customer_site"
        else:
            deployment = "customer_choice_local_or_private_cloud"

        confidence = "qualified" if observation_days >= 30 else "provisional"
        result = {
            "schema_version": "aion.sovereign_capacity_recommendation.v1",
            "tenant_id_hash": canonical_hash(tenant_id), "recommendation": level,
            "label": cls.LEVELS[level]["label"], "capacity_description": cls.LEVELS[level]["capacity"],
            "deployment": deployment, "confidence": confidence,
            "observation_days": observation_days, "reasons": reasons or ["current_workload_within_existing_machine_profile"],
            "evidence_hash": canonical_hash(evidence_ref),
            "assumptions": ["workload remains within observed order of magnitude", "model sizes and quantisation are selected separately"],
            "financial_claim": None, "vendor_selected": False,
            "customer_content_included": False, "generated_at": utc_now_iso(),
        }
        result["recommendation_hash"] = canonical_hash(result)
        return result
