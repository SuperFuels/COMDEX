# backend/modules/symbolic_engine/symbolic_kernels/physics_glyphs.py

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class PhysicsGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self):
        pass

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"


# --- Classical Mechanics Glyphs ---

class ForceGlyph(PhysicsGlyph):  # F = m * a
    def __init__(self, mass, acceleration):
        super().__init__('F', [mass, acceleration])
    def evaluate(self):
        return f"Force = {self.operands[0]} * {self.operands[1]}"


class EnergyKineticGlyph(PhysicsGlyph):  # E = 1/2 m v^2
    def __init__(self, mass, velocity):
        super().__init__('Ek', [mass, velocity])
    def evaluate(self):
        return f"Kinetic Energy = 0.5 * {self.operands[0]} * {self.operands[1]}2"


class EnergyRelativityGlyph(PhysicsGlyph):  # E = mc^2
    def __init__(self, mass, c='c'):
        super().__init__('E=mc2', [mass, c])
    def evaluate(self):
        return f"Energy = {self.operands[0]} * {self.operands[1]}2"


class MotionEquationGlyph(PhysicsGlyph):  # x = x0 + vt + 1⁄2at2
    def __init__(self, x0, v, t, a):
        super().__init__('x', [x0, v, t, a])
    def evaluate(self):
        return f"x = {self.operands[0]} + {self.operands[1]}*{self.operands[2]} + 0.5*{self.operands[3]}*{self.operands[2]}2"


# --- Vector & Unit Glyphs ---

class VectorGlyph(PhysicsGlyph):
    def __init__(self, components: List[Any]):
        super().__init__('vec', components)
    def evaluate(self):
        return f"Vector({', '.join(map(str, self.operands))})"


class UnitGlyph(PhysicsGlyph):
    def __init__(self, quantity: Any, unit: str):
        super().__init__('unit', [quantity, unit])
    def evaluate(self):
        return f"{self.operands[0]} [{self.operands[1]}]"


# --- Physical Law Glyphs ---

class NewtonsSecondLawGlyph(PhysicsGlyph):
    def __init__(self, force, mass, acceleration):
        super().__init__('F=ma', [force, mass, acceleration])
    def evaluate(self):
        return f"{self.operands[0]} = {self.operands[1]} * {self.operands[2]}"


# --- Domain Registry ---

class PhysicsDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])


physics_registry = PhysicsDomainRegistry()

# Registering core glyphs
physics_registry.register("mechanics", ForceGlyph)
physics_registry.register("mechanics", MotionEquationGlyph)
physics_registry.register("mechanics", NewtonsSecondLawGlyph)
physics_registry.register("energy", EnergyKineticGlyph)
physics_registry.register("energy", EnergyRelativityGlyph)
physics_registry.register("vectors", VectorGlyph)
physics_registry.register("units", UnitGlyph)


# --- Composer (for symbolic trace or GHX view) ---
def compose_physics_trace(glyphs: List[PhysicsGlyph]) -> str:
    return ' -> '.join(map(str, glyphs))