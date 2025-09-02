# glyphnet_transport.py

import logging
import threading
import queue
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class GlyphNetTransport:
    """
    Default transport layer for GlyphNetTransceiver.
    Supports simple in-memory queueing. Can be extended to WebSocket, ZeroMQ, etc.
    """

    def __init__(self):
        self.outbox = queue.Queue()
        self.inbox = queue.Queue()
        self.on_receive: Optional[Callable[[bytes], None]] = None
        self.running = False

    def start(self):
        """
        Start background listener thread (if inbox is used).
        """
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._process_inbox_loop, daemon=True).start()
        logger.info("[GlyphNetTransport] 🚀 Transport started.")

    def stop(self):
        self.running = False
        logger.info("[GlyphNetTransport] 🛑 Transport stopped.")

    def send(self, data: bytes):
        """
        Send data to outbox (could be wired to network, WS, etc).
        """
        self.outbox.put(data)
        logger.debug("[GlyphNetTransport] 📤 Data sent to outbox.")

    def receive(self, data: bytes):
        """
        External input into inbox queue.
        """
        self.inbox.put(data)
        logger.debug("[GlyphNetTransport] 📥 Data received into inbox.")

    def set_on_receive(self, callback: Callable[[bytes], None]):
        """
        Set callback to handle incoming data (simulates async receive).
        """
        self.on_receive = callback

    def _process_inbox_loop(self):
        while self.running:
            try:
                data = self.inbox.get(timeout=1.0)
                if self.on_receive:
                    self.on_receive(data)
            except queue.Empty:
                continue