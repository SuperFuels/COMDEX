from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.modules.aion_inference.local_model_package import LocalModelPackage, LocalModelReleaseCatalogue
from backend.modules.aion_inference.local_model_vault import LocalModelVault


def package(path: Path, warehouse_sha256: str, source_sha256: str = "a" * 64) -> Path:
    card = path / "AION-Models" / "gpt-oss" / "model-package.v1.json"
    card.parent.mkdir(parents=True)
    card.write_text(json.dumps({
        "schema_version": "aion.local-model-package.v1", "model_id": "gpt-oss", "version": "1", "display_name": "GPT-OSS",
        "storage": {"warehouse_manifest_relative_path": "AION-Warehouse/manifest.v1.json", "warehouse_manifest_sha256": warehouse_sha256,
                    "source_shards": [{"name": "source.gguf", "bytes": 3, "sha256": source_sha256}]},
        "runtime_profile": {"mode": "full_exact", "minimum_internal_free_bytes": 100},
        "compatibility": {"architectures": ["arm64"], "minimum_memory_bytes": 18},
        "speed_claim": {"status": "not_publicly_approved"},
    }), encoding="utf-8")
    return card


def test_discovers_and_selects_only_a_complete_verified_matching_warehouse(tmp_path: Path):
    warehouse = tmp_path / "AION-Warehouse" / "manifest.v1.json"
    warehouse.parent.mkdir()
    (warehouse.parent / "source.gguf").write_bytes(b"ggf")
    warehouse.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1", "status": "COMPLETE_VERIFIED", "verified_sources": [{"name": "source.gguf", "path": "source.gguf", "bytes": 3, "sha256": "a" * 64}]}), encoding="utf-8")
    card = package(tmp_path, hashlib.sha256(warehouse.read_bytes()).hexdigest())
    discovered = LocalModelPackage.discover([tmp_path])
    assert [item.package_path for item in discovered] == [card.resolve()]
    result = discovered[0].preflight(tmp_path, internal_free_bytes=100, memory_bytes=18)
    assert result["selectable"] is True
    assert result["runtime_profile"]["mode"] == "full_exact"
    assert result["model_path"] == str((warehouse.parent / "source.gguf").resolve())


def test_refuses_modified_or_incomplete_warehouse(tmp_path: Path):
    warehouse = tmp_path / "AION-Warehouse" / "manifest.v1.json"
    warehouse.parent.mkdir()
    warehouse.write_text(json.dumps({"schema": "aion.expert-frame-warehouse.v1", "status": "COMPLETE_VERIFIED", "verified_sources": []}), encoding="utf-8")
    card = package(tmp_path, "b" * 64)
    result = LocalModelPackage(card).preflight(tmp_path, internal_free_bytes=100, memory_bytes=18)
    assert result["selectable"] is False
    assert result["failures"] == ["warehouse_manifest_hash_mismatch"]


def test_real_gpt_oss_package_has_no_placeholder_identity():
    card = Path(__file__).parents[1] / "model_packages" / "gpt-oss-120b-q4km-sd-v1.json"
    package_data = json.loads(card.read_text(encoding="utf-8"))
    storage = package_data["storage"]
    assert len(storage["warehouse_manifest_sha256"]) == 64
    assert all(len(item["sha256"]) == 64 for item in storage["source_shards"])


def test_release_catalogue_exposes_only_the_owner_approved_bounded_qwen_package():
    catalogue_path = Path(__file__).parents[1] / "model_packages" / "catalogue.v1.json"
    catalogue = LocalModelReleaseCatalogue(catalogue_path)
    entries = catalogue.entries()
    assert {
        "openai-gpt-oss-120b-q4-k-m-aion-sd",
        "ibm-granite-3.1-3b-a800m-aion-sd",
        "qwen3-30b-a3b-aion-resident-q2",
    }.issubset({entry["model_id"] for entry in entries})
    selectable = [entry for entry in entries if entry["selection_status"] == "selectable"]
    assert [entry["model_id"] for entry in selectable] == ["qwen3-8b-fast-local-q4"]
    assert selectable[0]["release_status"] == "owner_approved_bounded"
    assert all(
        entry["selection_status"] == "visible_not_selectable"
        for entry in entries if entry["model_id"] != "qwen3-8b-fast-local-q4"
    )
    assert catalogue.package_for("qwen3-8b-fast-local-q4").name == "qwen3-8b-fast-local-q4-v1.json"
    assert catalogue.package_for("openai-gpt-oss-120b-q4-k-m-aion-sd") is None


def test_legacy_granite_card_is_found_but_not_made_selectable(tmp_path: Path, monkeypatch):
    model = tmp_path / "AION-Inference" / "hf-models" / "granite-3.1-3b-a800m-instruct"
    model.mkdir(parents=True)
    for name in ("config.json", "tokenizer.json", "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"):
        (model / name).write_text("x", encoding="utf-8")
    monkeypatch.setattr("backend.modules.aion_inference.local_model_vault._scan_roots", lambda: [tmp_path])
    granite = next(item for item in LocalModelVault().snapshot()["models"] if item["model_id"].startswith("ibm-granite"))
    assert granite["release_status"] == "package_validation_pending"
    assert granite["installations"][0]["selectable"] is False
