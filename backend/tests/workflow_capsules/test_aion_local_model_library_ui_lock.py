import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_local_library_catalogue_has_roles_and_harnesses_for_all_planned_models():
    catalogue = json.loads((ROOT / "backend/modules/aion_inference/model_packages/catalogue.v1.json").read_text())
    models = {item["model_id"]: item for item in catalogue["models"]}
    required = {
        "google-gemma-fast-local-8gb",
        "tessaris-fast-local-entry-3b",
        "mistral-ministral-3-8b-local",
        "qwen3-30b-a3b-aion-resident-q2",
        "openai-gpt-oss-20b-private-reasoning",
        "deepseek-r1-distill-qwen-14b-private-reasoning",
        "meta-muse-glimmer-agent-coding",
    }
    assert required <= models.keys()
    for item in models.values():
        assert item["category"].startswith("Local") or item["category"].startswith("Specialist")
        assert item["role"]
        assert item["harness"]["status"]


def test_vault_shows_gemma_as_a_local_library_model_not_an_api_key_provider():
    app = (ROOT / "desktop/mac/src/app.js").read_text()
    assert 'safeArray(status.providers).filter((provider) => provider?.id !== "gemma")' in app
    assert 'Local models, including Gemma, are installed and checked in SD card and Mac storage below.' in app
    assert '<strong>Harness:</strong>' in app
