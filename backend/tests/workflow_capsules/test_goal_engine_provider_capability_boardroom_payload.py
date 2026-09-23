from backend.modules.aion_business.runtime.business_container_service import BusinessContainerService


def test_boardroom_payload_includes_provider_capability_manifest():
    service = BusinessContainerService()
    payload = service.get_boardroom_payload("costa-conexion")

    assert "provider_capability_manifest" in payload
    manifest = payload["provider_capability_manifest"]

    assert manifest["schema_version"] == "aion.business.provider_capability_manifest.v1"
    assert manifest["trace_type"] == "provider_capability_manifest"
    assert manifest["safe_defaults"]["external_writes_require_approval"] is True
    assert manifest["safe_defaults"]["business_state_mutations_require_human_review"] is True
    assert "local" in manifest["providers"]
    assert "openai" in manifest["providers"]
    assert "anthropic" in manifest["providers"]


def test_business_container_service_uses_provider_router_manifest_source():
    text = open("backend/modules/aion_business/runtime/business_container_service.py").read()

    assert "ProviderRouter" in text
    assert "self.provider_router.capability_manifest()" in text
    assert 'payload["provider_capability_manifest"]' in text
