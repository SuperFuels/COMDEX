from backend.modules.dimensions.universal_container_system import ucs_runtime as ucs

def test_load_and_route_maxwell():
    ucs.atom_index.clear()
    ucs.load_container_from_path(
        "backend/modules/dimensions/containers/atom_maxwell_bundle.dc.json",
        register_as_atom=False,
    )
    assert "atom_maxwell" in ucs.atom_index

    goal = {"caps":["lean.replay"], "nodes":["maxwell_eqs"]}
    if hasattr(ucs, "choose_route"):
        route = ucs.choose_route(goal, k=3)
        atoms = route["atoms"]
    else:
        atoms = ucs.compose_path(goal, k=3)

    assert "atom_maxwell" in atoms