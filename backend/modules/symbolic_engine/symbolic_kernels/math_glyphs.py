# backend/modules/symbolic_kernels/math_kernel.py

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Union

class MathGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self):
        pass

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"

# Algebraic Glyphs
class AddGlyph(MathGlyph):
    def __init__(self, a, b): super().__init__('+', [a, b])
    def evaluate(self): return sum(self.operands)

class SubtractGlyph(MathGlyph):
    def __init__(self, a, b): super().__init__('-', [a, b])
    def evaluate(self): return self.operands[0] - self.operands[1]

class MultiplyGlyph(MathGlyph):
    def __init__(self, a, b): super().__init__('×', [a, b])
    def evaluate(self): return self.operands[0] * self.operands[1]

class DivideGlyph(MathGlyph):
    def __init__(self, a, b): super().__init__('÷', [a, b])
    def evaluate(self): return self.operands[0] / self.operands[1]

class PowerGlyph(MathGlyph):
    def __init__(self, base, exponent): super().__init__('^', [base, exponent])
    def evaluate(self): return self.operands[0] ** self.operands[1]

# Calculus Glyphs
class DerivativeGlyph(MathGlyph):
    def __init__(self, func, var): super().__init__('d/dx', [func, var])
    def evaluate(self): return f"d({self.operands[0]})/d({self.operands[1]})"

class IntegralGlyph(MathGlyph):
    def __init__(self, func, var): super().__init__('∫', [func, var])
    def evaluate(self): return f"∫ {self.operands[0]} d{self.operands[1]}"

class LimitGlyph(MathGlyph):
    def __init__(self, func, var, approaching): 
        super().__init__('lim', [func, var, approaching])
    def evaluate(self): return f"lim {self.operands[1]}→{self.operands[2]} {self.operands[0]}"

class PartialDerivativeGlyph(MathGlyph):
    def __init__(self, func, var): super().__init__('∂/∂x', [func, var])
    def evaluate(self): return f"∂({self.operands[0]})/∂({self.operands[1]})"

# Differential Equation Glyphs
class DifferentialEquationGlyph(MathGlyph):
    def __init__(self, lhs, rhs): super().__init__('DE', [lhs, rhs])
    def evaluate(self): return f"{self.operands[0]} = {self.operands[1]}"

# Symbolic Structures (Fields, Groups, etc.)
class MathStructureGlyph(MathGlyph):
    def __init__(self, name: str, properties: Dict[str, Any]):
        super().__init__(name, [], properties)
    def evaluate(self): return self.metadata

# Registry for Topics
class MathDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])

# Singleton for SQI use
math_registry = MathDomainRegistry()
math_registry.register("algebra", AddGlyph)
math_registry.register("algebra", SubtractGlyph)
math_registry.register("algebra", MultiplyGlyph)
math_registry.register("algebra", DivideGlyph)
math_registry.register("algebra", PowerGlyph)
math_registry.register("calculus", DerivativeGlyph)
math_registry.register("calculus", IntegralGlyph)
math_registry.register("calculus", LimitGlyph)
math_registry.register("calculus", PartialDerivativeGlyph)
math_registry.register("differential_equations", DifferentialEquationGlyph)

# Expression composer (stub for GHX/SQI usage)
def compose_expression_tree(glyphs: List[MathGlyph]) -> str:
    return ' → '.join(map(str, glyphs))