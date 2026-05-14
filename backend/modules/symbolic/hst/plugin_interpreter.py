import logging
from typing import Dict, List, Callable, Optional

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

logger = logging.getLogger(__name__)

# Plugin type signature
PluginFunc = Callable[[SymbolicTreeNode], Optional[Dict]]


class PluginAwareInterpreter:
    def __init__(self):
        self.plugins: Dict[str, PluginFunc] = {}
        self.kg_writer = KnowledgeGraphWriter()

    def register_plugin(self, name: str, plugin_func: PluginFunc):
        """
        Register a plugin with a name and callable that takes a SymbolicTreeNode and returns metadata.
        """
        self.plugins[name] = plugin_func
        logger.info(f"[🧩] Registered plugin: {name}")

    def interpret_tree(self, tree: SymbolicMeaningTree):
        """
        Apply all registered plugins to the symbolic tree nodes.
        """
        for node_id, node in tree.node_index.items():
            for name, plugin in self.plugins.items():
                try:
                    result = plugin(node)
                    if result:
                        node.metadata.setdefault("plugins", {})[name] = result
                        logger.info(f"[🧩] Plugin '{name}' enriched node {node_id}")
                        self.kg_writer.write_symbol_node(node)
                except Exception as e:
                    logger.warning(f"[⚠️] Plugin '{name}' failed on node {node_id}: {e}")