# backend/modules/holograms/tests/test_ghx_sync_layer.py
import pytest
from backend.modules.holograms.ghx_sync_layer import GHXSyncLayer

@pytest.mark.asyncio
async def test_ghx_sync_layer_bundle_creation():
    sync = GHXSyncLayer()
    bundle = await sync.assemble_bundle()

    assert "ghx_id" in bundle
    assert "integrity" in bundle
    assert bundle["integrity"]["verified"] is True
    assert isinstance(bundle["resonance_ledger"], dict)
    assert isinstance(bundle["pmg_snapshot"], dict)
    assert isinstance(bundle["usr_telemetry"], dict)

    print(f"\n✅ GHX Sync Layer created bundle {bundle['ghx_id']} successfully.")