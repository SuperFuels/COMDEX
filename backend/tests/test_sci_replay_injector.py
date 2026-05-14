import pytest
import asyncio
from backend.modules.sci.sci_replay_injector import SCIReplayInjector

@pytest.mark.asyncio
async def test_sci_replay_integration():
    injector = SCIReplayInjector()
    snapshots = await injector.fetch_snapshots(limit=1)
    assert isinstance(snapshots, list)
    frames = await injector.replay_photon_timeline(limit=1, reinjection=True)
    assert isinstance(frames, list)
    await injector.close()