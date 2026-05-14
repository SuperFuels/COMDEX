from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema
except Exception as e:  # pragma: no cover
    jsonschema = None
    _jsonschema_err = e


ROOT = Path("/workspaces/COMDEX")
ART = ROOT / "docs" / "Artifacts" / "v0.4" / "P21_GX1"
SCHEMAS = ROOT / "schemas"

SCHEMA_FILES = {
    "CONFIG.json": SCHEMAS / "gx1_genome_benchmark_config.schema.json",
    "METRICS.json": SCHEMAS / "gx1_genome_benchmark_metrics.schema.json",
    "REPLAY_BUNDLE.json": SCHEMAS / "gx1_replay_bundle.schema.json",
}

EXPECTED_SCHEMA_VERSIONS = {
    "CONFIG.json": "GX1_CONFIG_V0",
    "METRICS.json": "GX1_METRICS_V0",
    "REPLAY_BUNDLE.json": "GX1_REPLAY_BUNDLE_V0",
}


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _latest_run_id() -> str:
    rid = (ART / "runs" / "LATEST_RUN_ID.txt").read_text(encoding="utf-8").strip()
    assert rid, "LATEST_RUN_ID.txt is empty"
    return rid


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_gx1_latest_run_schema_validates() -> None:
    run_id = _latest_run_id()
    run_dir = ART / "runs" / run_id

    # Load schemas
    schemas = {k: _load_json(v) for k, v in SCHEMA_FILES.items()}

    # Validate each core artifact
    for fn, schema in schemas.items():
        fp = run_dir / fn
        assert fp.exists(), f"missing artifact: {fp}"
        doc = _load_json(fp)

        # explicit tag check (helps debugging before jsonschema error walls)
        assert doc.get("schemaVersion") == EXPECTED_SCHEMA_VERSIONS[fn], (
            f"{fn}: schemaVersion mismatch: got={doc.get('schemaVersion')} "
            f"expected={EXPECTED_SCHEMA_VERSIONS[fn]}"
        )

        # Draft 2020-12 validator
        jsonschema.Draft202012Validator(schema).validate(doc)


def test_gx1_schema_files_exist_and_parse() -> None:
    # This runs even if jsonschema isn't installed (basic sanity)
    for fn, sp in SCHEMA_FILES.items():
        assert sp.exists(), f"missing schema file: {sp}"
        _ = _load_json(sp)
