import pytest
from backend.modules.holograms.ghx_sync_layer import GHXSyncLayer

@pytest.mark.asyncio
async def test_ghx_pmg_binder_temporal_linkage():
    sync = GHXSyncLayer()

    # First bundle (no prev_hash)
    b1 = await sync.assemble_bundle_with_pmg_binder()
    assert "pmg_binder" in b1
    assert b1["pmg_binder"]["curr_hash"]
    assert b1["pmg_binder"]["prev_hash"] is None
    assert b1["pmg_binder"]["linked"] is False

    # Capture checksum of the first saved bundle *before it's replaced*
    first_checksum = sync.vault._last_saved_bundle["checksum"]

    # Second bundle (should link to first via prev_hash = first_checksum)
    b2 = await sync.assemble_bundle_with_pmg_binder()
    assert "pmg_binder" in b2
    assert b2["pmg_binder"]["curr_hash"]
    assert b2["pmg_binder"]["prev_hash"] == first_checksum
    assert b2["pmg_binder"]["linked"] is True

    # Basic integrity presence
    assert "integrity" in b1 and "integrity" in b2
    assert b1["integrity"]["hash"] != b2["integrity"]["hash"]