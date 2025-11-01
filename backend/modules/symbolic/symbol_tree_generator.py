# 📁 backend/modules/sqi/symbol_tree_generator.py

from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field
import uuid
import logging
import json
import sys
import os
import warnings

logger = logging.getLogger(__name__)

from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph, LogicGlyph
from backend.modules.symbolic.symbolic_meaning_tree import SymbolicMeaningTree
from backend.modules.symbolic.symbolic_tree_node import SymbolicTreeNode
from backend.modules.symbolnet.symbolnet_vector_utils import get_semantic_vector
from backend.modules.glyphwave.emitters.wave_injector import WaveInjector
from backend.modules.glyphwave.core.carrier_memory import CarrierMemory

def safe_load_container_by_id(container_id_or_path: str) -> Any:
    """
    Safe container loader using UCSRuntime (preferred), with fallback warning.
    Works for both file paths (ending in .dc.json) and registered container IDs.
    """
    def normalize_path(path: str) -> str:
        name = os.path.basename(path).replace(".dc.json", "")
        return os.path.join("containers", f"{name}.dc.json")

    def extract_container_id(path: str) -> str:
        return os.path.basename(path).replace(".dc.json", "")

    try:
        # ⬇️ ✅ Import inside function to avoid circular dependency
        from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
        ucs_runtime = get_ucs_runtime()

        filepath = normalize_path(container_id_or_path)
        ucs_runtime.load_container(filepath)
        cid = extract_container_id(filepath)
        return ucs_runtime.get_container(cid)

    except Exception as e:
        warnings.warn(
            f"⚠️ UCSRuntime failed to load container '{container_id_or_path}': {e}\n"
            f"Falling back to deprecated legacy loader.",
            DeprecationWarning
        )
        try:
            from backend.modules.dimensions.containers.container_loader import load_container_by_id
            return load_container_by_id(container_id_or_path)
        except Exception as inner_e:
            raise ImportError(
                f"❌ Failed to load container via both UCS and legacy loaders:\n"
                f"  UCS error: {e}\n"
                f"  Legacy error: {inner_e}"
            )

def inject_symbolic_tree(container_id_or_path: str, verbose: bool = True) -> None:
    """
    Inject symbolic meaning tree into the specified container.
    """
    try:
        container = safe_load_container_by_id(container_id_or_path)
        symbolic_tree = build_symbolic_tree_from_container(container)
        container.symbolic_tree = symbolic_tree
        if verbose:
            print(f"✅ Symbolic tree injected successfully.")
    except Exception as e:
        print(f"[❌] Failed: {e}")
        import logging
        logger.error(f"[HST Injection] Failed to inject SymbolicMeaningTree: {e}")

def resolve_replay_chain(tree: SymbolicMeaningTree, node: SymbolicTreeNode):
    """
    Adds replay chain hints based on predictive or mutation links.
    Used for visualizing stepwise reasoning or symbolic progression.
    """
    replay = []

    # 🔍 Link to predictions under this node (forward reasoning)
    for child in node.children:
        if child.glyph.metadata.get("type") == "prediction":
            replay.append({
                "target_id": child.id,
                "reason": "prediction",
                "score": child.glyph.metadata.get("goal_match_score", 0.5)
            })

    # 🔁 Back-link if this node is a prediction (point to parent)
    if node.glyph.metadata.get("type") == "prediction":
        parent_id = node.glyph.metadata.get("parent_electron_id")
        if parent_id and parent_id in tree.node_index:
            replay.append({
                "target_id": parent_id,
                "reason": "reverse_reasoning",
                "score": 0.5
            })

    # 🧬 Add symbolic trail links (e.g., mutation result, derived_from)
    derived_from = node.glyph.metadata.get("derived_from")
    if derived_from and derived_from in tree.node_index:
        replay.append({
            "target_id": derived_from,
            "reason": "mutation_result",
            "score": 0.7
        })

    node.replay_chain = replay

def resolve_semantic_links(tree: SymbolicMeaningTree, node: SymbolicTreeNode):
    """
    Attempts to identify related glyphs in the tree and annotate semantic links.
    Injects links into node.semantic_links and node.semantic_context.
    """
    current_label = node.glyph.label
    current_meta = node.glyph.metadata or {}
    related_links = []

    for other_node in tree.node_index.values():
        if other_node.id == node.id:
            continue

        other_label = other_node.glyph.label
        other_meta = other_node.glyph.metadata or {}

        # 🧠 Match based on partial label similarity or shared tags
        if current_label.lower() in other_label.lower() or other_label.lower() in current_label.lower():
            related_links.append({
                "type": "label_similarity",
                "target_id": other_node.id,
                "score": 0.8
            })

        # 🔁 Match shared metadata tags (e.g. 'domain', 'meaning', 'group')
        shared_keys = set(current_meta.keys()) & set(other_meta.keys())
        for key in shared_keys:
            if current_meta.get(key) == other_meta.get(key):
                related_links.append({
                    "type": "shared_metadata",
                    "key": key,
                    "target_id": other_node.id,
                    "score": 0.6
                })

        # 🌀 If both contain a semantic_context, link them
        if current_meta.get("semantic_context") and current_meta.get("semantic_context") == other_meta.get("semantic_context"):
            related_links.append({
                "type": "semantic_context",
                "target_id": other_node.id,
                "score": 1.0
            })
            node.semantic_context = current_meta.get("semantic_context")

    node.semantic_links.extend(related_links)

from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph, LogicGlyph

def ensure_glyph(glyph_entry: Dict[str, Any]) -> LogicGlyph:
    if isinstance(glyph_entry, LogicGlyph):
        return glyph_entry
    elif isinstance(glyph_entry, dict):
        allowed_keys = {"type", "operator", "operands", "metadata", "value", "label"}
        filtered = {k: v for k, v in glyph_entry.items() if k in allowed_keys}

        if "label" not in filtered:
            filtered["label"] = (
                filtered.get("value")
                or filtered.get("operator")
                or filtered.get("type")
                or "unknown"
            )

        return LogicGlyph.create(
            symbol=filtered.get("label", "∅"),
            operands=filtered.get("operands", []),
            metadata=filtered.get("metadata", {})
        )
    else:
        raise TypeError("Invalid glyph entry format.")

def resolve_electron_links(electron: Dict[str, Any], glyph: SymbolGlyph, node: SymbolicTreeNode):
    """
    Injects container/QFC cross-link metadata into the glyph and morphic overlay.
    """
    link_container_id = electron.get("linkContainerId")
    visualize_flag = electron.get("visualizeInQFC", False)

    if link_container_id:
        glyph.metadata["linkContainerId"] = link_container_id
        glyph.metadata["visualizeInQFC"] = visualize_flag
        node.morphic_overlay["qfc_overlay_target"] = link_container_id

def build_symbolic_tree_from_container(
    container: Union[Dict, Any],
    emit_wave: bool = True,
    inject_trace: bool = False,
    inject_overlay: bool = False
) -> SymbolicMeaningTree:
    # Normalize UCSBaseContainer to dict
    if hasattr(container, "to_dict"):
        container = container.to_dict()

    container_id = container.get("id") or "unknown_container"
    container_name = container.get("name") or container_id

    # ✅ 1. Root node from container
    root_glyph = SymbolGlyph(
        label="container",
        value=container_name,
        metadata={
            "type": "container",
            "id": container_id,
            "created_on": container.get("created_on")
        }
    )
    root_node = SymbolicTreeNode(glyph=root_glyph)
    tree = SymbolicMeaningTree(root=root_node, container_id=container_id)

    # ✅ 2. Add direct glyphs
    glyph_entries = container.get("glyphs", [])
    if not glyph_entries:
        logger.warning(f"[⚠️] No glyphs found in container {container_id}")

    for glyph_entry in glyph_entries:
        try:
            glyph = ensure_glyph(glyph_entry)

            # 🧠 Extract operator/label for display
            label = getattr(glyph, "label", None) or getattr(glyph, "operator", None) or "unknown"

            # 🛑 Skip dummy or malformed glyphs
            if label == "unknown" and not getattr(glyph, "operands", []):
                logger.warning(f"[⏩] Skipping dummy glyph: {glyph_entry}")
                continue

            # 🔍 Extract glyph_id safely
            glyph_id = None
            if isinstance(glyph, dict):
                glyph_id = glyph.get("id") or glyph.get("_id") or glyph.get("value")
            elif hasattr(glyph, "id"):
                glyph_id = glyph.id
            elif hasattr(glyph, "metadata") and isinstance(glyph.metadata, dict):
                glyph_id = glyph.metadata.get("id") or glyph.metadata.get("_id")

            g_node = tree.add_node(
                label="glyph",
                value=label,
                metadata={
                    "id": glyph_id or "unknown",
                    "type": "glyph"
                },
                parent=root_node
            )

            # 🌊 Optional: Emit GWave from glyph
            if emit_wave:
                try:
                    injector = WaveInjector(CarrierMemory())

                    # ✅ Defensive handling of EncodedLogicGlyph vs dict
                    if isinstance(glyph, dict):
                        glyph_id_debug = glyph.get("id", "unknown_dict")
                    elif hasattr(glyph, "metadata") and isinstance(glyph.metadata, dict):
                        glyph_id_debug = glyph.metadata.get("id", "unknown_encoded")
                    else:
                        glyph_id_debug = getattr(glyph, "id", "unknown_object")

                    injector.emit_from_glyph(glyph, source="symbol_tree_builder")

                except Exception as wave_err:
                    logger.warning(f"[⚠️] Failed to emit wave for glyph {glyph_id_debug}: {wave_err}")

            # 🌐 Optional: Link glyph to Knowledge Graph
            if isinstance(glyph, dict):
                glyph_id = glyph.get("id")
                metadata = glyph.get("metadata", {})
            else:
                glyph_id = getattr(glyph, "id", None)
                metadata = getattr(glyph, "metadata", {})

            if isinstance(glyph_id, str):
                if glyph_id.startswith("glyph_"):
                    try:
                        kg_writer = KnowledgeGraphWriter()
                        relation = (
                            metadata.get("kg_origin_path", "supports")
                            if isinstance(metadata, dict)
                            else "supports"
                        )
                        kg_writer.link_source(
                            node_id=glyph_id,
                            source_id=container_id,
                            relation=relation
                        )
                    except Exception as kg_err:
                        logger.warning(f"[KG] Failed to link glyph {glyph_id} to KG: {kg_err}")
                else:
                    logger.warning(f"[KG] Glyph ID does not start with 'glyph_': {glyph_id}")
            else:
                logger.warning(f"[KG] Skipping invalid glyph ID for container {container_id}: {glyph_id}")

        except Exception as e:
            logger.warning(f"[⚠️] Failed to process glyph entry: {glyph_entry}. Error: {e}")

    # ✅ 3. Attach electrons under root (if it's an atom container)
    electrons = container.get("electrons", [])
    for electron in electrons:
        glyph = ensure_glyph(electron.get("glyph", {}))

        e_node = SymbolicTreeNode(glyph=glyph, parent=root_node)
        resolve_electron_links(electron, glyph, e_node)

        link_container_id = electron.get("linkContainerId")
        visualize_flag = electron.get("visualizeInQFC", False)
        glyph.metadata["linkContainerId"] = link_container_id
        glyph.metadata["visualizeInQFC"] = visualize_flag

        if link_container_id:
            e_node.morphic_overlay["qfc_overlay_target"] = link_container_id

        root_node.children.append(e_node)
        tree.node_index[e_node.id] = e_node

        if emit_wave:
            injector = WaveInjector(CarrierMemory())
            injector.emit_from_glyph(glyph, source="symbol_tree_builder")

        preds = electron.get("predictions", [])
        for pred in preds:
            pred_glyph = ensure_glyph(pred)
            pred_glyph.metadata["linked_goal_id"] = electron.get("linked_goal_id")
            pred_glyph.metadata["type"] = "prediction"
            pred_glyph.metadata["parent_electron_id"] = e_node.id
            pred_glyph.metadata["goal_match_score"] = pred.get("goal_match_score", 0.0)
            pred_glyph.metadata["rewrite_success_prob"] = pred.get("rewrite_success_prob", 0.0)

            p_node = SymbolicTreeNode(glyph=pred_glyph, parent=e_node)
            e_node.children.append(p_node)
            tree.node_index[p_node.id] = p_node

            if emit_wave:
                emit_from_glyph(pred_glyph, source="symbol_tree_builder")

    # ✅ 4. Attach nested atoms
    sub_atoms = container.get("atoms", [])
    for atom in sub_atoms:
        atom_name = atom.get("name") or atom.get("id") or "anonymous_atom"
        atom_glyph = SymbolGlyph(
            label="atom",
            value=atom_name,
            metadata={
                "type": "atom",
                "id": atom.get("id")
            }
        )
        atom_node = SymbolicTreeNode(glyph=atom_glyph, parent=root_node)
        root_node.children.append(atom_node)
        tree.node_index[atom_node.id] = atom_node

        if emit_wave:
            emit_from_glyph(atom_glyph, source="symbol_tree_builder")

        atom_glyphs = atom.get("glyphs", [])
        for glyph in atom_glyphs:
            g_node = tree.add_node(
                label="glyph",
                value=glyph.get("label") or glyph.get("name") or glyph.get("id") or "unknown",
                metadata={
                    "id": glyph.get("id"),
                    "type": "glyph",
                    "atom_id": atom.get("id")
                },
                parent=atom_node
            )
            if emit_wave:
                injector = WaveInjector(CarrierMemory())
                injector.emit_from_glyph(glyph, source="symbol_tree_builder")

        sub_electrons = atom.get("electrons", [])
        for electron in sub_electrons:
            e_glyph = ensure_glyph(electron.get("glyph", {}))
            e_node = SymbolicTreeNode(glyph=e_glyph, parent=atom_node)
            atom_node.children.append(e_node)
            tree.node_index[e_node.id] = e_node

            if emit_wave:
                emit_from_glyph(e_glyph, source="symbol_tree_builder")

            for pred in electron.get("predictions", []):
                pred_glyph = ensure_glyph(pred)
                pred_glyph.metadata["type"] = "prediction"
                pred_glyph.metadata["goal_match_score"] = pred.get("goal_match_score", 0.0)
                pred_glyph.metadata["rewrite_success_prob"] = pred.get("rewrite_success_prob", 0.0)
                pred_glyph.metadata["parent_electron_id"] = e_node.id

                p_node = SymbolicTreeNode(glyph=pred_glyph, parent=e_node)
                e_node.children.append(p_node)
                tree.node_index[p_node.id] = p_node

                if emit_wave:
                    emit_from_glyph(pred_glyph, source="symbol_tree_builder")

    # ✅ 5. Enrich all nodes with semantic meaning vectors
    from backend.modules.symbolnet.symbolnet_vector_utils import get_semantic_vector
    for node in tree.node_index.values():
        label = node.glyph.label
        meaning_vec = get_semantic_vector(label)
        if meaning_vec is not None:
            node.meaning_vector = meaning_vec

    # ✅ 6. Add KG origin links and CodexCore metadata
    goal_id = container.get("goal", {}).get("id")
    mutation_id = container.get("mutation", {}).get("id")
    from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

    for node in tree.node_index.values():
        glyph = node.glyph
        if glyph:
            if goal_id:
                glyph.metadata["goal_id"] = goal_id
            if mutation_id:
                glyph.metadata["mutation_id"] = mutation_id

            glyph.metadata["kg_origin_path"] = f"containers/{container_id}/glyphs/{glyph.metadata.get('id', 'unknown')}"
            glyph.metadata["container_id"] = container_id

            glyph_id = glyph.metadata.get("id")

            # Handle case where id is a dict instead of a string
            if isinstance(glyph_id, dict):
                glyph_id = glyph_id.get("id") or glyph_id.get("_id") or glyph_id.get("value")

            # Only proceed if glyph_id is now a valid string
            if isinstance(glyph_id, str) and glyph_id.strip():
                try:
                    kg_writer = KnowledgeGraphWriter()
                    kg_writer.link_source(
                        node_id=glyph_id,
                        source_id=container_id,
                        relation=glyph.metadata.get("kg_origin_path", "supports")
                    )
                except Exception as e:
                    logger.warning(f"[KG] Failed to link glyph {glyph_id} to KG: {e}")
            else:
                logger.warning(f"[KG] Skipping invalid glyph ID for container {container_id}: {glyph_id}")

    # ✅ 7. Add semantic links and replay chains
    for node in tree.node_index.values():
        resolve_semantic_links(tree, node)
        resolve_replay_chain(tree, node)

    # 🔁 Inject trace replay paths if requested
    if inject_trace:
        from backend.modules.symbolic.hst.symbol_tree_replay_utils import build_replay_paths
        replay_paths = build_replay_paths(tree, container)
        container.setdefault("trace", {})["replayPaths"] = replay_paths

    # 🌌 Inject GHX overlay if enabled
    if inject_overlay:
        from backend.modules.symbolic.symbolnet.symbolnet_overlay_injector import inject_overlay_to_container
        inject_overlay_to_container(container, tree)

    logger.info(f"[🌳] SymbolicMeaningTree built for container {container_id} with {len(tree.node_index)} nodes.")
    return tree
    
def resolve_container(input_arg: str) -> dict:
    """
    Load container from file if path is given, otherwise use container ID.
    Handles both file paths and runtime container IDs.
    """
    if input_arg.endswith(".dc.json") or os.path.exists(input_arg):
        # Load from file path using legacy loader (stable for .dc.json files)
        try:
            from backend.modules.dimensions.containers.container_loader import load_container_from_file
            return load_container_from_file(input_arg)
        except ImportError as e:
            raise ImportError(f"❌ Could not import legacy file loader: {e}")
    else:
        # Load by container ID using safe fallback-aware loader
        try:
            from backend.modules.symbolic.utils.container_utils import safe_load_container_by_id
            return safe_load_container_by_id(input_arg)
        except Exception as e:
            raise RuntimeError(f"❌ Failed to load container by ID '{input_arg}': {e}")

def safe_register_container(*args, **kwargs):
    from backend.modules.sqi.sqi_container_registry import register_container
    return register_container(*args, **kwargs)

class StubGWaveTransmitter:
    @staticmethod
    def send(data: dict):
        print(f"[Stub:GWave] Sending symbolic tree data: {json.dumps(data)[:120]}...")

GWaveTransmitter = StubGWaveTransmitter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Symbolic Tree Structures ----------------------------------------------------

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid

from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph
@dataclass
class SymbolicTreeNode:
    glyph: 'SymbolGlyph'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    children: List['SymbolicTreeNode'] = field(default_factory=list)
    parent: Optional['SymbolicTreeNode'] = None
    entangled_ids: List[str] = field(default_factory=list)
    replayed_from: Optional[str] = None
    mutation_source: Optional[str] = None
    goal_score: Optional[float] = None
    sqi_score: Optional[float] = None
    semantic_context: Optional[str] = None  # 🌐 New: meaning group
    semantic_links: List[Dict[str, Any]] = field(default_factory=list)
    morphic_overlay: Dict[str, Any] = field(default_factory=dict)  # 🌀 Visual replay/goal overlay

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "glyph": self.glyph.to_dict(),
            "entangled_ids": self.entangled_ids,
            "replayed_from": self.replayed_from,
            "mutation_source": self.mutation_source,
            "goal_score": self.goal_score,
            "sqi_score": self.sqi_score,
            "semantic_context": self.semantic_context,
            "semantic_links": self.semantic_links,
            "morphic_overlay": self.morphic_overlay,  # 🌀 Include visual goal/entropy overlays
            "children": [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SymbolicTreeNode':
        glyph = SymbolGlyph.from_dict(data["glyph"])
        node = SymbolicTreeNode(
            glyph=glyph,
            id=data.get("id", str(uuid.uuid4())),
            entangled_ids=data.get("entangled_ids", []),
            replayed_from=data.get("replayed_from"),
            mutation_source=data.get("mutation_source"),
            goal_score=data.get("goal_score"),
            sqi_score=data.get("sqi_score"),
            semantic_context=data.get("semantic_context"),
            semantic_links=data.get("semantic_links", []),
            morphic_overlay=data.get("morphic_overlay", {}) 
        )
        node.children = [SymbolicTreeNode.from_dict(child) for child in data.get("children", [])]
        return node


from dataclasses import dataclass, field
from typing import Dict

@dataclass
class SymbolicMeaningTree:
    root: SymbolicTreeNode
    container_id: str
    node_index: Dict[str, SymbolicTreeNode] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)  # <-- Add this field

    def __post_init__(self):
        self.node_index[self.root.id] = self.root
        self.metadata["container_id"] = self.container_id
        self.metadata["container_name"] = getattr(self.root.glyph.metadata, "container_name", None) or self.container_id

    def add_node(self, label: str, value: str, metadata: Optional[dict] = None, parent: Optional[SymbolicTreeNode] = None) -> str:
        # 🌱 Build a SymbolGlyph from label/value/metadata
        glyph = SymbolGlyph(
            label=label,
            value=value,
            metadata=metadata or {},
        )
        # 📦 Wrap into a SymbolicTreeNode
        parent_node = parent or self.root
        node = SymbolicTreeNode(glyph=glyph, parent=parent_node)
        parent_node.children.append(node)
        self.node_index[node.id] = node
        return node.id

    def replay_path(self, node_id: str) -> List[SymbolGlyph]:
        path = []
        node = self.node_index.get(node_id)
        while node:
            path.append(node.glyph)
            node = node.parent
        return list(reversed(path))

    def mutate_path(self, from_node_id: str, new_glyph: SymbolGlyph) -> SymbolicTreeNode:
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
# --- Utility ---------------------------------------------------------------------

def generate_symbol_tree_from_file(container_path: str):
    """
    Load a .dc.json container and extract its Symbolic Meaning Tree.
    """
    if not os.path.exists(container_path):
        raise FileNotFoundError(f"Container not found: {container_path}")

    try:
        from backend.modules.dimensions.containers.container_loader import load_container_from_file
    except ImportError:
        from backend.modules.dimensions.containers.container_loader import load_container_from_file

    container = load_container_from_file(container_path)
    tree = build_tree_from_container(container)

    return tree

def preview_tree(container_path: str):
    tree = generate_symbol_tree_from_file(container_path)

    print(f"\n🌳 [bold]Symbolic Meaning Tree for:[/bold] {container_path}")
    print(f"[cyan]Root Glyph:[/cyan] {tree.root.glyph}")
    print(f"[cyan]Nodes:[/cyan] {len(tree.node_index)}")

    # 🔍 Add diagnostics:
    print(f"[dim]Node IDs:[/dim] {list(tree.node_index.keys())}")
    print(f"[dim]Trace Length:[/dim] {len(build_tree_from_container(container_path).node_index)}")

# --- Tree Construction + Injection Logic -----------------------------------------

def build_tree_from_container(container: Union[str, dict, object]) -> SymbolicMeaningTree:
    """
    Build a symbolic tree from a container ID (str) or a loaded container (dict or object).
    """
    if isinstance(container, str):
        container_id = container
    elif isinstance(container, dict):
        container_id = container.get("id") or container.get("container_id") or "unknown"
    else:
        container_id = getattr(container, "id", None) or getattr(container, "container_id", None) or "unknown"

    from backend.modules.knowledge_graph.kg_writer_singleton import get_glyph_trace_for_container
    trace = get_glyph_trace_for_container(container_id)
    if not trace:
        raise ValueError(f"No glyph trace found for container {container_id}")

    def ensure_glyph(g):
        if isinstance(g, SymbolGlyph):
            return g
        return SymbolGlyph(
            label=g.get("label", "unknown"),
            value=g.get("value", ""),
            metadata=g.get("metadata", {})
        )

    def attach_replay_data(node: SymbolicTreeNode, glyph: SymbolGlyph):
        if "replay" in glyph.metadata:
            node.metadata["replay"] = glyph.metadata["replay"]
        if "entangled_with" in glyph.metadata:
            node.metadata["entangled_with"] = glyph.metadata["entangled_with"]

    # Build root node from trace
    root_glyph = ensure_glyph(trace[0])
    root_node = SymbolicTreeNode(glyph=root_glyph)
    attach_replay_data(root_node, root_glyph)

    tree = SymbolicMeaningTree(root=root_node, container_id=container_id)
    tree.node_index[root_node.id] = root_node

    current = root_node
    for raw_glyph in trace[1:]:
        glyph = ensure_glyph(raw_glyph)
        node = SymbolicTreeNode(glyph=glyph, parent=current)
        attach_replay_data(node, glyph)
        current.children.append(node)
        tree.node_index[node.id] = node
        current = node

    logger.info(f"Built SymbolicMeaningTree for container {container_id} with {len(tree.node_index)} nodes.")
    return tree

def build_qfc_view(container_data: Dict) -> Dict:
    """
    Builds a QFC-ready node+link+trail structure from a .dc.json container
    """
    tree = build_symbolic_tree_from_container(container_data)

    nodes = []
    links = []

    for node in tree.iter_nodes():
        g = node.glyph
        nid = node.id

        # 🌌 Node rendering data
        node_data = {
            "id": nid,
            "label": g.label,
            "position": node.metadata.get("qfc_position", [0, 0, 0]),
            "containerId": g.metadata.get("linkContainerId"),
            "color": g.metadata.get("color"),
            "predicted": g.metadata.get("type") == "prediction",
            "trailId": g.metadata.get("trail_id"),
            "sqiScore": getattr(node, "sqi_score", None),
            "goalMatchScore": g.metadata.get("goal_match_score"),
            "rewriteSuccessProb": g.metadata.get("rewrite_success_prob"),
        }

        # 🧬 Optional enhancements
        if "entangled_with" in node.metadata:
            node_data["entangledWith"] = node.metadata["entangled_with"]
        if "replay" in node.metadata:
            node_data["replay"] = node.metadata["replay"]

        nodes.append(node_data)

        # ➰ Link to children
        for child in node.children:
            links.append({
                "source": nid,
                "target": child.id,
                "type": g.metadata.get("link_type", "entangled"),
            })

    return {
        "nodes": nodes,
        "links": links,
        "containerId": tree.container_id,
        "rootNodeId": tree.root.id,
    }

def stream_tree_to_qfc(container_data: Dict):
    from backend.modules.qfield.qfc_bridge import send_qfc_payload
    payload = build_qfc_view(container_data)
    send_qfc_payload(payload)

def inject_mutation_path(tree: SymbolicMeaningTree, from_node_id: str, new_glyph: SymbolGlyph) -> SymbolicTreeNode:
    node = tree.mutate_path(from_node_id, new_glyph)
    logger.info(f"Injected mutation from {from_node_id} into tree for container {tree.container_id}")
    return node

def score_path_with_SQI(tree: SymbolicMeaningTree):
    try:
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
    except ImportError as e:
        logger.warning(f"[⚠️] Could not import SQIReasoningEngine due to circular import: {e}")
        return

    engine = SQIReasoningEngine()

    for node in tree.node_index.values():
        glyph = node.glyph
        # Ensure the glyph is valid before scoring
        if glyph is None:
            logger.warning(f"[SQI] Node {node.id} has no glyph. Skipping.")
            continue

        try:
            score = engine.score_node(glyph)
            node.sqi_score = score
            logger.debug(f"SQI score for node {node.id}: {score}")
        except Exception as score_err:
            logger.warning(f"[SQI] Failed to score glyph in node {node.id}: {score_err}")

def visualize_path(tree: SymbolicMeaningTree, mode: str = "GHX"):
    if mode == "GHX":
        from backend.modules.hologram.ghx_encoder import render_symbolic_tree_to_ghx
        render_symbolic_tree_to_ghx(tree)
    elif mode == "ReplayHUD":
        from backend.modules.runtime.replay_hud import stream_tree_to_hud
        stream_tree_to_hud(tree)
    elif mode == "QFC":
        from backend.modules.qfield.qfc_streamer import stream_tree_to_qfc
        stream_tree_to_qfc(tree)
    else:
        logger.warning(f"Unknown visualization mode: {mode}")

def visualize_path(tree: SymbolicMeaningTree, mode: str = "GHX"):
    logger.info(f"Visualizing symbolic tree for {tree.container_id} in mode {mode}")

def stream_tree_to_gwave(tree: SymbolicMeaningTree):
    GWaveTransmitter.send({
        "type": "symbol_tree",
        "tree": tree.to_dict(),
    })

def attach_tree_to_teleport(packet, tree: SymbolicMeaningTree):
    from backend.modules.teleport.teleport_packet import TeleportPacket

    if not isinstance(packet, TeleportPacket):
        raise TypeError("Expected packet to be a TeleportPacket")

    packet.attach_payload("symbol_tree", tree.to_dict())

def inject_tree_to_dreamcore(tree: SymbolicMeaningTree):
    from backend.modules.aion.dream_core import DreamCore 
    DreamCore().inject_future_tree(tree)

def resolve_goal_from_tree(tree: SymbolicMeaningTree):
    from backend.modules.skills.goal_engine import GoalEngine
    GoalEngine().resolve_from_tree_path(tree)

def export_tree_to_kg(tree: SymbolicMeaningTree):
    from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
    kg_writer = get_kg_writer()
    
    if not kg_writer:
        logger.warning("No KnowledgeGraphWriter instance available to export tree.")
        return

    try:
        # 🧠 Ensure container ID is string if present
        container_id = tree.metadata.get("container_id") or tree.metadata.get("id")
        source_id = str(container_id) if container_id and not isinstance(container_id, str) else container_id

        # 🔁 Inject source_id into all nodes for linking
        for node in tree.nodes:
            glyph_id = node.glyph_id or node.node_id
            if glyph_id and source_id:
                try:
                    kg_writer.link_source(
                        node_id=glyph_id,
                        source_id=source_id,
                        relation=node.glyph.metadata.get("kg_origin_path", "supports") if node.glyph else "supports"
                    )
                except Exception as e:
                    logger.warning(f"[KG] Failed to link node {glyph_id} -> {source_id}: {e}")
        
        # 🌳 Export full symbolic tree to KG
        kg_writer.export_symbol_tree(tree)
    except Exception as e:
        logger.error(f"[KG] Error during export: {e}")

# --- CLI Entry -------------------------------------------------------------------

def inject_symbolic_tree(container_arg: str):
    try:
        container = None
        container_id = None

        # 🧠 Case 1: Path to .dc.json file
        if container_arg.endswith(".dc.json") and os.path.exists(container_arg):
            with open(container_arg, 'r') as f:
                container = json.load(f)
            if isinstance(container, dict):
                container_id = container.get("id") or os.path.splitext(os.path.basename(container_arg))[0]
            else:
                raise ValueError(f"[❌] Loaded non-dict container from file: {container_arg}")

        else:
            # 🧠 Case 2: Treat as UCS container ID
            container = safe_load_container_by_id(container_arg)

            # 🧯 Fallback: Try to load from containers/<id>.dc.json if not found
            if not container:
                fallback_path = f"containers/{container_arg}.dc.json"
                if os.path.exists(fallback_path):
                    with open(fallback_path, 'r') as f:
                        container = json.load(f)
                    if isinstance(container, dict):
                        container_id = container.get("id") or container_arg
                        logger.warning(f"[Fallback] Loaded container from file: {fallback_path}")
                    else:
                        raise ValueError(f"[❌] Loaded non-dict container from fallback file: {fallback_path}")
                else:
                    raise ValueError(f"Container '{container_arg}' not found in UCS or file path: {fallback_path}")
            else:
                container_id = getattr(container, "id", None) or getattr(container, "container_id", None) or container_arg

        # 🔁 Try registering into symbolic container registry (may fail if missing symbolic fields)
        try:
            safe_register_container(container)
        except Exception as e:
            logger.warning(f"[⚠️] Could not register container in UCS registry: {e}")

        # 🌳 Build Symbol Tree
        tree = build_symbolic_tree_from_container(container)
        tree_dict = tree.to_dict()

        # ✅ Inject symbolic tree based on container type
        if isinstance(container, dict):
            if "symbolTree" in container and isinstance(container["symbolTree"], dict):
                merged_tree = {**container["symbolTree"], **tree_dict}
                container["symbolTree"] = merged_tree
                logger.info(f"[🔁] Merged symbolic tree with existing tree in container '{container_id}'")
            else:
                container["symbolTree"] = tree_dict
                logger.info(f"[🆕] Injected new symbolic tree into container '{container_id}'")
        else:
            setattr(container, "symbolTree", tree_dict)
            logger.info(f"[🧬] Injected symbolic tree into UCS container object: '{container_id}'")

        # 🧠 SQI evaluation and KG export (optional for full containers)
        try:
            score_path_with_SQI(tree)
            export_tree_to_kg(tree)
        except Exception as e:
            logger.warning(f"[⚠️] Skipping SQI/Export: {e}")

        # 💾 Save updated container if dict-based
        if isinstance(container, dict) and (container_arg.endswith(".dc.json") or container_id):
            output_path = container_arg if container_arg.endswith(".dc.json") else f"containers/{container_id}.dc.json"
            with open(output_path, 'w') as f:
                json.dump(container, f, indent=2)
            logger.info(f"[💾] Saved symbolic tree to {output_path} with {len(tree.node_index)} nodes.")

        print(f"[✅] Symbolic Tree injected into: {container_id}")

    except Exception as e:
        logger.error(f"Failed to inject symbolic tree: {e}")
        print(f"[❌] Failed: {e}")
        
# --- CLI Hook --------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import logging
    import json
    import os

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if len(sys.argv) < 2:
        print("Usage: symbol_tree_generator.py <container_id | path/to/container.dc.json>")
        sys.exit(1)

    container_arg = sys.argv[1]
    is_path = os.path.exists(container_arg)

    try:
        # ✅ Attempt full symbolic tree injection via UCS + Knowledge Graph
        inject_symbolic_tree(container_arg)

    except Exception as e:
        logger.warning(f"[⚠️ Fallback] Full injector failed: {e}")
        try:
            # 🧯 Fallback: Use raw file from known container directory if needed
            if container_arg.endswith(".dc.json") and os.path.exists(container_arg):
                file_path = container_arg
            else:
                file_path = f"backend/modules/dimensions/containers/{container_arg}.dc.json"

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, 'r') as f:
                container = json.load(f)

            tree = build_symbolic_tree_from_container(container)
            container["symbolTree"] = tree.to_dict()

            with open(file_path, 'w') as f:
                json.dump(container, f, indent=2)

            print(f"[✅] Fallback symbolic tree injected into {file_path} with {len(tree.node_index)} nodes.")

        except Exception as fallback_error:
            logger.error(f"[❌] Fallback symbolic tree injection failed: {fallback_error}")
            print(f"[❌] Failed: {fallback_error}")