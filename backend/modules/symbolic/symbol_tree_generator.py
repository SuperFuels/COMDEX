# File: backend/modules/symbolic/symbol_tree_generator.py

from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from backend.modules.knowledge_graph.knowledge_graph_writer import get_glyph_trace_for_container
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.aion.dream_core import DreamCore
# TODO: Restore after GWave system is built
# from backend.modules.gwave.gwave_transmitter import GWaveTransmitter

class GWaveTransmitter:
    @staticmethod
    def emit_symbol_quality_index(trace_id: str, score: float):
        print(f"[Stub:GWave] SQI emitted for {trace_id} → {score}")

import uuid
import logging

logger = logging.getLogger(__name__)

@dataclass
class SymbolicTreeNode:
    glyph: LogicGlyph
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    children: List['SymbolicTreeNode'] = field(default_factory=list)
    parent: Optional['SymbolicTreeNode'] = None
    entangled_ids: List[str] = field(default_factory=list)
    replayed_from: Optional[str] = None
    mutation_source: Optional[str] = None
    goal_score: Optional[float] = None
    sqi_score: Optional[float] = None

    def to_dict(self):
        return {
            "id": self.id,
            "glyph": self.glyph.to_dict(),
            "children": [child.to_dict() for child in self.children],
            "entangled_ids": self.entangled_ids,
            "replayed_from": self.replayed_from,
            "mutation_source": self.mutation_source,
            "goal_score": self.goal_score,
            "sqi_score": self.sqi_score,
        }

@dataclass
class SymbolicMeaningTree:
    root: SymbolicTreeNode
    container_id: str
    node_index: Dict[str, SymbolicTreeNode] = field(default_factory=dict)

    def replay_path(self, node_id: str) -> List[LogicGlyph]:
        path = []
        node = self.node_index.get(node_id)
        while node:
            path.append(node.glyph)
            node = node.parent
        return list(reversed(path))

    def mutate_path(self, from_node_id: str, new_glyph: LogicGlyph) -> SymbolicTreeNode:
        parent_node = self.node_index.get(from_node_id)
        new_node = SymbolicTreeNode(glyph=new_glyph, parent=parent_node, mutation_source=from_node_id)
        parent_node.children.append(new_node)
        self.node_index[new_node.id] = new_node
        return new_node

    def to_dict(self):
        return {
            "container_id": self.container_id,
            "root": self.root.to_dict(),
        }

def build_tree_from_container(container_id: str) -> SymbolicMeaningTree:
    trace = get_glyph_trace_for_container(container_id)
    if not trace:
        raise ValueError(f"No glyph trace found for container {container_id}")

    root_glyph = trace[0]
    root_node = SymbolicTreeNode(glyph=root_glyph)
    tree = SymbolicMeaningTree(root=root_node, container_id=container_id)
    tree.node_index[root_node.id] = root_node

    current = root_node
    for glyph in trace[1:]:
        node = SymbolicTreeNode(glyph=glyph, parent=current)
        current.children.append(node)
        tree.node_index[node.id] = node
        current = node

    logger.info(f"Built SymbolicMeaningTree for container {container_id} with {len(tree.node_index)} nodes.")
    return tree

def inject_mutation_path(tree: SymbolicMeaningTree, from_node_id: str, new_glyph: LogicGlyph) -> SymbolicTreeNode:
    node = tree.mutate_path(from_node_id, new_glyph)
    logger.info(f"Injected mutation from {from_node_id} into tree for container {tree.container_id}")
    return node

def score_path_with_SQI(tree: SymbolicMeaningTree):
    engine = SQIReasoningEngine()
    for node in tree.node_index.values():
        score = engine.score_node(node.glyph)
        node.sqi_score = score
        logger.debug(f"SQI score for node {node.id}: {score}")

def visualize_path(tree: SymbolicMeaningTree, mode: str = "GHX"):
    # Placeholder for rendering in GHX or web UI
    logger.info(f"Visualizing symbolic tree for {tree.container_id} in mode {mode}")

def stream_tree_to_gwave(tree: SymbolicMeaningTree):
    GWaveTransmitter().send({
        "type": "symbol_tree",
        "tree": tree.to_dict(),
    })

def attach_tree_to_teleport(packet: TeleportPacket, tree: SymbolicMeaningTree):
    packet.attach_payload("symbol_tree", tree.to_dict())

def inject_tree_to_dreamcore(tree: SymbolicMeaningTree):
    DreamCore().inject_future_tree(tree)

def resolve_goal_from_tree(tree: SymbolicMeaningTree):
    GoalEngine().resolve_from_tree_path(tree)

def export_tree_to_kg(tree: SymbolicMeaningTree):
    from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
    KnowledgeGraphWriter().export_symbol_tree(tree)

# Optional: CLI / API will call these entrypoints
