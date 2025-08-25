from backend.modules.dimensions.container_expander import ContainerExpander
from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer

# Seed + auto-load into KG (ContainerExpander already calls load_domain_pack for physics_core)
exp = ContainerExpander("physics_core")
exp.seed_initial_space(size=1, geometry="Tesseract")

# If you want to force-run the pack again explicitly:
# from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
# container = ucs_runtime.get_container("physics_core")
# kg_writer.load_domain_pack("physics_core", container)

# Inspect recent KG glyphs written by the loader
recent = kg_writer.list_recent(50)
physics = [g for g in recent if g.get("plugin") in ("KG", "SQI") or "KG" in g.get("tags", [])]
print("KG writes (last 50):")
for g in physics:
    print(g["type"], g.get("metadata", {}))