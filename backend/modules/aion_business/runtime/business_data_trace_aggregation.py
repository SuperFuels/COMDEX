from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_business.runtime.business_data_discovery_scenarios import (
    load_discovery_scenario_catalogue,
)
from backend.modules.aion_business.runtime.business_data_write_tracer import TRACE_SCHEMA


class BusinessDataTraceAggregationError(ValueError):
    pass


EXPECTED_EVIDENCE_KIND = {
    "desktop_backend": "process_write_observations",
    "filesystem_import": "process_write_observations",
    "update_runner": "process_write_observations",
    "electron_main": "process_write_observations",
    "desktop_renderer": "browser_storage_observations",
    "provider_sandbox": "external_surface_observations",
    "mobile_companion": "external_surface_observations",
}


def _read(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BusinessDataTraceAggregationError(
            f"discovery_fragment_invalid:{path.name}"
        ) from exc
    if payload.get("schema_version") != TRACE_SCHEMA:
        raise BusinessDataTraceAggregationError(
            f"discovery_fragment_schema_invalid:{path.name}"
        )
    return payload


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def aggregate_discovery_session_fragments(
    *,
    manifest_path: str | Path,
    catalogue_path: str | Path,
    trace_root: str | Path,
    session_id: str,
) -> dict[str, Any]:
    """Combine required process/surface fragments into one campaign trace.

    The aggregate cannot pass while any declared execution surface is missing,
    incomplete, truncated, unsafe, mismatched or empty across the whole journey.
    """

    trace_root = Path(trace_root)
    catalogue = load_discovery_scenario_catalogue(
        catalogue_path=catalogue_path,
        manifest_path=manifest_path,
    )
    indexed = {str(item["session_id"]): item for item in catalogue["scenarios"]}
    if session_id not in indexed:
        raise BusinessDataTraceAggregationError(
            f"discovery_session_not_catalogued:{session_id}"
        )
    scenario = indexed[session_id]
    required_surfaces = sorted({str(item) for item in scenario["execution_surfaces"]})
    expected_paths = {
        surface: trace_root / f"{session_id}.{surface}.json"
        for surface in required_surfaces
    }
    expected_domains = sorted({str(item) for item in scenario["expected_domains"]})
    expected_external_classes = sorted({
        str(item) for item in scenario["expected_external_classes"] if item != "none"
    })
    unexpected = sorted(
        path.name
        for path in trace_root.glob(f"{session_id}.*.json")
        if path.name not in {item.name for item in expected_paths.values()}
    )
    if unexpected:
        raise BusinessDataTraceAggregationError(
            "discovery_fragment_surface_unexpected:" + ",".join(unexpected)
        )

    fragments: list[tuple[str, Path, dict[str, Any]]] = []
    missing: list[str] = []
    for surface, fragment_path in expected_paths.items():
        if not fragment_path.is_file():
            missing.append(surface)
            continue
        payload = _read(fragment_path)
        if payload.get("session_id") != session_id:
            raise BusinessDataTraceAggregationError(
                f"discovery_fragment_session_mismatch:{surface}"
            )
        if payload.get("surface") != surface:
            raise BusinessDataTraceAggregationError(
                f"discovery_fragment_surface_mismatch:{surface}"
            )
        if payload.get("evidence_kind") != EXPECTED_EVIDENCE_KIND[surface]:
            raise BusinessDataTraceAggregationError(
                f"discovery_fragment_evidence_kind_invalid:{surface}"
            )
        if surface in {"provider_sandbox", "mobile_companion"}:
            expected_external = sorted({
                str(value)
                for value in scenario["expected_external_classes"]
                if value != "none"
            })
            declared_external = sorted({
                str(value) for value in payload.get("expected_external_classes") or []
            })
            observed_external = sorted({
                str(value) for value in payload.get("observed_external_classes") or []
            })
            if (
                declared_external != expected_external
                or observed_external != expected_external
                or payload.get("release_gate_passed") is not True
            ):
                raise BusinessDataTraceAggregationError(
                    f"discovery_fragment_external_coverage_invalid:{surface}"
                )
        fragments.append((surface, fragment_path, payload))

    events: list[dict[str, Any]] = []
    grouped: Counter[tuple[str, str, str, int, str]] = Counter()
    destination_counts: Counter[str] = Counter()
    dropped = unsafe = 0
    all_complete = not missing
    fragment_digests: dict[str, str] = {}
    scenarios: set[str] = set()
    observed_domains: set[str] = set()
    observed_external_classes: set[str] = set()
    for surface, fragment_path, payload in fragments:
        fragment_digests[surface] = _digest(fragment_path)
        scenarios.add(str(payload.get("scenario") or ""))
        if payload.get("scenario_completed") is not True or payload.get("complete") is not True:
            all_complete = False
        if payload.get("release_gate_passed") is not True:
            all_complete = False
        fragment_domains = payload.get("observed_vault_domains") or []
        if (
            not isinstance(fragment_domains, list)
            or any(not isinstance(item, str) or not item for item in fragment_domains)
        ):
            raise BusinessDataTraceAggregationError(
                f"discovery_fragment_domain_coverage_invalid:{surface}"
            )
        observed_domains.update(fragment_domains)
        fragment_external = payload.get("observed_external_classes") or []
        if (
            not isinstance(fragment_external, list)
            or any(not isinstance(item, str) or not item for item in fragment_external)
        ):
            raise BusinessDataTraceAggregationError(
                f"discovery_fragment_external_coverage_invalid:{surface}"
            )
        observed_external_classes.update(fragment_external)
        dropped += int(payload.get("dropped_event_count", -1))
        unsafe += int(payload.get("unsafe_write_count", -1))
        for destination, count in dict(payload.get("destination_counts") or {}).items():
            destination_counts[str(destination)] += int(count)
        for event in list(payload.get("events") or []):
            item = dict(event)
            item["surface"] = surface
            events.append(item)
        for item in list(payload.get("grouped_source_operations") or []):
            grouped[
                (
                    str(item.get("operation") or ""),
                    str(item.get("destination_class") or ""),
                    str(item.get("source_path") or ""),
                    int(item.get("line", 0)),
                    surface,
                )
            ] += int(item.get("count", 0))
    if len(scenarios) > 1:
        raise BusinessDataTraceAggregationError("discovery_fragment_scenario_mismatch")

    missing_domains = sorted(set(expected_domains) - observed_domains)
    unexpected_domains = sorted(observed_domains - set(expected_domains))
    missing_external_classes = sorted(
        set(expected_external_classes) - observed_external_classes
    )
    unexpected_external_classes = sorted(
        observed_external_classes - set(expected_external_classes)
    )
    report = {
        "schema_version": TRACE_SCHEMA,
        "session_id": session_id,
        "scenario": next(iter(scenarios), session_id),
        "surface": "aggregated",
        "privacy": "source_locations_registered_domain_ids_and_keyed_path_fingerprints_only_no_raw_paths_or_values",
        "expected_vault_domains": expected_domains,
        "observed_vault_domains": sorted(observed_domains),
        "missing_vault_domains": missing_domains,
        "unexpected_vault_domains": unexpected_domains,
        "expected_external_classes": expected_external_classes,
        "observed_external_classes": sorted(observed_external_classes),
        "missing_external_classes": missing_external_classes,
        "unexpected_external_classes": unexpected_external_classes,
        "required_surfaces": required_surfaces,
        "included_surfaces": sorted(fragment_digests),
        "missing_surfaces": missing,
        "fragment_sha256": dict(sorted(fragment_digests.items())),
        "event_count": len(events),
        "scenario_completed": all_complete,
        "dropped_event_count": dropped,
        "complete": all_complete and dropped == 0,
        "destination_counts": dict(sorted(destination_counts.items())),
        "unsafe_write_count": unsafe,
        "release_gate_passed": (
            all_complete
            and not missing
            and not missing_domains
            and not unexpected_domains
            and not missing_external_classes
            and not unexpected_external_classes
            and len(events) > 0
            and dropped == 0
            and unsafe == 0
        ),
        "grouped_source_operations": [
            {
                "operation": key[0],
                "destination_class": key[1],
                "source_path": key[2],
                "line": key[3],
                "surface": key[4],
                "count": count,
            }
            for key, count in sorted(grouped.items())
        ],
        "events": events,
    }
    target = trace_root / f"{session_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
