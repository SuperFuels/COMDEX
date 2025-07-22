# File: backend/modules/glyphnet/glyphnet_node_sim.py

import asyncio
import json
from typing import Dict, List
from ..gip.gip_executor import execute_gip_packet

class GlyphNetNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.connected_nodes: List[GlyphNetNode] = []
        self.packet_log: List[Dict] = []

    def connect(self, other_node: 'GlyphNetNode'):
        if other_node not in self.connected_nodes:
            self.connected_nodes.append(other_node)
            other_node.connected_nodes.append(self)

    async def receive_packet(self, packet: Dict):
        self.packet_log.append(packet)
        print(f"[GlyphNet:{self.node_id}] Received packet: {packet.get('id') or packet.get('glyph')}")
        await execute_gip_packet(packet)  # Trigger symbolic action

    async def broadcast_packet(self, packet: Dict):
        self.packet_log.append(packet)
        print(f"[GlyphNet:{self.node_id}] Broadcasting packet to {len(self.connected_nodes)} nodes...")
        for node in self.connected_nodes:
            await node.receive_packet(packet)

# Simple in-memory simulation controller
class GlyphNetSimulator:
    def __init__(self):
        self.nodes: Dict[str, GlyphNetNode] = {}

    def create_node(self, node_id: str) -> GlyphNetNode:
        node = GlyphNetNode(node_id)
        self.nodes[node_id] = node
        return node

    def link_nodes(self, node_a: str, node_b: str):
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].connect(self.nodes[node_b])

    async def send(self, sender_id: str, packet: Dict):
        node = self.nodes.get(sender_id)
        if node:
            await node.broadcast_packet(packet)

glyphnet_sim = GlyphNetSimulator()