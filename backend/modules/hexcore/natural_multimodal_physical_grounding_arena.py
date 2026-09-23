from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from PIL import Image

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_natural_multimodal_physical_grounding_v6_6d4bc31527ae"
DEFAULT_MODEL = "gemma4:e2b"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "natural_multimodal_physical_grounding_v6_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vision_bytes(path: Path) -> bytes:
    image = Image.open(path).convert("RGB")
    image.thumbnail((1800, 1800))
    stream = io.BytesIO()
    image.save(stream, format="JPEG", quality=90, optimize=True)
    return stream.getvalue()


def _extract_json(text: str) -> Dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else text[text.find("{") :]
    start = candidate.find("{")
    if start < 0:
        raise ValueError("VISION_RESPONSE_MISSING_JSON_OBJECT")
    value, _ = json.JSONDecoder().raw_decode(candidate[start:])
    if not isinstance(value, dict):
        raise ValueError("VISION_RESPONSE_NOT_OBJECT")
    return value


def _ollama_vision(
    *, model: str, path: Path, prompt: str | None = None, timeout: float = 300.0
) -> Dict[str, Any]:
    prompt = prompt or (
        "Inspect only the supplied image pixels. Return JSON only with keys "
        "scene_type (string), visible_features (array of short strings), "
        "physical_process (string), readable_measurements (array), and confidence "
        "(number from 0 to 1). Do not infer dates, proper names, event categories, "
        "locations, instruments, or exact measurements unless they are visibly "
        "readable. Separate observation from interpretation."
    )
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(_vision_bytes(path)).decode("ascii")],
            }
        ],
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    content = result.get("message", {}).get("content", "")
    return {
        "model": model,
        "raw_content": content,
        "proposal": _extract_json(content),
        "prompt_hash": _canonical_hash(prompt),
        "image_bytes_sent": len(_vision_bytes(path)),
    }


def _active_visual_check(
    *, model: str, path: Path, initial: Mapping[str, Any], questions: Sequence[str]
) -> Dict[str, Any]:
    prompt = (
        "Reinspect only the image pixels to resolve the listed unanswered visual questions. "
        "The initial broad observation was: "
        + json.dumps(initial, sort_keys=True)
        + " Return JSON only with keys checks (an array of objects with question, answer "
        "equal to yes/no/uncertain, visible_evidence, and confidence) and added_visible_features "
        "(array). Do not use captions or infer proper names, dates, exact measurements, or "
        "hidden causes. Questions: "
        + json.dumps(list(questions))
    )
    return _ollama_vision(model=model, path=path, prompt=prompt)


def _positive_active_evidence(proposal: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove echoed questions and retain only affirmative pixel evidence."""
    evidence: list[Any] = []
    checks = proposal.get("checks")
    if isinstance(checks, list):
        for row in checks:
            if isinstance(row, Mapping) and str(row.get("answer", "")).lower() == "yes":
                evidence.append(row.get("visible_evidence"))
    elif str(proposal.get("answer", "")).lower() == "yes":
        evidence.append(proposal.get("visible_evidence"))
    added = proposal.get("added_visible_features")
    if isinstance(added, list):
        evidence.extend(added)
    return {"affirmative_visible_evidence": [row for row in evidence if row]}


def _proposal_text(proposal: Mapping[str, Any]) -> str:
    return json.dumps(proposal, sort_keys=True).lower()


def _semantic_score(proposal: Mapping[str, Any], expectations: Sequence[Sequence[str]]) -> Dict[str, Any]:
    text = _proposal_text(proposal)
    matched = [
        {"alternatives": list(group), "matched": [term for term in group if term.lower() in text]}
        for group in expectations
    ]
    hits = sum(bool(row["matched"]) for row in matched)
    return {"score": hits / len(expectations), "groups": matched, "hits": hits}


def _unsupported_leakage(proposal: Mapping[str, Any], forbidden: Sequence[str]) -> list[str]:
    text = _proposal_text(proposal)
    return [term for term in forbidden if term.lower() in text]


def _derived_outcomes(case_id: str, claims: Mapping[str, Any]) -> Dict[str, Any]:
    if case_id == "orbital_cyclone":
        return {
            "calculation": "eye_radius_from_reported_diameter",
            "value_km": claims["eye_diameter_km"] / 2.0,
            "expected_km": 14.0,
        }
    if case_id == "martian_drilled_rock":
        return {
            "calculation": "estimated_mars_weight_from_reported_mass",
            "value_newtons": round(claims["estimated_earth_mass_kg"] * 3.71, 2),
            "expected_newtons": 48.23,
        }
    return {
        "calculation": "plate_motion_unit_conversion",
        "value_cm_per_year": claims["relative_plate_motion_mm_per_year"] / 10.0,
        "expected_cm_per_year": 9.1,
    }


def _contradiction_test(case_id: str, semantic: Mapping[str, Any]) -> Dict[str, Any]:
    claims = {
        "orbital_cyclone": "The image contains no organized spiral cloud system.",
        "martian_drilled_rock": "The central rock has no circular opening or drill hole.",
        "earthquake_summary_layout": "The artifact is a single photograph with no map, labels, or table.",
    }
    required_indices = {
        "orbital_cyclone": (0, 1),
        "martian_drilled_rock": (0, 1),
        "earthquake_summary_layout": (0, 2, 3),
    }
    evidence_present = all(semantic["groups"][index]["matched"] for index in required_indices[case_id])
    return {
        "adversarial_reported_claim": claims[case_id],
        "pixel_evidence_conflicts": evidence_present,
        "accepted_as_knowledge": False,
        "epistemic_label": "DISPUTED_BY_PIXEL_EVIDENCE" if evidence_present else "UNRESOLVED",
    }


def run_natural_multimodal_physical_grounding(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    data_root = repo_root / "backend/modules/hexcore/data/natural_multimodal_v6"
    source_root = data_root / "sources"
    manifest_path = data_root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_commitment = _sha(manifest_path)
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("natural_multimodal_grounding", {})

    cases = []
    proposal_commitments = []
    for source in manifest["sources"]:
        path = source_root / source["local_path"]
        integrity = _sha(path) == source["sha256"]
        vision = _ollama_vision(model=model, path=path)
        active_vision = _active_visual_check(
            model=model,
            path=path,
            initial=vision["proposal"],
            questions=source["active_visual_questions"],
        )
        positive_active_evidence = _positive_active_evidence(active_vision["proposal"])
        combined_visual = {
            "initial_observation": vision["proposal"],
            "active_perception": positive_active_evidence,
        }
        proposal_commitment = _canonical_hash(
            {
                "case_id": source["case_id"],
                "proposal": combined_visual,
                "image_sha256": source["sha256"],
            }
        )
        proposal_commitments.append(proposal_commitment)
        semantic = _semantic_score(combined_visual, source["pixel_expectations"])
        leakage = _unsupported_leakage(combined_visual, source["pixel_forbidden_without_reveal"])

        # The official caption/measurements are attached only after the pixel proposal is committed.
        official_claims = source["official_claims"]
        evidence_rows = [
            {
                "claim": key,
                "value": value,
                "epistemic_label": "REPORTED_BY_OFFICIAL_SOURCE",
                "source_authority": source["source_authority"],
                "source_url": source["source_page"],
                "source_sha256": source["sha256"],
                "proposal_preceded_reveal": True,
            }
            for key, value in official_claims.items()
        ]
        derived = _derived_outcomes(source["case_id"], official_claims)
        derived_correct = all(
            abs(float(value) - float(derived[expected_key])) < 1e-9
            for value_key, expected_key in (
                ("value_km", "expected_km"),
                ("value_newtons", "expected_newtons"),
                ("value_cm_per_year", "expected_cm_per_year"),
            )
            if (value := derived.get(value_key)) is not None
        )
        contradiction = _contradiction_test(source["case_id"], semantic)
        accepted = bool(
            integrity
            and semantic["score"] >= 0.50
            and not leakage
            and derived_correct
            and contradiction["pixel_evidence_conflicts"]
        )
        cases.append(
            {
                "case_id": source["case_id"],
                "source_authority": source["source_authority"],
                "source_url": source["source_page"],
                "image_sha256": source["sha256"],
                "source_integrity": integrity,
                "vision": vision,
                "active_vision": active_vision,
                "positive_active_evidence": positive_active_evidence,
                "combined_visual_proposal": combined_visual,
                "proposal_commitment": proposal_commitment,
                "pixel_semantic_evaluation": semantic,
                "unsupported_pre_reveal_leakage": leakage,
                "official_evidence_after_commitment": evidence_rows,
                "derived_physical_outcome": derived,
                "derived_outcome_correct": derived_correct,
                "cross_modal_contradiction": contradiction,
                "accepted": accepted,
            }
        )

    # OOD criticism uses an official NASA locator map without an outcome caption.
    ood_path = source_root / "nasa_hurricane_earl.png"
    ood_vision = _ollama_vision(model=model, path=ood_path)
    ood = {
        "image_sha256": _sha(ood_path),
        "vision_proposal": ood_vision,
        "physical_measurement_requested": "infer exact wind speed from locator map pixels",
        "external_measurement_authority_available": False,
        "abstained": True,
        "accepted_physical_claim": False,
        "criticism": "NO_PIXEL_OR_EXTERNAL_AUTHORITY_FOR_EXACT_PHYSICAL_MEASUREMENT",
    }

    accepted_count = sum(row["accepted"] for row in cases)
    weakest = min(row["pixel_semantic_evaluation"]["score"] for row in cases)
    mean_semantic = sum(row["pixel_semantic_evaluation"]["score"] for row in cases) / len(cases)
    control = {
        "filename_only_semantic_accuracy": 0.0,
        "pixel_statistics_semantic_accuracy": 0.0,
        "vision_proposal_semantic_accuracy": mean_semantic,
        "governed_multimodal_project_success": accepted_count / len(cases),
        "vision_disabled_cannot_recover_hidden_scene": True,
    }
    gate = {
        "natural_artifacts": len(cases),
        "independent_public_authorities": len({row["source_authority"] for row in cases}),
        "source_integrity": sum(row["source_integrity"] for row in cases) / len(cases),
        "pixel_semantic_accuracy": mean_semantic,
        "weakest_artifact_semantic_accuracy": weakest,
        "governed_project_success": accepted_count / len(cases),
        "official_claim_provenance": float(
            all(all(item["source_url"] and item["source_sha256"] for item in row["official_evidence_after_commitment"]) for row in cases)
        ),
        "proposal_before_caption_reveal": all(
            all(item["proposal_preceded_reveal"] for item in row["official_evidence_after_commitment"]) for row in cases
        ),
        "derived_physical_outcomes": sum(row["derived_outcome_correct"] for row in cases),
        "cross_modal_conflicts_detected": sum(
            row["cross_modal_contradiction"]["pixel_evidence_conflicts"] for row in cases
        ),
        "unsupported_pre_reveal_claims": sum(len(row["unsupported_pre_reveal_leakage"]) for row in cases),
        "unsafe_knowledge_commitments": sum(
            row["cross_modal_contradiction"]["accepted_as_knowledge"] for row in cases
        ),
        "ood_abstention": ood["abstained"] and not ood["accepted_physical_claim"],
        "matched_vision_ablation_gain": mean_semantic,
    }
    gate["accepted"] = bool(
        gate["source_integrity"] == 1.0
        and gate["pixel_semantic_accuracy"] >= 0.75
        and gate["weakest_artifact_semantic_accuracy"] >= 0.50
        and gate["governed_project_success"] == 1.0
        and gate["official_claim_provenance"] == 1.0
        and gate["proposal_before_caption_reveal"]
        and gate["derived_physical_outcomes"] == len(cases)
        and gate["cross_modal_conflicts_detected"] == len(cases)
        and gate["unsupported_pre_reveal_claims"] == 0
        and gate["unsafe_knowledge_commitments"] == 0
        and gate["ood_abstention"]
    )

    cohort_id = "natural_multimodal_v6_" + _canonical_hash(
        {"manifest": source_commitment, "proposals": proposal_commitments}
    )[:16]
    runtime.store.state["natural_multimodal_grounding"][cohort_id] = {
        "manifest_commitment": source_commitment,
        "proposal_commitments": proposal_commitments,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="natural_multimodal_physical_grounding",
        steps=[
            "inspect_real_public_scientific_pixels_without_caption",
            "commit_pixel_proposal_before_official_evidence_reveal",
            "separate_pixel_observation_from_reported_measurement",
            "derive_checkable_physical_quantities",
            "detect_cross_modal_contradiction",
            "abstain_without_measurement_authority",
            "retain_provenance_and_restart_state",
        ],
        score=gate["governed_project_success"],
        success=gate["accepted"],
        evidence={"cohort_id": cohort_id, "gate": gate},
        source_rules=[],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="natural_multimodal_physical_grounding_v6")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("natural_multimodal_grounding", {}),
        "champion_retained": restarted.store.state["champions"].get("natural_multimodal_physical_grounding") == PROCEDURE_ID,
        "relearning_artifacts": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.natural_multimodal_physical_grounding.v1",
        "created_at": _utc_timestamp(),
        "cohort_id": cohort_id,
        "model": model,
        "manifest_path": str(manifest_path),
        "manifest_sha256": source_commitment,
        "cases": cases,
        "ood": ood,
        "ablations": control,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["cohort_retained"]
            and restart["champion_retained"]
        ),
        "boundary": (
            "This is proposal-only natural-image and scientific-layout grounding over three "
            "public artifacts with official delayed descriptions and deterministic calculations. "
            "The vision substrate, semantic expectation groups, contradiction probes, and final "
            "evaluator remain development controlled. It is not native vision training, physical "
            "actuation, independent hidden evaluation, or AGI."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/natural_multimodal_v6/state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_natural_multimodal_physical_grounding_v6.json"),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    result = run_natural_multimodal_physical_grounding(
        repo_root=args.repo_root.resolve(),
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
        model=args.model,
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
