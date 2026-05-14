def test_physics_core_seed_loads():
    from backend.modules.dimensions.container_expander import ContainerExpander

    expander = ContainerExpander("physics_core")
    msg = expander.seed_initial_space(size=2, geometry="Tesseract")
    assert "Seeded initial" in msg

    snap = expander.status()

    # Categories from the seed must exist
    cats = {c.get("id") for c in snap.get("glyph_categories", [])}
    assert {"mech", "thermo", "em", "qft"} <= cats

    # Snapshot-only alias nodes must be present
    # (N_force, N_energy, N_maxwell, N_qft are added in _snapshot_with_aliases;
    # this locks the behavior so future changes don't regress it)
    node_ids = {n.get("id") for n in snap.get("nodes", [])}
    assert {"N_force", "N_energy", "N_maxwell", "N_qft"} <= node_ids

    # Alias link required by tests
    rels = {(l.get("src"), l.get("dst"), l.get("relation")) for l in snap.get("links", [])}
    assert ("N_force", "N_energy", "work-energy") in rels