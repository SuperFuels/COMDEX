# backend/modules/glyphnet/broadcast_throttle.py
import os, time, threading, queue

SOUL_LAW_BROADCAST = os.getenv("SOUL_LAW_BROADCAST", "on").lower()  # on|off
MAX_RATE = float(os.getenv("SOUL_LAW_BROADCAST_RPS", "25"))  # events/sec budget
FLUSH_INTERVAL = float(os.getenv("SOUL_LAW_BROADCAST_FLUSH", "0.1"))  # seconds

class BroadcastThrottle:
    def __init__(self, send_func):
        self.send = send_func
        self.q = queue.Queue()
        self.running = True
        self.last_sent = 0.0
        self.min_interval = 1.0 / MAX_RATE if MAX_RATE > 0 else 0.0
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        if SOUL_LAW_BROADCAST == "off":
            # drain quietly
            while self.running:
                try:
                    self.q.get(timeout=0.5)
                    self.q.task_done()
                except queue.Empty:
                    pass
            return

        batch = []
        while self.running:
            try:
                item = self.q.get(timeout=FLUSH_INTERVAL)
                batch.append(item)
                # collect a small batch
                while True:
                    try:
                        batch.append(self.q.get_nowait())
                        self.q.task_done()
                    except queue.Empty:
                        break
                # rate control
                now = time.time()
                sleep_for = max(0.0, self.min_interval - (now - self.last_sent))
                if sleep_for > 0:
                    time.sleep(sleep_for)
                # ship batch
                for etype, payload in batch:
                    try:
                        self.send(etype, payload)
                    except Exception:
                        pass
                self.last_sent = time.time()
                batch.clear()
                self.q.task_done()
            except queue.Empty:
                # idle → nothing to do
                pass

    def submit(self, event_type, payload):
        try:
            self.q.put_nowait((event_type, payload))
        except Exception:
            pass

_throttle = None

def install(send_func):
    global _throttle
    if _throttle is None:
        _throttle = BroadcastThrottle(send_func)

def throttled_broadcast(event_type: str, payload: dict):
    if _throttle is None:
        # fallback direct
        return
    _throttle.submit(event_type, payload)