from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

# ✅ Hub connector (idempotent)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):  # safe no-op fallback
        pass

# ✅ Optional directory + wormhole link (safe fallbacks)
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _NullAB:
        def register_container(self, *_a, **_k): pass
    address_book = _NullAB()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k): pass


class DNASpiral(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="DNA Spiral", geometry="dna_spiral", runtime=runtime)
        self.enable_feature("micro_grid")  # mutation lineage needs grid
        self.apply_time_dilation(1.2)      # slightly accelerated growth

        # --- NEW: Register + connect to hub (idempotent, safe) ---
        try:
            # minimal doc to appear in maps/graphs
            doc = {
                "id": getattr(self, "id", None) or self.name,
                "name": self.name,
                "geometry": self.geometry,
                "type": "container",
                "meta": {"address": f"ucs://local/{getattr(self, 'id', None) or self.name}#container"},
            }
            # 1) hub connect (does nothing if already connected)
            connect_container_to_hub(doc)

            # 2) optional: address directory + default wormhole link
            try:
                address_book.register_container(doc)
            finally:
                # link to your hub/root so it appears in wormhole graph; change hub id if needed
                link_wormhole(doc["id"], "ucs_hub")
        except Exception:
            # keep init resilient; logging is handled by upstream frameworks
            pass

    def mutate_lineage(self, glyph_sequence):
        print(f"🧬 Mutating lineage in {self.name}: {glyph_sequence}")
        self.glyph_storage.extend(glyph_sequence)
        self.visualize_state("mutation")