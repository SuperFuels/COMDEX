# backend/replay/replay_engine.py
from backend.replay.photon_journal import load_events

async def replay_into_crdt(ytext):
    for ev in load_events():
        if ev["type"] == "glyph_edit":
            ytext.delete(0, len(ytext.toString()))
            ytext.insert(0, ev["content"])
            await asyncio.sleep(0.002)  # smooth playback