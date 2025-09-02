from backend.modules.symbolic.hst.symbol_tree_generator import build_symbolic_tree_from_container
from backend.modules.runtime.container_runtime import safe_load_container_by_id
from backend.modules.ghx.ghx_overlay_utils import render_symbolic_branch_overlay
from backend.modules.sqi.qfc_overlay_driver import inject_qfc_overlay
from backend.modules.knowledge.knowledge_graph_writer import export_hst_branch_metadata
from backend.modules.sqi.qglyph_utils import broadcast_qglyph_fusion_trail
from backend.modules.dna_chain.dna_stream_exporter import inject_into_shared_dna_pool
from backend.modules.sqi.soul_law_gate import enforce_soul_law_filter
from backend.modules.sqi.plugin_system import apply_plugin_hooks_on_tree
from backend.modules.prediction.prediction_engine import prepare_future_trace_scenarios
from backend.modules.symbolic.teleport.symbolic_teleport_fuser import trigger_symbolic_teleportation


def generate_holographic_tree(
    container_id: str,
    *,
    render_qfc: bool = True,
    render_ghx: bool = True,
    export_metadata: bool = True,
    enable_multi_agent: bool = True,
    apply_mutation_hooks: bool = True,
    run_prediction_sim: bool = True,
    soul_law_filter: bool = True,
    plugin_extensions: bool = True
) -> dict:
    """
    Build and render the SymbolicMeaningTree as a holographic tree structure with multi-agent and mutation support.
    """

    container = safe_load_container_by_id(container_id)
    if container is None:
        raise ValueError(f"Container not found: {container_id}")

    symbolic_tree = build_symbolic_tree_from_container(container)

    # 🧩 Plugin extension hooks
    if plugin_extensions:
        apply_plugin_hooks_on_tree(symbolic_tree)

    # 🚦 SoulLaw mutation filtering
    if soul_law_filter:
        symbolic_tree = enforce_soul_law_filter(symbolic_tree)

    # ♻️ Mutation ripple scoring
    if apply_mutation_hooks:
        broadcast_qglyph_fusion_trail(symbolic_tree, source_container_id=container_id)

    # 🧬 Shared DNA stream
    inject_into_shared_dna_pool(container_id, symbolic_tree)

    # 🪞 Reflective + multi-agent fusion overlays
    if enable_multi_agent:
        render_symbolic_branch_overlay(container_id, symbolic_tree, multi_agent=True)

    # 🌀 Inject into QFC 3D field
    if render_qfc:
        inject_qfc_overlay(container_id, symbolic_tree)

    # 🌀 Inject into GHX 3D overlay
    if render_ghx:
        render_symbolic_branch_overlay(container_id, symbolic_tree)

    # 📽️ Export replay + morphic metadata
    if export_metadata:
        export_hst_branch_metadata(container_id, symbolic_tree)

    # 🪄 Prepare predictive simulations
    if run_prediction_sim:
        prepare_future_trace_scenarios(container_id, symbolic_tree)

    # 🚀 Symbolic teleport/fusion trigger
    trigger_symbolic_teleportation(container_id, symbolic_tree)

    return {
        "status": "success",
        "tree": symbolic_tree.to_dict(),
        "render_qfc": render_qfc,
        "render_ghx": render_ghx,
        "metadata_exported": export_metadata,
        "multi_agent": enable_multi_agent,
        "mutation_hooks_applied": apply_mutation_hooks,
        "soul_law_filter_applied": soul_law_filter,
        "plugin_extensions_applied": plugin_extensions,
        "predictive_simulations": run_prediction_sim,
        "teleportation_triggered": True
    }