# backend/modules/gip/luxnet_simulator.py

import asyncio
from typing import Dict, List
from .gip_packet import GIPPacket
from .gip_executor import execute_gip_packet

# Simulated LuxNet network of symbolic nodes
class SymbolicNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.inbox: List[GIPPacket] = []

    async def receive_packet(self, packet: GIPPacket) -> Dict:
        self.inbox.append(packet)
        result = await execute_gip_packet(packet)
        return {"node": self.node_id, "result": result}


class LuxNetSimulator:
    def __init__(self):
        self.nodes: Dict[str, SymbolicNode] = {}

    def register_node(self, node_id: str):
        if node_id not in self.nodes:
            self.nodes[node_id] = SymbolicNode(node_id)

    async def broadcast(self, packet: GIPPacket) -> Dict[str, Dict]:
        results = {}
        for node_id, node in self.nodes.items():
            result = await node.receive_packet(packet)
            results[node_id] = result
        return results

    async def send_to_node(self, node_id: str, packet: GIPPacket) -> Dict:
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        return await self.nodes[node_id].receive_packet(packet)


# Singleton simulator instance
luxnet = LuxNetSimulator()

# Register default symbolic nodes
for i in range(3):
    luxnet.register_node(f"symbolic-node-{i+1}")