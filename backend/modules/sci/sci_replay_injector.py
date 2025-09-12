# File: backend/modules/sci/sci_replay_injector.py

from typing import Dict, List, Any, Optional
import time

class SCIReplayInjector:
    """
    D3 Module: SCI Replay Injector
    Injects scroll-based replay logs into the QuantumFieldCanvas in timed sequence.
    """

    def __init__(self, send_fn):
        """
        Args:
            send_fn: A callback to emit replay payloads to QFC (e.g. via WebSocket).
        """
        self.send_fn = send_fn
        self.replay_speed = 1.0  # multiplier (1.0 = real time)
        self.active = False

    def start_replay(self, replay_log: List[Dict[str, Any]], observer_id: Optional[str] = None, speed: float = 1.0):
        """
        Begins replay of a scroll-based QFC session.
        """
        if not replay_log:
            print("⚠️ No replay log provided.")
            return

        self.active = True
        self.replay_speed = speed
        print(f"🔁 Starting SCI replay: {len(replay_log)} frames @ {speed}x speed")

        last_timestamp = None
        for frame in replay_log:
            if not self.active:
                break

            timestamp = frame.get("timestamp")
            payload = frame.get("payload")

            if last_timestamp is not None and timestamp:
                delay = (timestamp - last_timestamp) / self.replay_speed
                time.sleep(max(0, delay))

            last_timestamp = timestamp

            if payload:
                replay_payload = {
                    "type": "qfc.replay_frame",
                    "observer": observer_id,
                    "frame": payload
                }
                self.send_fn(replay_payload)

        print("✅ Replay complete.")
        self.active = False

    def stop_replay(self):
        self.active = False
        print("⏹️ Replay stopped.")


# Optional test
if __name__ == "__main__":
    def mock_send_fn(event):
        print(f"📤 Sent: {event}")

    mock_log = [
        {"timestamp": 0, "payload": {"nodes": ["A"]}},
        {"timestamp": 1, "payload": {"nodes": ["B"]}},
        {"timestamp": 2, "payload": {"nodes": ["C"]}},
    ]

    injector = SCIReplayInjector(send_fn=mock_send_fn)
    injector.start_replay(mock_log, observer_id="kevin", speed=2.0)
