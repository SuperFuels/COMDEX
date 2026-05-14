# File: backend/modules/glyphnet/glyphnet_transport.py

import logging
import threading
import queue
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class GlyphNetTransport:
    """
    Default transport layer for GlyphNetTransceiver.
    Provides simple in-memory queueing for send/receive simulation.
    Can be extended to WebSocket, ZeroMQ, RF drivers, etc.
    """

    def __init__(self):
        self.outbox: "queue.Queue[bytes]" = queue.Queue()
        self.inbox: "queue.Queue[bytes]" = queue.Queue()
        self.on_receive: Optional[Callable[[bytes], None]] = None

        self._thread: Optional[threading.Thread] = None
        self.running: bool = False

        # Stats
        self.sent_count: int = 0
        self.recv_count: int = 0

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────
    def start(self) -> None:
        """
        Start background listener thread for processing inbox.
        """
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._process_inbox_loop, daemon=True
        )
        self._thread.start()
        logger.info("[GlyphNetTransport] 🚀 Transport started.")

    def stop(self) -> None:
        """
        Stop background listener thread gracefully.
        """
        if not self.running:
            return
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("[GlyphNetTransport] 🛑 Transport stopped.")

    # ──────────────────────────────────────────────
    # Send / Receive
    # ──────────────────────────────────────────────
    def send(self, data: bytes) -> None:
        """
        Send data to outbox (can be wired to network/WS/etc).
        """
        self.outbox.put(data)
        self.sent_count += 1
        logger.debug("[GlyphNetTransport:TX] 📤 Data sent to outbox.")

    def receive(self, data: bytes) -> None:
        """
        External input into inbox queue (simulates incoming data).
        """
        self.inbox.put(data)
        logger.debug("[GlyphNetTransport:RX] 📥 Data injected into inbox.")

    def set_on_receive(self, callback: Callable[[bytes], None]) -> None:
        """
        Set callback to handle incoming data (executed in background thread).
        """
        self.on_receive = callback

    # ──────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────
    def _process_inbox_loop(self) -> None:
        """
        Worker loop to process inbox messages and dispatch to callback.
        """
        while self.running:
            try:
                data = self.inbox.get(timeout=1.0)
            except queue.Empty:
                continue

            self.recv_count += 1
            if self.on_receive:
                try:
                    self.on_receive(data)
                except Exception as cb_err:
                    logger.warning(
                        f"[GlyphNetTransport:RX] ⚠️ Callback error: {cb_err}"
                    )

    # ──────────────────────────────────────────────
    # Debug / Utilities
    # ──────────────────────────────────────────────
    def peek_outbox(self) -> Optional[bytes]:
        """
        Peek at next item in outbox without removing.
        """
        try:
            return self.outbox.queue[0]
        except IndexError:
            return None

    def drain_outbox(self) -> list[bytes]:
        """
        Drain and return all items currently in outbox.
        """
        drained: list[bytes] = []
        while not self.outbox.empty():
            drained.append(self.outbox.get_nowait())
        return drained

    def stats(self) -> dict:
        """
        Return transport statistics.
        """
        return {
            "sent_count": self.sent_count,
            "recv_count": self.recv_count,
            "outbox_size": self.outbox.qsize(),
            "inbox_size": self.inbox.qsize(),
            "running": self.running,
        }