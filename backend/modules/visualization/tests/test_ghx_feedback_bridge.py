import pytest, asyncio
from backend.modules.visualization.ghx_feedback_bridge import GHXFeedbackBridge

@pytest.mark.asyncio
async def test_emit_packet_roundtrip():
    packets = []
    def capture(p): packets.append(p)

    bridge = GHXFeedbackBridge(send_callback=capture)
    await bridge.emit({"symbolic_temperature":0.5}, {"scheduler":{}, "carrier":{}})
    assert packets and "feedback" in packets[0]