from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update

def stream_qfc_from_entangled_wave(container_id: str, entangled_wave) -> None:
    """
    Converts entangled wave to QFC payload and sends via WebSocket.
    """
    try:
        payload = entangled_wave.to_qfc_payload()
        send_qfc_update({
            "source": f"wave_state::{container_id}",
            "payload": payload
        })
        print(f"📡 Streamed QFC update for {container_id} with {len(payload['nodes'])} nodes.")
    except Exception as e:
        print(f"❌ Failed to stream QFC from wave: {e}")