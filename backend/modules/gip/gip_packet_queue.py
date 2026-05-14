# File: backend/modules/gip/gip_packet_queue.py

import asyncio
from collections import deque
from typing import Dict, Deque, Optional
from .gip_executor import execute_gip_packet

class GIPPacketQueue:
    def __init__(self):
        self.queue: Deque[Dict] = deque()
        self.processing = False

    def enqueue(self, packet: Dict):
        self.queue.append(packet)

    async def process(self):
        if self.processing:
            return
        self.processing = True
        try:
            while self.queue:
                packet = self.queue.popleft()
                await execute_gip_packet(packet)
        finally:
            self.processing = False

# Singleton instance
gip_queue = GIPPacketQueue()

# Async utility for external use
async def enqueue_and_process(packet: Dict):
    gip_queue.enqueue(packet)
    await gip_queue.process()