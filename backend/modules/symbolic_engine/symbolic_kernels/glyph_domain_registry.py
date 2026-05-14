# backend/modules/symbolic_engine/symbolic_kernels/glyph_domain_registry.py

class GlyphDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])

glyph_registry = GlyphDomainRegistry()