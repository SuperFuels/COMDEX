# File: backend/modules/glyphnet/glyphnet_node_sim.py

import asyncio
import logging
from typing import Dict, List, Optional, Any

from backend.modules.gip.gip_executor import execute_gip_packet

logger = logging.getLogger(__name__)


class GlyphNetNode:
    """
    A lightweight in-memory simulation of a GlyphNet node.
    Can connect to peers, broadcast, and execute .gip packets.
    """

    def __init__(self, node_id: str):
        self.node_id: str = node_id
        self.connected_nodes: List["GlyphNetNode"] = []
        self.packet_log: List[Dict[str, Any]] = []

    def connect(self, other_node: "GlyphNetNode") -> None:
        """Bidirectionally link two nodes."""
        if other_node not in self.connected_nodes:
            self.connected_nodes.append(other_node)
            other_node.connected_nodes.append(self)
            logger.info(f"[GlyphNetSim] Linked {self.node_id} ↔ {other_node.node_id}")

    async def receive_packet(self, packet: Dict[str, Any]) -> None:
        """
        Receive and process a packet sent from another node.
        Appends to log and executes via gip_executor.
        """
        self.packet_log.append(packet)
        glyph_id = packet.get("id") or packet.get("glyph") or "?"
        logger.info(f"[GlyphNet:{self.node_id}] Received packet: {glyph_id}")
        try:
            await execute_gip_packet(packet)  # symbolic execution
        except Exception as e:
            logger.error(f"[GlyphNet:{self.node_id}] Packet execution failed: {e}")

    async def broadcast_packet(self, packet: Dict[str, Any]) -> None:
        """
        Broadcast a packet to all connected peers (including self-log).
        """
        self.packet_log.append(packet)
        logger.info(f"[GlyphNet:{self.node_id}] Broadcasting packet to {len(self.connected_nodes)} peers…")

        tasks = [node.receive_packet(packet) for node in self.connected_nodes]
        if tasks:
            await asyncio.gather(*tasks)

    def get_log_summary(self, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        """
        Return the most recent N packets for inspection/debugging.
        """
        return self.packet_log[-limit:]

    async def replay_packets(self, delay: float = 0.5, limit: Optional[int] = None) -> None:
        """
        Step-through replay of this node’s packet log.
        Replays packets in order with optional delay (seconds) between them.
        """
        packets = self.packet_log if limit is None else self.packet_log[:limit]
        logger.info(f"[GlyphNet:{self.node_id}] Replaying {len(packets)} packets with delay={delay}s")
        for idx, packet in enumerate(packets, 1):
            glyph_id = packet.get("id") or packet.get("glyph") or "?"
            logger.debug(f"[GlyphNet:{self.node_id}] Replay {idx}/{len(packets)} → {glyph_id}")
            try:
                await execute_gip_packet(packet)
            except Exception as e:
                logger.error(f"[GlyphNet:{self.node_id}] Replay failed on packet {glyph_id}: {e}")
            await asyncio.sleep(delay)


class GlyphNetSimulator:
    """
    A simple in-memory GlyphNet network simulator.
    Allows you to spawn nodes, connect them, send packets, and replay history.
    """

    def __init__(self):
        self.nodes: Dict[str, GlyphNetNode] = {}

    def create_node(self, node_id: str) -> GlyphNetNode:
        """Create and register a new simulated node."""
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already exists in simulation")
        node = GlyphNetNode(node_id)
        self.nodes[node_id] = node
        logger.info(f"[GlyphNetSim] Created node: {node_id}")
        return node

    def link_nodes(self, node_a: str, node_b: str) -> None:
        """Connect two nodes by ID (bidirectional)."""
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].connect(self.nodes[node_b])
        else:
            raise ValueError(f"Cannot link: missing nodes {node_a}, {node_b}")

    async def send(self, sender_id: str, packet: Dict[str, Any]) -> None:
        """Send a packet from a specific node into the network."""
        node = self.nodes.get(sender_id)
        if not node:
            raise ValueError(f"Sender node '{sender_id}' not found in simulation")
        await node.broadcast_packet(packet)

    def get_network_topology(self) -> Dict[str, List[str]]:
        """Return a dict view of current simulation topology."""
        return {
            node_id: [n.node_id for n in node.connected_nodes]
            for node_id, node in self.nodes.items()
        }

    def get_node_log(self, node_id: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        """Inspect recent packets for a node by ID."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found in simulation")
        return node.get_log_summary(limit=limit)

    async def replay_network(self, delay: float = 0.5, limit: Optional[int] = None) -> None:
        """
        Step-through replay across all nodes in the network.
        Replays in insertion order, node by node.
        """
        for node_id, node in self.nodes.items():
            logger.info(f"[GlyphNetSim] Replaying node {node_id}")
            await node.replay_packets(delay=delay, limit=limit)


# Singleton simulator instance
glyphnet_sim = GlyphNetSimulator()