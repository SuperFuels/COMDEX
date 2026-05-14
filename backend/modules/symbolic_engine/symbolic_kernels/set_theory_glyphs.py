from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional


class SetGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self):
        pass

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"


# Basic Set Operations
class ElementOfGlyph(SetGlyph):  # ∈
    def __init__(self, element, set_): super().__init__('∈', [element, set_])
    def evaluate(self): return self.operands[0] in self.operands[1]

class NotElementOfGlyph(SetGlyph):  # ∉
    def __init__(self, element, set_): super().__init__('∉', [element, set_])
    def evaluate(self): return self.operands[0] not in self.operands[1]

class SubsetGlyph(SetGlyph):  # ⊆
    def __init__(self, a, b): super().__init__('⊆', [a, b])
    def evaluate(self): return set(self.operands[0]).issubset(set(self.operands[1]))

class UnionGlyph(SetGlyph):  # ∪
    def __init__(self, a, b): super().__init__('∪', [a, b])
    def evaluate(self): return set(self.operands[0]).union(set(self.operands[1]))

class IntersectionGlyph(SetGlyph):  # ∩
    def __init__(self, a, b): super().__init__('∩', [a, b])
    def evaluate(self): return set(self.operands[0]).intersection(set(self.operands[1]))

class DifferenceGlyph(SetGlyph):  # ∖
    def __init__(self, a, b): super().__init__('∖', [a, b])
    def evaluate(self): return set(self.operands[0]).difference(set(self.operands[1]))

class PowerSetGlyph(SetGlyph):  # ℘
    def __init__(self, s): super().__init__('℘', [s])
    def evaluate(self):
        from itertools import chain, combinations
        s = list(self.operands[0])
        return list(chain.from_iterable(combinations(s, r) for r in range(len(s)+1)))


# Set Constants
class EmptySetGlyph(SetGlyph):  # ∅
    def __init__(self): super().__init__('∅', [])
    def evaluate(self): return set()

class UniversalSetGlyph(SetGlyph):  # U
    def __init__(self, domain_scope: Optional[List[Any]] = None):
        domain_scope = domain_scope or []
        super().__init__('U', [domain_scope])

    def evaluate(self):
        return set(self.operands[0])


# Set Builder Notation
class SetBuilderGlyph(SetGlyph):
    def __init__(self, variable: str, condition: str):  # { x | condition }
        super().__init__('{ | }', [variable, condition])
    def evaluate(self): return f"{{ {self.operands[0]} | {self.operands[1]} }}"


# Registry
class SetTheoryRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])


set_registry = SetTheoryRegistry()
set_registry.register("basic", ElementOfGlyph)
set_registry.register("basic", NotElementOfGlyph)
set_registry.register("basic", SubsetGlyph)
set_registry.register("operations", UnionGlyph)
set_registry.register("operations", IntersectionGlyph)
set_registry.register("operations", DifferenceGlyph)
set_registry.register("operations", PowerSetGlyph)
set_registry.register("constants", EmptySetGlyph)
set_registry.register("constants", UniversalSetGlyph)
set_registry.register("builder", SetBuilderGlyph)


# Composer (for GHX, .dc debug)
def compose_set_expression(glyphs: List[SetGlyph]) -> str:
    return ' ⊢ '.join(map(str, glyphs))