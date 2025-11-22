# backend/modules/symbolic/hst/symbol_tree_replay.py

from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Core tree + link utilities
from backend.modules.symbolic.symbol_tree_generator import (
    SymbolicMeaningTree,
    SymbolicTreeNode,
    build_symbolic_tree_from_container,
    resolve_replay_chain,
)


def _build_tree_for_container(container: Dict[str, Any]) -> Optional[SymbolicMeaningTree]:
    """
    Safely build a SymbolicMeaningTree for the given container.

    We deliberately call the generator here instead of trying to reconstruct
    the tree from the serialized HST dict, because the generator already
    knows how to:

      - Walk glyphs & traces
      - Attach semantic_links
      - Attach replay_chain hints via resolve_replay_chain(...)
    """
    if not isinstance(container, dict):
        return None

    try:
        # Newer signature (with inject_trace flag)
        return build_symbolic_tree_from_container(container, inject_trace=False)
    except TypeError:
        # Older signature without inject_trace
        try:
            return build_symbolic_tree_from_container(container)
        except Exception as e:
            logger.warning("[HST replay] build_symbolic_tree_from_container failed: %s", e)
            return None
    except Exception as e:
        logger.warning("[HST replay] build_symbolic_tree_from_container failed: %s", e)
        return None


def _node_to_step(node: SymbolicTreeNode) -> Dict[str, Any]:
    """
    Convert a SymbolicTreeNode into a compact, WS-friendly step dict.

    This is what ends up inside each replay path's "steps" array.
    """
    glyph = getattr(node, "glyph", None)
    coord = None
    glyph_text = None

    if glyph is not None:
        # Be tolerant of slightly different glyph shapes across branches
        coord = getattr(glyph, "coord", None) or getattr(glyph, "coordinate", None)
        glyph_text = getattr(glyph, "glyph", None) or getattr(glyph, "text", None)

    metadata = getattr(node, "metadata", {}) or {}

    return {
        "id": node.id,
        "label": node.label,
        "kind": getattr(node, "node_type", None),
        "weight": getattr(node, "weight", None),
        "glyph": glyph_text,
        "coord": coord or metadata.get("coord"),
        "metadata": metadata,
    }


def build_replay_paths(
    tree: SymbolicMeaningTree,
    container: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Flatten per-node replay_chain hints on a SymbolicMeaningTree into a list
    of lightweight replay path descriptors.

    Each element in the returned list has shape:

        {
          "id": "<seed_id>-><target_id>",
          "seed_id": "...",
          "target_id": "...",
          "reason": "<link type>",
          "score": <float|None>,
          "container_id": "<dc id or None>",
          "steps": [
            {  # seed node snapshot
              "id": ...,
              "label": ...,
              "kind": ...,
              "glyph": ...,
              "coord": ...,
              "metadata": {...},
            },
            {  # target node snapshot (if resolvable)
              ...
            }
          ]
        }

    This structure is:

      - Simple enough for container_runtime to tuck into container["trace"]["replayPaths"]
      - Directly consumable by hst_websocket_streamer.broadcast_replay_paths(...)
    """
    paths: List[Dict[str, Any]] = []

    if not tree or not getattr(tree, "node_index", None):
        return paths

    container_id = (container or {}).get("id") if isinstance(container, dict) else None

    # Ensure replay_chain exists on each node (idempotent).
    # build_symbolic_tree_from_container normally already calls this, but
    # we re-run defensively so this helper works in more contexts.
    try:
        for node in tree.node_index.values():
            try:
                resolve_replay_chain(tree, node)
            except Exception:
                # If resolve_replay_chain blows up for a node we still keep going.
                pass
    except Exception:
        pass

    # Walk all nodes and harvest their replay_chain hints
    for node in tree.node_index.values():
        replay_chain = getattr(node, "replay_chain", None) or []
        if not replay_chain:
            continue

        seed_step = _node_to_step(node)

        for link in replay_chain:
            target_id = link.get("target_id")
            target_node = tree.node_index.get(target_id)
            steps = [seed_step]

            if target_node is not None and target_node is not node:
                steps.append(_node_to_step(target_node))

            path_id = f"{node.id}->{target_id}" if target_id else node.id

            paths.append(
                {
                    "id": path_id,
                    "seed_id": node.id,
                    "target_id": target_id,
                    "reason": link.get("reason"),
                    "score": link.get("score"),
                    "container_id": container_id,
                    "steps": steps,
                }
            )

    # Sort so "most interesting" (highest score) paths float to the top.
    # Entries with no score land at the end.
    paths.sort(key=lambda p: (p.get("score") is None, -(p.get("score") or 0.0)))
    return paths


def build_symbol_tree_replay_paths(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    High-level helper used by ContainerRuntime.get_decrypted_current_container.

    Given a decrypted container dict, rebuilds the SymbolicMeaningTree and
    derives replay paths suitable for:

      - container["trace"]["replayPaths"]
      - hst_websocket_streamer.broadcast_replay_paths(...)

    Safe to call even if the container is missing HST metadata; you'll just
    get an empty list back.
    """
    if not isinstance(container, dict):
        return []

    tree = _build_tree_for_container(container)
    if not tree:
        return []

    try:
        return build_replay_paths(tree, container=container)
    except Exception as e:
        logger.warning("[HST replay] Failed to build replay paths for container %s: %s",
                       container.get("id"), e)
        return []