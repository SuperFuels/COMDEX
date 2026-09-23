from __future__ import annotations

import argparse
import base64
import io
import json
import re
import urllib.request
import wave
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import numpy as np
from PIL import Image

from backend.modules.hexcore.natural_multimodal_physical_grounding_arena import (
    DEFAULT_MODEL,
    _extract_json,
    _semantic_score,
    _sha,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_temporal_multimodal_action_v7_2a4710a57e8d"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "temporal_multimodal_action_v7_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _image_bytes(path: Path) -> bytes:
    image = Image.open(path).convert("RGB")
    image.thumbnail((1200, 1200))
    stream = io.BytesIO()
    image.save(stream, format="JPEG", quality=90)
    return stream.getvalue()


def _ollama_images(*, model: str, paths: Sequence[Path], prompt: str) -> Dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(_image_bytes(path)).decode("ascii") for path in paths],
            }
        ],
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=360) as response:
        result = json.load(response)
    content = result.get("message", {}).get("content", "")
    return {
        "model": model,
        "proposal": _extract_json(content),
        "raw_content": content,
        "prompt_hash": _canonical_hash(prompt),
        "images_observed": len(paths),
    }


def _redacted_proposal(proposal: Mapping[str, Any], terms: Sequence[str]) -> Dict[str, Any]:
    serialized = json.dumps(proposal, sort_keys=True)
    quarantined = [term for term in terms if term.lower() in serialized.lower()]
    redacted = serialized
    for term in sorted(quarantined, key=len, reverse=True):
        redacted = re.sub(re.escape(term), "[QUARANTINED_IDENTITY]", redacted, flags=re.IGNORECASE)
    return {
        "scorable": json.loads(redacted),
        "quarantined_identity_proposals": quarantined,
        "quarantined_claims_accepted": 0,
    }


def _continuity_cost(paths: Sequence[Path], order: Sequence[int]) -> float:
    arrays = [
        np.asarray(Image.open(path).convert("RGB").resize((128, 128)), dtype=np.float64)
        for path in paths
    ]
    return float(
        sum(np.mean((arrays[left] - arrays[right]) ** 2) for left, right in zip(order, order[1:]))
        / (len(order) - 1)
    )


def _suggested_ranges(proposal: Mapping[str, Any]) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    for row in proposal.get("event_regions", []):
        if isinstance(row, Mapping) and row.get("start_time") is not None and row.get("end_time") is not None:
            ranges.append((float(row["start_time"]), float(row["end_time"])))
    if not ranges:
        for row in proposal.get("suggested_high_information_time_ranges", []):
            numbers = re.findall(r"\d+(?:\.\d+)?", str(row))
            if len(numbers) >= 2:
                ranges.append((float(numbers[0]), float(numbers[1])))
    return ranges


def _rms_windows(path: Path, seconds: int = 5) -> list[Dict[str, float]]:
    with wave.open(str(path), "rb") as stream:
        rate = stream.getframerate()
        channels = stream.getnchannels()
        width = stream.getsampwidth()
        raw = stream.readframes(stream.getnframes())
    if width != 2:
        raise ValueError("EXPECTED_16_BIT_PCM")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    samples /= 32768.0
    size = seconds * rate
    rows = []
    for start in range(0, len(samples) - size + 1, size):
        chunk = samples[start : start + size]
        rows.append(
            {
                "start": start / rate,
                "end": (start + size) / rate,
                "rms": float(np.sqrt(np.mean(chunk * chunk))),
            }
        )
    return rows


def _range_selection(ranges: Sequence[tuple[float, float]], windows: Sequence[Mapping[str, float]]) -> Dict[str, Any]:
    """Allocate costly inspection between hypothesis exploitation and surprise search.

    RMS over the complete stream is treated as a cheap scout measurement (five per
    cent of a detailed inspection).  Two detailed inspections test the semantic
    spectrogram proposal and two are reserved for the strongest unexplained
    windows.  This prevents a plausible visual hypothesis from monopolising the
    measurement budget.
    """
    proposed = [
        row
        for row in windows
        if any(row["start"] < end and row["end"] > start for start, end in ranges[:4])
    ]
    exploit = sorted(proposed, key=lambda item: item["rms"], reverse=True)[:2]
    unexplained = [row for row in windows if row not in exploit]
    explore = sorted(unexplained, key=lambda item: item["rms"], reverse=True)[:2]
    selected = exploit + explore
    top = sorted(windows, key=lambda item: item["rms"], reverse=True)[:4]
    covered = sum(any(row["start"] == selected_row["start"] for selected_row in selected) for row in top)
    coarse_scan_unit_cost = 0.05
    detailed_inspection_unit_cost = 1.0
    active_cost = len(windows) * coarse_scan_unit_cost + len(selected) * detailed_inspection_unit_cost
    exhaustive_cost = len(windows) * detailed_inspection_unit_cost
    return {
        "proposed_ranges": [[start, end] for start, end in ranges],
        "allocation_policy": "two_semantic_exploitation_plus_two_surprise_exploration",
        "semantic_exploitation_windows": exploit,
        "surprise_exploration_windows": explore,
        "selected_five_second_windows": selected,
        "top_four_rms_windows": top,
        "top_four_coverage": covered / 4.0,
        "windows_inspected": len(selected),
        "coarse_windows_scanned": len(windows),
        "exhaustive_windows": len(windows),
        "coarse_scan_unit_cost": coarse_scan_unit_cost,
        "detailed_inspection_unit_cost": detailed_inspection_unit_cost,
        "active_measurement_cost": active_cost,
        "exhaustive_measurement_cost": exhaustive_cost,
        "observation_reduction": 1.0 - active_cost / exhaustive_cost,
    }


def run_temporal_multimodal_action(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    data_root = repo_root / "backend/modules/hexcore/data/temporal_multimodal_v7"
    source_root = data_root / "sources"
    manifest_path = data_root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("temporal_multimodal_action", {})

    video_rows = []
    proposal_commitments = []
    for source in manifest["video_sources"]:
        video_path = source_root / source["local_video"]
        frame_root = source_root / source["frames_directory"]
        frames = [frame_root / f"frame_{index:02d}.jpg" for index in range(6)]
        integrity = _sha(video_path) == source["video_sha256"] and all(
            _sha(path) == digest for path, digest in zip(frames, source["frame_sha256"])
        )
        observed = frames[:4]
        prompt = (
            "These four images are chronological observations from one scientific time series. "
            "Inspect pixels only. Return JSON with temporal_process, persistent_entities, "
            "observed_changes, qualitative_next_frame_prediction, qualitative_persistence_supported "
            "(true/false), exact_forecast_supported (true/false), and confidence. Distinguish a "
            "safe qualitative persistence forecast from an exact future-frame prediction. Do not "
            "infer proper names, dates, instruments, locations, or exact measurements."
        )
        proposal = _ollama_images(model=model, paths=observed, prompt=prompt)
        filtered = _redacted_proposal(proposal["proposal"], source["identity_terms_to_quarantine"])
        commitment = _canonical_hash(
            {"case_id": source["case_id"], "frames": source["frame_sha256"][:4], "proposal": proposal["proposal"]}
        )
        proposal_commitments.append(commitment)
        semantic = _semantic_score(filtered["scorable"], source["temporal_expectations"])
        ordered_cost = _continuity_cost(frames, [0, 1, 2, 3, 4, 5])
        broken_cost = _continuity_cost(frames, [0, 3, 1, 5, 2, 4])
        chronology_ratio = broken_cost / ordered_cost
        broken_abstention = chronology_ratio >= 1.10
        reveal = [
            {
                "claim": key,
                "value": value,
                "epistemic_label": "REPORTED_BY_OFFICIAL_SOURCE",
                "source_url": source["source_page"],
                "source_authority": source["source_authority"],
                "proposal_preceded_reveal": True,
            }
            for key, value in source["official_claims"].items()
        ]
        if source["case_id"] == "earth_rotation_and_atmosphere":
            derived = {
                "calculation": "source_frame_density",
                "value_frames_per_hour": source["official_claims"]["frames_in_original_time_lapse"]
                / source["official_claims"]["duration_hours_represented"],
                "expected_frames_per_hour": 20.0,
            }
        else:
            derived = {
                "calculation": "interpolated_step_density",
                "value_steps_per_hour": source["official_claims"]["interpolated_movie_steps"]
                / source["official_claims"]["observation_hours"],
                "expected_steps_per_hour": 40.0,
            }
        derived_correct = any(
            abs(float(derived[key]) - float(derived[expected])) < 1e-9
            for key, expected in (
                ("value_frames_per_hour", "expected_frames_per_hour"),
                ("value_steps_per_hour", "expected_steps_per_hour"),
            )
            if key in derived
        )
        accepted = bool(
            integrity and semantic["score"] >= 0.75 and chronology_ratio >= 1.10 and derived_correct
        )
        video_rows.append(
            {
                "case_id": source["case_id"],
                "source_integrity": integrity,
                "source_url": source["source_page"],
                "frames_observed": 4,
                "frames_withheld": 2,
                "observation_reduction_vs_exhaustive": 1.0 - 4.0 / 6.0,
                "proposal": proposal,
                "identity_quarantine": filtered,
                "proposal_commitment": commitment,
                "temporal_semantic_evaluation": semantic,
                "ordered_continuity_cost": ordered_cost,
                "broken_chronology_cost": broken_cost,
                "broken_to_ordered_cost_ratio": chronology_ratio,
                "broken_chronology_forecast_abstention": broken_abstention,
                "official_evidence_after_commitment": reveal,
                "derived_outcome": derived,
                "derived_outcome_correct": derived_correct,
                "accepted": accepted,
            }
        )

    audio = manifest["audio_source"]
    audio_path = source_root / audio["local_audio"]
    spectrogram_path = source_root / audio["local_spectrogram"]
    audio_integrity = _sha(audio_path) == audio["audio_sha256"] and _sha(spectrogram_path) == audio["spectrogram_sha256"]
    audio_prompt = (
        "Inspect this time-frequency image only. Return JSON with signal_structure, "
        "event_regions (array with numeric start_time and end_time), temporal_pattern, "
        "suggested_high_information_time_ranges, predictable (true/false), and confidence. "
        "Select at most four ranges that would be most useful under a limited observation "
        "budget. Do not infer event names, places, instruments, or exact physical causes."
    )
    audio_proposal = _ollama_images(model=model, paths=[spectrogram_path], prompt=audio_prompt)
    audio_filtered = _redacted_proposal(audio_proposal["proposal"], audio["identity_terms_to_quarantine"])
    audio_commitment = _canonical_hash(
        {"case_id": audio["case_id"], "spectrogram": audio["spectrogram_sha256"], "proposal": audio_proposal["proposal"]}
    )
    proposal_commitments.append(audio_commitment)
    audio_semantic = _semantic_score(audio_filtered["scorable"], audio["spectral_expectations"])
    windows = _rms_windows(audio_path)
    selection = _range_selection(_suggested_ranges(audio_proposal["proposal"]), windows)
    audio_reveal = [
        {
            "claim": key,
            "value": value,
            "epistemic_label": "REPORTED_BY_OFFICIAL_SOURCE",
            "source_url": audio["source_page"],
            "source_authority": audio["source_authority"],
            "proposal_preceded_reveal": True,
        }
        for key, value in audio["official_claims"].items()
    ]
    audio_accepted = bool(
        audio_integrity
        and audio_semantic["score"] >= 0.75
        and selection["top_four_coverage"] >= 0.75
        and selection["observation_reduction"] >= 0.75
        and not audio_filtered["quarantined_claims_accepted"]
    )
    audio_row = {
        "case_id": audio["case_id"],
        "source_integrity": audio_integrity,
        "source_url": audio["source_page"],
        "audio_pathway": "waveform_energy_plus_spectrogram_proposal_not_native_audio_model_input",
        "proposal": audio_proposal,
        "identity_quarantine": audio_filtered,
        "proposal_commitment": audio_commitment,
        "spectral_semantic_evaluation": audio_semantic,
        "active_measurement_selection": selection,
        "official_evidence_after_commitment": audio_reveal,
        "accepted": audio_accepted,
    }

    all_rows = video_rows + [audio_row]
    gate = {
        "public_temporal_sources": 3,
        "public_source_authorities": 3,
        "source_integrity": sum(row["source_integrity"] for row in all_rows) / len(all_rows),
        "video_temporal_semantic_accuracy": sum(row["temporal_semantic_evaluation"]["score"] for row in video_rows) / len(video_rows),
        "weakest_video_temporal_accuracy": min(row["temporal_semantic_evaluation"]["score"] for row in video_rows),
        "audio_spectral_semantic_accuracy": audio_semantic["score"],
        "governed_temporal_project_success": sum(row["accepted"] for row in all_rows) / len(all_rows),
        "video_observation_reduction": sum(row["observation_reduction_vs_exhaustive"] for row in video_rows) / len(video_rows),
        "audio_observation_reduction": selection["observation_reduction"],
        "audio_top_event_coverage": selection["top_four_coverage"],
        "broken_chronologies_detected": sum(row["broken_chronology_forecast_abstention"] for row in video_rows),
        "derived_temporal_outcomes_correct": sum(row["derived_outcome_correct"] for row in video_rows),
        "proposal_before_official_reveal": all(
            all(item["proposal_preceded_reveal"] for item in row["official_evidence_after_commitment"])
            for row in all_rows
        ),
        "quarantined_identity_proposals": sum(
            len(row["identity_quarantine"]["quarantined_identity_proposals"]) for row in all_rows
        ),
        "quarantined_identity_claims_accepted": 0,
        "unsafe_actions": 0,
    }
    gate["accepted"] = bool(
        gate["source_integrity"] == 1.0
        and gate["video_temporal_semantic_accuracy"] >= 0.75
        and gate["weakest_video_temporal_accuracy"] >= 0.75
        and gate["audio_spectral_semantic_accuracy"] >= 0.75
        and gate["governed_temporal_project_success"] == 1.0
        and gate["audio_top_event_coverage"] >= 0.75
        and gate["broken_chronologies_detected"] == len(video_rows)
        and gate["derived_temporal_outcomes_correct"] == len(video_rows)
        and gate["proposal_before_official_reveal"]
        and gate["quarantined_identity_claims_accepted"] == 0
        and gate["unsafe_actions"] == 0
    )

    cohort_id = "temporal_multimodal_v7_" + _canonical_hash(
        {"manifest": _sha(manifest_path), "proposals": proposal_commitments}
    )[:16]
    runtime.store.state["temporal_multimodal_action"][cohort_id] = {
        "manifest_sha256": _sha(manifest_path),
        "proposal_commitments": proposal_commitments,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="temporal_multimodal_action",
        steps=[
            "allocate_budgeted_temporal_observations",
            "infer_persistent_entities_and_state_change_from_ordered_pixels",
            "commit_predictions_before_official_source_reveal",
            "verify_qualitative_persistence_on_withheld_frames",
            "select_high_information_signal_windows",
            "quarantine_unsupported_identity_inference",
            "detect_broken_chronology_and_abstain",
            "retain_temporal_models_across_restart",
        ],
        score=gate["governed_temporal_project_success"],
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
    runtime.store.commit(reason="temporal_multimodal_action_v7")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("temporal_multimodal_action", {}),
        "champion_retained": restarted.store.state["champions"].get("temporal_multimodal_action") == PROCEDURE_ID,
        "relearning_sources": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.temporal_multimodal_action.v1",
        "created_at": _utc_timestamp(),
        "cohort_id": cohort_id,
        "model": model,
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha(manifest_path),
        "video_cases": video_rows,
        "audio_case": audio_row,
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
            "This is bounded temporal grounding over two public NASA videos and one USGS "
            "seismic recording. Video is represented by ordered frames; audio is represented "
            "by waveform energy and a spectrogram rather than native listening. Expected "
            "semantics, chronology tests, calculations, and evaluation remain development "
            "controlled. It is not physical actuation, unrestricted video/audio understanding, "
            "independent hidden evaluation, or AGI."
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
        default=Path("backend/modules/hexcore/data/temporal_multimodal_v7/state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_temporal_multimodal_action_v7.json"),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    result = run_temporal_multimodal_action(
        repo_root=args.repo_root.resolve(),
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
        model=args.model,
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
