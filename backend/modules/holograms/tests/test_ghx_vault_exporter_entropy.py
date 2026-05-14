import pytest, asyncio
from backend.modules.holograms.ghx_vault_exporter import inject_entropy_signature

@pytest.mark.asyncio
async def test_entropy_injection():
    sample = {"chain": [{"a": 1}, {"b": 2}]}
    enriched = inject_entropy_signature(sample.copy())
    assert "entropy_signature" in enriched
    assert "ghx_meta" in enriched
    assert enriched["ghx_meta"]["validated"] is True