from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List


class CategoryGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self):
        pass

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"


# Core Category Theory Glyphs

class ObjectGlyph(CategoryGlyph):  # A, B, C
    def __init__(self, name: str):
        super().__init__('Obj', [name])
    def evaluate(self): return {"object": self.operands[0]}


class MorphismGlyph(CategoryGlyph):  # f: A -> B
    def __init__(self, source: Any, target: Any, name: Optional[str] = None):
        metadata = {"name": name} if name else {}
        super().__init__('->', [source, target], metadata)
    def evaluate(self): return {
        "morphism": self.metadata.get("name", f"{self.operands[0]}->{self.operands[1]}"),
        "from": self.operands[0],
        "to": self.operands[1]
    }


class IdentityGlyph(CategoryGlyph):  # id_A
    def __init__(self, obj: Any):
        super().__init__('id', [obj])
    def evaluate(self): return {
        "identity": f"id_{self.operands[0]}"
    }


class CompositionGlyph(CategoryGlyph):  # g ∘ f
    def __init__(self, f: Any, g: Any):
        super().__init__('∘', [f, g])
    def evaluate(self): return {
        "composition": f"{self.operands[1]} ∘ {self.operands[0]}"
    }


class FunctorGlyph(CategoryGlyph):  # F: C -> D
    def __init__(self, source_cat: Any, target_cat: Any, name: Optional[str] = None):
        metadata = {"name": name} if name else {}
        super().__init__('F', [source_cat, target_cat], metadata)
    def evaluate(self): return {
        "functor": self.metadata.get("name", "F"),
        "from": self.operands[0],
        "to": self.operands[1]
    }


class NaturalTransformationGlyph(CategoryGlyph):  # η: F -> G
    def __init__(self, F: Any, G: Any, name: Optional[str] = None):
        metadata = {"name": name} if name else {}
        super().__init__('->', [F, G], metadata)
    def evaluate(self): return {
        "transformation": self.metadata.get("name", "η"),
        "from": self.operands[0],
        "to": self.operands[1]
    }


# Registry
class CategoryDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])


# Singleton Registry
category_registry = CategoryDomainRegistry()
category_registry.register("core", ObjectGlyph)
category_registry.register("core", MorphismGlyph)
category_registry.register("core", IdentityGlyph)
category_registry.register("core", CompositionGlyph)
category_registry.register("core", FunctorGlyph)
category_registry.register("core", NaturalTransformationGlyph)