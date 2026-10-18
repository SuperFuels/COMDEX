import hashlib
import json
import struct

from backend.modules.aion_inference.gptoss_mixed_q3_sidecar import GptOssMixedQ3Sidecar


def canonical(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def build_fixture(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("source\n")
    components = [bytes([index]) * (index + 1) for index in range(6)]
    payload = struct.pack("<8s6Q", b"AIONQ3S1", *map(len, components)) + b"".join(components)
    frame = tmp_path / "layer-12-expert-003.aionq3"
    frame.write_bytes(payload)
    manifest = {
        "schema": "aion.gptoss-mixed-q3-sidecar.v1", "status": "COMPLETE_VERIFIED",
        "source_manifest_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "entries": [{
            "layer": 12, "expert": 3, "relative_path": frame.name,
            "file_sha256": hashlib.sha256(payload).hexdigest(),
            "component_sha256": [hashlib.sha256(value).hexdigest() for value in components],
        }],
    }
    manifest["canonical_sha256"] = canonical(manifest)
    path = tmp_path / "manifest.v1.json"
    path.write_text(json.dumps(manifest))
    return source, path, components, frame


def test_reads_verified_components_without_retaining_payload(tmp_path):
    source, manifest, components, _ = build_fixture(tmp_path)
    sidecar = GptOssMixedQ3Sidecar(manifest, source)
    value = sidecar.get(12, 3)
    assert value is not None
    assert [value[p][k] for p in ("gate", "up", "down")
            for k in ("weight", "bias")] == components
    assert sidecar.metrics()["hits"] == 1


def test_integrity_failure_returns_exact_fallback_signal(tmp_path):
    source, manifest, _, frame = build_fixture(tmp_path)
    sidecar = GptOssMixedQ3Sidecar(manifest, source)
    frame.write_bytes(frame.read_bytes()[:-1] + b"x")
    assert sidecar.get(12, 3) is None
    assert sidecar.metrics()["integrity_failures"] == 1
