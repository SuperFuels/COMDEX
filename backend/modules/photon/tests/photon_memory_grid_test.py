import asyncio
import pytest
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid

@pytest.mark.asyncio
async def test_photon_memory_grid_store_and_recall():
    grid = PhotonMemoryGrid()
    state = {"final_wave": [0.1, 0.2, 0.3], "timestamp": 12345}
    await grid.store_capsule_state("test_capsule", state)
    recalled = grid.recall_state("test_capsule")
    assert recalled is not None
    assert "checksum" in recalled
    assert grid.integrity_check("test_capsule")